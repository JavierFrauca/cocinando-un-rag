---
title: "9 · El índice: FTS5 + sqlite-vec, un archivo"
---

# 9 · El índice: FTS5 + sqlite-vec, un archivo

"Primero, instala Docker. Después, levanta el contenedor del motor vectorial. Después, configura el cluster." — así empiezan casi todos los tutoriales de RAG, y así muere la mitad de ellos: en la infraestructura, antes del método. Este capítulo empieza de otra manera: `pip install sqlite-vec`, y el lector tiene **un índice vectorial + un índice léxico BM25 en un solo archivo** que puede copiar, versionar y llevarse en el bolsillo. El archivo es la base de datos; el método es el que manda. Y cuando el día de mañana el corpus crezca más allá de lo que la fuerza bruta padece bien, Qdrant — el motor del sistema real — cabe detrás de la misma interfaz sin reescribir nada de método.

## La decisión

El doble campo del libro 1 — el texto para leer y el vector para buscar — hecho índice real: **FTS5** para el canal léxico y **sqlite-vec** para el denso, en el mismo fichero SQLite. Sin servidor, sin contenedor, sin cuenta. Los límites, dichos de entrada y sin maquillaje: el KNN de sqlite-vec es por fuerza bruta (perfecto hasta decenas de miles de píldoras, no para millones) y SQLite escribe en solitario. Ninguno de los dos límites importa en un libro de pruebas y en un corpus de despacho; ambos importarían en producción — y por eso el repositorio es el **puerto** del dominio con esta clase como primera implementación: cambiar de motor es un despliegue con regresión, no una reescritura.

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

Cómo se leerlo: tres tablas con papeles claros. `pildoras` es la verdad — el texto y el payload del cap. 6; `pildoras_fts` es el canal léxico, una tabla virtual FTS5 con el texto y el título indexados; `pildoras_vec` es el canal denso, la tabla virtual vec0 con el embedding. El `guardar` escribe en las tres dentro de una transacción: o la píldora existe en los tres sitios o en ninguno. Con un motor externo, esa atomicidad sería infraestructura; aquí es una transacción.

Y su prueba de puerta — la ingesta idempotente vista desde el índice:

```python
def test_ingesta_idempotente(repo):
    primera = _cocer(repo, DOC_A, "c24.md")
    _cocer(repo, DOC_A, "c24.md")                     # la misma ingesta, dos veces
    assert repo.contar() == len(primera)              # y el índice no crece
```

## Lo que importa

1. **El `INSERT OR REPLACE` por id de contenido ES la idempotencia.** No hay lógica de "¿ya existe?": el id del cap. 5 ya respondió esa pregunta. Re-ingestar el corpus entero cada noche es seguro por construcción — y la prueba lo demuestra con dos ingestas seguidas y un `contar()` que no se mueve. La deletreada versión (ids posicionales) duplica el índice en cada pasada y el primer síntoma es una respuesta que cita la misma tabla dos veces.
2. **El vector va empaquetado como floats nativos.** `struct.pack` de la lista: sqlite-vec consume el formato binario sin pasar por JSON — la diferencia entre una cocción de minutos y una de horas sobre el corpus entero. Un detalle de infraestructura, sí; el cap. 10 de este libro existe porque los detalles de cocción se pagan en factura.
3. **El `PRAGMA table_info` antes de crear `pildoras_vec`.** Las tablas virtuales vec0 no se pueden alterar: si mañana cambian las dimensiones del embedding, la tabla vieja no se migra — se recocina desde cero. Esta guardia evita el error de crear dos veces y deja la decisión explícita donde corresponde: en el cap. 8 y su regresión.
4. **La atomicidad de las tres escrituras.** `guardar` confirma una única transacción al final: si la cocción muere a mitad de lote, el índice queda como estaba — sin píldoras de texto sin vector, sin vectores huérfanos. Con un motor externo, sincronizar dos índices y una tabla es infraestructura seria; aquí es `commit`.
5. **El límite, escrito en el docstring y no escondido.** KNN por fuerza bruta: perfecto hasta decenas de miles de píldoras, no para millones, y un escritor a la vez. El libro dice la verdad sobre su herramienta — y la salida de crecimiento es el otro adaptador del puerto, no un parche aquí. El día que el corpus llegue a millones, el capítulo que cambia es el de configuración; este método sigue siendo el mismo.
6. **El archivo es una ventaja de gobierno, no solo de instalación.** Una base de datos copiable con `cp` se versiona, se respalda y se comparte con el mismo método que el corpus: la copia de seguridad del índice es un documento más. El motor en contenedor necesita su plan de volumen, su red y su monitorización — bien para producción; para aprender, una puerta más antes del método.

## Los números

Con las píldoras de 1.200 caracteres del cap. 5, el corpus del despacho entero cabe en **un archivo de decenas de megabytes** — copiable, versionable, sin plan de capacidad. La búsqueda híbrida del cap. 11 responde en el orden de **milisegundos** sobre decenas de miles de píldoras (dos consultas indexadas y una fusión en memoria). La cocción completa del corpus con BGE-M3 en CPU lleva el tiempo del modelo, no del índice. Y el número de frontera que conviene vigilar: **píldoras totales** — cuando pase de cinco cifras con crecimiento continuado, es el momento de invitar a Qdrant por el puerto, con la vara del cap. 15 decidiendo.

## Enlaces

- Repo: `cocinando/infraestructura/sqlite_repo.py` · `pruebas/test_repositorio.py`
- Web: fase [Almacenamiento](https://ragcooking.info/biblioteca/)
- Libro 1, cap. 12: el doble campo de origen · Libro 2, apéndice: por qué el sistema real corre sobre Qdrant y qué preguntarle a cualquier motor
