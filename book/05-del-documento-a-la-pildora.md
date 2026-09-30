---
title: "5 · Del documento a la píldora: el chunking"
---

# 5 · Del documento a la píldora: el chunking

## La decisión

El corpus de la serie se construye sobre la **píldora de información**: la unidad mínima autocontenida, con su texto legible, su referencia y sus metadatos (libro 1, caps. 10-11). La puerta de salida de la fase es verificable — *píldora íntegra; tablas sin cortar* —, y dos decisiones del método gobiernan el código: la estructura del documento es el corte natural (el chunking semántico empieza en el formato que el redactor ya dio), y la tabla es atómica — una tabla partida en dos es dos medias verdades.

## El código

El corte vive en el dominio — lógica pura, sin I/O: el chunking no sabe qué embedding lo cocerá. `cocinando/dominio/pildoras.py` — del documento a la lista de píldoras, en una pasada:

```python
# cocinando/dominio/pildoras.py — del documento a la píldora
# Capítulo escrito contra la v0.1 del repositorio de los ejemplos.

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

MAX_PILDORA = 1200  # caracteres: guardia contra bloques sin estructura, no objetivo

ENCABEZADO = re.compile(r"^(#{1,4})\s+(.+)$")


@dataclass
class Pildora:
    texto: str                  # lo que leerá el modelo: título de contexto + contenido
    titulo: str                 # ruta de encabezados del documento
    fuente: str                 # documento de origen, con su versión
    orden: int                  # posición en el documento: la usa el ensamblado
    tipo: str                   # "texto" | "tabla": lo usan el ensamblado y la vara
    dominio: str = ""
    vigencia: str | None = None

    @property
    def id(self) -> str:
        # La identidad nace del CONTENIDO, no de la posición:
        # re-ingestar un documento sin cambios no crea píldoras nuevas.
        digesto = hashlib.sha1(f"{self.fuente}|{self.texto}".encode()).hexdigest()[:16]
        return f"{digesto}-{self.orden:03d}"


class _Estado:
    """Lo que acumula la píldora en curso mientras se recorre el documento."""

    def __init__(self, fuente: str, dominio: str) -> None:
        self.fuente = fuente
        self.dominio = dominio
        self.titulo: list[str] = []   # la ruta de encabezados viva
        self.bloque: list[str] = []
        self.orden = 0
        self.en_tabla = False

    def subir(self, nivel: int, texto: str) -> None:
        self.titulo = self.titulo[: nivel - 1] + [texto]

    def cerrar(self, pildoras: list[Pildora]) -> None:
        texto = "\n".join(self.bloque).strip()
        if texto:
            ruta = " > ".join(self.titulo) if self.titulo else "(portada)"
            pildoras.append(Pildora(
                texto=f"[{ruta}]\n\n{texto}",      # el chunking contextual: el contexto viaja con el trozo
                titulo=ruta,
                fuente=self.fuente,
                orden=self.orden,
                tipo="tabla" if self.en_tabla else "texto",
                dominio=self.dominio,
            ))
            self.orden += 1
        self.bloque = []
        self.en_tabla = False


def trocear(documento: str, fuente: str, dominio: str = "") -> list[Pildora]:
    estado = _Estado(fuente, dominio)
    for linea in documento.splitlines():
        encabezado = ENCABEZADO.match(linea)
        if encabezado:
            estado.cerrar(pildoras)                 # la estructura manda: un encabezado cierra
            estado.subir(len(encabezado.group(1)), encabezado.group(2).strip())
            continue
        if linea.lstrip().startswith("|"):
            if not estado.en_tabla:
                estado.cerrar(pildoras)             # la tabla no se mezcla con la prosa
                estado.en_tabla = True
            estado.bloque.append(linea)
            continue
        if estado.en_tabla:
            estado.cerrar(pildoras)                 # la tabla terminó: sale entera
        estado.bloque.append(linea)
        if len("\n".join(estado.bloque)) >= MAX_PILDORA:
            estado.cerrar(pildoras)                 # la guardia: corta en el borde de línea
    estado.cerrar(pildoras)
    return pildoras
```

Y su puerta de salida, como toda la serie manda — la prueba que este capítulo debe pasar:

