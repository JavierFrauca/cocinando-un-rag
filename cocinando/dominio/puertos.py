"""Los puertos: los contratos que el dominio exige y la infraestructura cumple.

Cada Protocol es un contrato de la serie hecho interfaz. Las capas superiores
los orquestan sin saber quién los implementa: SQLite o Qdrant, BGE-M3 o una API,
un LLM u otro — el método no cambia.
"""

from __future__ import annotations

from typing import Protocol

from cocinando.dominio.modelos import (
    Consulta,
    Hit,
    Pildora,
    Respuesta,
    Veredicto,
)


class ClienteEmbeddings(Protocol):
    """El puerto de la cocción vectorial. Dos adaptadores: local y de API."""

    VENTANA_TOKENS: int          # el techo real del tamaño de la píldora
    DIMENSIONES: int

    def incrustar(self, textos: list[str]) -> list[list[float]]:
        """Textos dentro, vectores fuera — normalizados, listos para coseno."""
        ...


class RepositorioPildoras(Protocol):
    """El contrato de recuperación hecho interfaz (libro 2, cap. 3).

    Guardar es idempotente: dos ingestas del mismo documento dejan el mismo
    índice. Buscar es híbrido por contrato — ninguna implementación puede
    devolver solo un canal sin declararlo.
    """

    def guardar(self, pildoras: list[Pildora], vectores: list[list[float]]) -> None: ...

    def buscar_hibrido(
        self,
        vector: list[float],
        lexico: str,
        k: int,
        dominio: str | None = None,
    ) -> list[Hit]: ...

    def contar(self) -> int: ...


class ReescritorConsulta(Protocol):
    """Normaliza y reescribe ANTES de la primera búsqueda: la pieza que faltaba.

    Determinista primero (ortografía, jerga del corpus), semántico después.
    Nunca responde: solo reescribe.
    """

    def reescribir(self, consulta: Consulta) -> Consulta: ...


class JuezCosecha(Protocol):
    """El juez de cosecha: veredictos cerrados sobre lo recuperado (libro 2, cap. 16).

    Certifica encaje consulta-cosecha, no verdad jurídica.
    """

    def veredictar(self, consulta: Consulta, cosecha: list[Hit]) -> Veredicto: ...


class Generador(Protocol):
    """El generador ensamblador (libro 3, cap. 13): componer, nunca; ensamblar, siempre."""

    def generar(self, consulta: Consulta, cosecha: list[Hit]) -> Respuesta: ...
