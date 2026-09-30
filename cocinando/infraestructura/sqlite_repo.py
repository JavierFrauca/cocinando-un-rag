"""El repositorio: FTS5 + sqlite-vec en un solo archivo (caps. 9 y 11).

Dos canales — el léxico (FTS5, BM25 de serie) y el denso (sqlite-vec) —
viven en el mismo fichero SQLite, sin servidor ni contenedor. Y como el
repositorio es el puerto del dominio, Qdrant cabe detrás de la misma
interfaz: cambiar de motor es un despliegue con regresión, no una reescritura.

Límites honestos del adaptador: KNN por fuerza bruta (perfecto hasta
decenas de miles de píldoras; no para millones) y un escritor a la vez.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from cocinando.dominio.modelos import Hit, Pildora

CONSTANTE_RRF = 60   # la constante del paper de RRF: dos canales, un ranking


class RepositorioPildorasSqlite:
    """La implementación por omisión del puerto RepositorioPildoras.

    Guardar es idempotente (INSERT OR REPLACE por el id de contenido);
    buscar es híbrido por contrato — nunca devuelve un solo canal sin
    declararlo en los Hit.
    """

    def __init__(self, ruta: Path, dimensiones: int = 1024) -> None:
        try:
            import sqlite_vec
        except ImportError as exc:  # pragma: no cover - aviso de instalación
            raise ImportError("pip install sqlite-vec") from exc

        self.conn = sqlite3.connect(ruta)
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)          # el canal denso, cargado como extensión
        self.conn.enable_load_extension(False)
        self.dimensiones = dimensiones
        self._esquema()

    def _esquema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS pildoras (
                id        TEXT PRIMARY KEY,
                texto     TEXT NOT NULL,
                titulo    TEXT NOT NULL,
                fuente    TEXT NOT NULL,
                orden     INTEGER NOT NULL,
                tipo      TEXT NOT NULL,
                dominio   TEXT NOT NULL,
                vigencia  TEXT
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS pildoras_fts USING fts5(
                id UNINDEXED, texto, titulo
            );
            """
        )
        columnas = [f[1] for f in self.conn.execute("PRAGMA table_info(pildoras_vec)")]
        if "embedding" not in columnas:
            self.conn.execute(
                f"CREATE VIRTUAL TABLE pildoras_vec USING vec0(embedding float[{self.dimensiones}])"
            )
        self.conn.commit()

    # ---------------------------------------------------------------- guardar

    def guardar(self, pildoras: list[Pildora], vectores: list[list[float]]) -> None:
        """Ingesta idempotente: mismo contenido, mismo id, mismo índice."""
        if len(pildoras) != len(vectores):
            raise ValueError("cada píldora necesita exactamente un vector")
        cur = self.conn.cursor()
        for pildora, vector in zip(pildoras, vectores):
            cur.execute(
                """INSERT OR REPLACE INTO pildoras
                   (id, texto, titulo, fuente, orden, tipo, dominio, vigencia)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (pildora.id, pildora.texto, pildora.titulo, pildora.fuente,
                 pildora.orden, pildora.tipo, pildora.dominio, pildora.vigencia),
            )
            rowid = cur.execute(
                "SELECT rowid FROM pildoras WHERE id = ?", (pildora.id,)
            ).fetchone()[0]
            cur.execute("DELETE FROM pildoras_fts WHERE id = ?", (pildora.id,))
            cur.execute(
                "INSERT INTO pildoras_fts (id, texto, titulo) VALUES (?, ?, ?)",
                (pildora.id, pildora.texto, pildora.titulo),
            )
            cur.execute(
                "DELETE FROM pildoras_vec WHERE rowid = ?", (rowid,)
            )
            cur.execute(
                "INSERT INTO pildoras_vec (rowid, embedding) VALUES (?, ?)",
                (rowid, __import__("struct").pack(f"{len(vector)}f", *vector)),
            )
        self.conn.commit()

    def contar(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM pildoras").fetchone()[0]

    # ----------------------------------------------------------------- buscar

    def buscar_hibrido(
        self,
        vector: list[float],
        lexico: str,
        k: int,
        dominio: str | None = None,
    ) -> list[Hit]:
        """Denso + léxico fundidos con RRF, con el dominio filtrando antes.

        Cada canal aporta su ranking; la fusión suma los recíprocos.
        Un Hit que salió por los dos canales lo declara en `canales` —
        y suele ser la mejor señal de pertinencia que existe.
        """
        import struct

        candidato_x, filtro = k * 4, ""        # margen para que el filtro no vacíe el corte
        params_denso: list = [struct.pack(f"{len(vector)}f", *vector), candidato_x]
        if dominio:
            filtro = "AND p.dominio = ?"
            params_denso.append(dominio)
        denso = {
            fila[0]: fila[1]
            for fila in self.conn.execute(
                f"""SELECT p.id, v.distance
                    FROM pildoras_vec v JOIN pildoras p ON p.rowid = v.rowid
                    WHERE v.embedding MATCH ? AND k = ? {filtro}
                    ORDER BY v.distance""",
                params_denso,
            )
        }

        lexico_consulta = " ".join(f'"{t}"' for t in lexico.split() if t)
        filtro_lex = "AND id IN (SELECT id FROM pildoras WHERE dominio = ?)" if dominio else ""
        params_lexico: list = [lexico_consulta] + ([dominio] if dominio else []) + [candidato_x]
        lexico_ranking = {
            fila[0]: fila[1]
            for fila in self.conn.execute(
                f"""SELECT id, bm25(pildoras_fts) AS score
                    FROM pildoras_fts WHERE pildoras_fts MATCH ? {filtro_lex}
                    ORDER BY score LIMIT ?""",
                params_lexico,
            )
        }

        return self._fundir(denso, lexico_ranking, k, dominio)

    def _fundir(self, denso: dict[str, float], lexico: dict[str, float],
                k: int, dominio: str | None) -> list[Hit]:
        """Reciprocal Rank Fusion: simple, robusta y sin puntuaciones mezcladas.

        Comparar el coseno del denso con el BM25 del léxico es comparar
        grados con kilos; RRF solo mira puestos.
        """
        puntuaciones: dict[str, float] = {}
        canales: dict[str, set[str]] = {}
        for nombre, ranking in (("denso", denso), ("lexico", lexico)):
            for puesto, pid in enumerate(sorted(ranking, key=ranking.get, reverse=True)):
                puntuaciones[pid] = puntuaciones.get(pid, 0.0) + 1.0 / (CONSTANTE_RRF + puesto + 1)
                canales.setdefault(pid, set()).add(nombre)

        filas = self.conn.execute(
            f"SELECT * FROM pildoras WHERE id IN ({','.join('?' * len(puntuaciones))})",
            list(puntuaciones),
        ).fetchall()
        por_id = {
            fila[0]: Pildora(texto=fila[1], titulo=fila[2], fuente=fila[3],
                             orden=fila[4], tipo=fila[5], dominio=fila[6], vigencia=fila[7])
            for fila in filas
        }
        ordenados = sorted(puntuaciones, key=puntuaciones.get, reverse=True)[:k]
        return [
            Hit(pildora=por_id[pid], score=round(puntuaciones[pid], 6),
                canales=tuple(sorted(canales[pid])))
            for pid in ordenados if pid in por_id
        ]
