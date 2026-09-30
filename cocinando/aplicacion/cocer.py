"""Cocción: incrustar, indexar y medir el embudo (caps. 8-10).

El servicio que convierte píldoras en índice — y que nunca pierde
de vista cuánto ruido deja cada fase, porque el embudo no medido
es una factura con sorpresas.
"""

from __future__ import annotations

from cocinando.dominio.modelos import Pildora, RegistroEmbudo
from cocinando.dominio.puertos import ClienteEmbeddings, RepositorioPildoras

LOTE = 64  # píldoras por llamada al modelo: grande para el rendimiento, pequeña para el error


def cocer(pildoras: list[Pildora], embeddings: ClienteEmbeddings,
          repo: RepositorioPildoras) -> list[RegistroEmbudo]:
    """Del texto al índice, por lotes y con el embudo medido.

    Los lotes existen por dos razones de método: el error de una llamada
    no tira la cocción entera, y la factura es legible lote a lote.
    """
    embudo = [RegistroEmbudo("cocer", len(pildoras), len(pildoras))]
    vivas = [p for p in pildoras if len(p.texto) <= embeddings.VENTANA_TOKENS * 4]
    embudo.append(RegistroEmbudo("ventana", len(pildoras), len(vivas)))

    vectores: list[list[float]] = []
    for i in range(0, len(vivas), LOTE):
        tro = vivas[i:i + LOTE]
        vectores.extend(embeddings.incrustar([p.texto for p in tro]))
    repo.guardar(vivas, vectores)

    embudo.append(RegistroEmbudo("indexado", len(vivas), repo.contar()))
    return embudo


def leer_embudo(embudo: list[RegistroEmbudo]) -> str:
    """El embudo, en una línea por fase — el ruido donde se vea."""
    return "\n".join(
        f"{r.fase}: {r.salieron}/{r.entraron} (ruido {r.ruido:.1%})" for r in embudo
    )
