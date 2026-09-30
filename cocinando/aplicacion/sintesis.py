"""La síntesis Gold con guía humana (libro 1, caps. 13-15).

El Gold no se genera solo: se firma. Esta pieza es pequeña a propósito —
toda su inteligencia está en la puerta que no deja pasar una síntesis
sin nombre y apellidos detrás.
"""

from __future__ import annotations

from cocinando.dominio.modelos import Pildora


def registrar_sintesis(texto: str, dominio: str, firmada_por: str,
                       fuente: str = "gold/sintesis") -> Pildora:
    """Da de alta una síntesis Gold — si y solo si una persona la firma.

    La regla de la serie: quien resuelve a mano, firma la verdad.
    Un ValueError aquí no es un fastidio: es la frontera entre el corpus
    y lo que el LLM se inventaría por su cuenta.
    """
    if not firmada_por.strip():
        raise ValueError("una síntesis Gold sin firma humana no entra en el corpus")
    return Pildora(
        texto=f"[Síntesis · {dominio} · firmada por {firmada_por}]\n\n{texto}",
        titulo=f"Síntesis Gold · {dominio}",
        fuente=fuente,
        orden=0,
        tipo="sintesis",
        dominio=dominio,
    )