```python
# pruebas/test_pildoras.py

from cocinando.pildoras import trocear


def test_tabla_atomica():
    doc = "# Uso\nTexto de uso.\n| Col A | Col B |\n|---|---|\n| 1 | 2 |\nPie de tabla.\n"
    pildoras = trocear(doc, fuente="prueba.md")
    tablas = [p for p in pildoras if p.tipo == "tabla"]
    assert len(tablas) == 1
    assert "| 1 | 2 |" in tablas[0].texto           # entera
    assert "Texto de uso" not in tablas[0].texto    # sin mezclar con la prosa


def test_contexto_viaja_con_el_trozo():
    doc = "# Convenio 2024\n## 3. Plazos\nEl plazo de reclamación es de veinte días.\n"
    (pildora,) = trocear(doc, fuente="c24.md")
    assert pildora.texto.startswith("[Convenio 2024 > 3. Plazos]")


def test_identidad_idempotente():
    a = trocear(DOC, fuente="x.md")
    b = trocear(DOC, fuente="x.md")
    assert [p.id for p in a] == [p.id for p in b]   # re-ingestar no duplica
```

## Lo que importa

1. **Un encabezado cierra la píldora.** El corte natural ya está en el documento: el redactor le dio estructura, y esa estructura es semántica gratis. Los troceadores de tamaño fijo la destruyen — cortan frases por la mitad y obligan al solape a remendar lo roto. Aquí la estructura manda y el tamaño solo arbitra.
2. **Las tablas son atómicas y viajan con tipo propio.** Una tabla cortada en dos píldoras produce lo que el cap. 14 del libro 3 llama extrapolación: el modelo recibe la mitad numérica y completa el resto con imaginación. La tabla entra, se completa y sale entera, marcada `tipo="tabla"` para que el ensamblado (libro 2, cap. 17) la trate distinto de la prosa.
3. **El encabezado viaja con el texto.** El prefijo `[Convenio 2024 > 3. Plazos]` es el *chunking contextual*: el embedding se cocina con el contexto dentro, la búsqueda encuentra la píldora por su contenido, y el modelo que la recibe aislada sabe de qué habla. Sin él, cada píldora es un huérfano que el modelo rellena con lo que le parece.
4. **La identidad nace del contenido, no de la posición.** El `id` es el hash de fuente+texto: re-ingestar el mismo documento no duplica el índice, y cambiar un párrafo solo regenera las píldoras afectadas. Es la **manutención idempotente** del libro 1 (caps. 18 y 20) hecha una línea de código — sin ella, la ingesta semanal duplica el corpus en silencio.
5. **El máximo es una guardia, no un objetivo.** El corte por tamaño solo dispara cuando un bloque desborda, y corta en el borde de línea más próximo — nunca dentro de una tabla ni a mitad de palabra. Si la guardia dispara a menudo, el problema no es el número: es que la estructura de encabezados del documento es demasiado gruesa, y eso se arregla aguas arriba.
6. **Sin solape.** El *overlap* de los troceadores de tamaño fijo no existe aquí por decisión: el solape es duplicidad, y la duplicidad la paga el ensamblado (el libro 2, cap. 14, la llama fotocopia). El contexto que un trozo "olvida" viaja en su título, no repitiendo el texto del vecino.

## Los números

- **1.200 caracteres** es el valor por omisión del repositorio — del orden de 300 tokens en español. El techo real lo fija tu modelo de embeddings: su ventana de tokens menos lo que ocupe el título de contexto (la [fase Embedding de la web](https://ragcooking.info/biblioteca/embedding/) lleva la tabla de ventanas por modelo). El número definitivo lo confirma tu vara, no este libro.
- Una **tabla que desborda la ventana del embedding no se corta aquí**: va entera al índice y se truncará al cocer. Eso no se arregla en esta fase — se detecta en la medición del ruido (cap. 10), y su arreglo es de estructura del documento, no de esta función.
- La fuente lleva **versión** (`fuente="convenio_2024@v3"` en el sistema real): el id hereda la versión, y una revisión del convenio genera píldoras nuevas que conviven con las viejas hasta que el ciclo de vida retira las muertas — tal como manda el libro 1.

## Enlaces

- Repo: `cocinando/dominio/pildoras.py` · `pruebas/test_pildoras.py`
- Web: [fase Chunking](https://ragcooking.info/biblioteca/chunking/) · [fase Estructura](https://ragcooking.info/biblioteca/estructura/)
- Libro 1, caps. 10-11: chunking contextual y tablas atómicas · Libro 2, caps. 14 y 17: la diversidad y el ensamblado que reciben estas píldoras · Libro 3, cap. 14: la extrapolación que este corte evita
