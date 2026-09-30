---
title: "9 · El índice: FTS5 + sqlite-vec, un archivo"
---

# 9 · El índice: FTS5 + sqlite-vec, un archivo

## La decisión

El doble campo del libro 1 — el texto para leer y el vector para buscar — hecho índice real: **FTS5** para el canal léxico y **sqlite-vec** para el denso, en el mismo fichero SQLite. Sin servidor, sin contenedor, sin cuenta: `pip install sqlite-vec` y el lector tiene un índice vectorial en su portátil. Y como el repositorio es el puerto del dominio, Qdrant — el motor del sistema real — cabe detrás de la misma interfaz: cambiar de motor es un despliegue con regresión, no una reescritura.

## El código

`cocinando/infraestructura/sqlite_repo.py`, primera mitad — el esquema y la ingesta idempotente (la búsqueda híbrida con RRF es el cap. 11, del mismo archivo):

```python
# cocinando/infraestructura/sqlite_repo.py
# FTS5 + sqlite-vec: dos canales, un archivo.

from __future__ import annotations

import sqlite3
from pathlib import Path

from cocinando.dominio.modelos import Hit, Pildora


class RepositorioPildorasSqlite:
    """La implementación por omisión del puerto RepositorioPildoras.

    Guardar es idempotente (INSERT OR REPLACE por el id de contenido);
    buscar es híbrido por contrato — nunca devuelve un solo canal sin
    declararlo en los Hit.
    """

    def __init__(self, ruta: Path, dimensiones: int = 1024) -> None:
        try:
            import sqlite_vec
        except ImportError as exc:
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
            cur.execute("DELETE FROM pildoras_vec WHERE rowid = ?", (rowid,))
            cur.execute(
                "INSERT INTO pildoras_vec (rowid, embedding) VALUES (?, ?)",
                (rowid, struct.pack(f"{len(vector)}f", *vector)),
            )
        self.conn.commit()

    def contar(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM pildoras").fetchone()[0]
```

Y su prueba de puerta — la ingesta idempotente vista desde el índice:

```python
def test_ingesta_idempotente(repo):
    primera = _cocer(repo, DOC_A, "c24.md")
    _cocer(repo, DOC_A, "c24.md")                     # la misma ingesta, dos veces
    assert repo.contar() == len(primera)              # y el índice no crece
```

## Lo que importa

1. **Tres tablas, un solo fichero.** `pildoras` (el texto y el payload), `pildoras_fts` (el canal léxico) y `pildoras_vec` (el canal denso) comparten SQLite: la transacción que guarda una píldora la escribe en los tres sitios o en ninguno. Con un motor externo, esa atomicidad sería infraestructura; aquí es una transacción.
2. **El `INSERT OR REPLACE` por id de contenido ES la idempotencia.** No hay lógica de "¿ya existe?": el id del cap. 5 ya responde. Re-ingestar el corpus entero cada noche es seguro por construcción — y la prueba lo demuestra con dos ingestas seguidas y un `contar()` que no se mueve.
3. **El vector va empaquetado como floats nativos.** `struct.pack` de la lista: sqlite-vec consume el formato binario sin convertir a JSON — la diferencia entre una cocción de minutos y una de horas sobre el corpus entero.
4. **El `PRAGMA table_info` antes de crear `pildoras_vec`.** Las tablas virtuales vec0 no se pueden alterar: si mañana cambian las dimensiones del embedding, la tabla vieja no se migra — se recocina. Esta guardia evita el error de crear dos veces y deja la decisión explícita en el cap. 8.
5. **El límite, escrito en el docstring.** KNN por fuerza bruta: perfecto hasta decenas de miles de píldoras, no para millones, y un escritor a la vez. El libro dice la verdad sobre su herramienta — y la salida de crecimiento es el otro adaptador del puerto, no un parche aquí.

## Los números

Con las píldoras de 1.200 caracteres del cap. 5, el corpus del despacho entero cabe en **un archivo de decenas de megabytes** — copiable, versionable, sin plan de capacidad. La búsqueda híbrida del cap. 11 responde en el orden de milisegundos sobre decenas de miles de píldoras; cuando el día de mañana esa cola sea de millones, el puerto ya sabe hablar con Qdrant.

## Enlaces

- Repo: `cocinando/infraestructura/sqlite_repo.py` · `pruebas/test_repositorio.py`
- Web: fase [Almacenamiento](https://ragcooking.info/biblioteca/)
- Libro 1, cap. 12: el doble campo de origen · Libro 2, apéndice: por qué el sistema real corre sobre Qdrant y qué preguntarle a cualquier motor
