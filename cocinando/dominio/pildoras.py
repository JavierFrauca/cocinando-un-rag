"""Del documento a la píldora: la lógica pura del chunking (libro 1, caps. 10-11).

Este módulo no hace I/O ni conoce el índice: el chunking no sabe
qué embedding lo cocerá. Todo lo que entra y sale vive en el dominio.
"""

from __future__ import annotations

import re

from cocinando.dominio.modelos import MAX_PILDORA, Pildora

ENCABEZADO = re.compile(r"^(#{1,4})\s+(.+)$")


class _Estado:
    """Lo que acumula la píldora en curso mientras se recorre el documento."""

    def __init__(self, fuente: str, dominio: str, vigencia: str | None) -> None:
        self.fuente = fuente
        self.dominio = dominio
        self.vigencia = vigencia
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
                vigencia=self.vigencia,
            ))
            self.orden += 1
        self.bloque = []
        self.en_tabla = False


def trocear(documento: str, fuente: str, dominio: str = "",
            vigencia: str | None = None) -> list[Pildora]:
    """Corta un documento en píldoras: la estructura manda, las tablas son atómicas.

    La guardia de tamaño (MAX_PILDORA) existe para bloques sin estructura;
    si dispara a menudo, el problema es del documento, no del número.
    """
    estado = _Estado(fuente, dominio, vigencia)
    pildoras: list[Pildora] = []
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
