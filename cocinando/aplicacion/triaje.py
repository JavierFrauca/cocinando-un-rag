"""El panel y el triaje: las siete métricas y la cuarta corriente (libro 3, caps. 16-17).

De un diario de eventos en JSONL a las siete métricas por familia
y las filas de triaje con destino. Quince minutos de lectura, ni uno más.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from cocinando.dominio.modelos import EventoRespuesta


def cargar_diario(fichero: Path) -> list[EventoRespuesta]:
    """El diario de respuestas servidas: un evento JSONL por consulta."""
    eventos = []
    for linea in fichero.read_text("utf-8").splitlines():
        if linea.strip():
            eventos.append(EventoRespuesta(**json.loads(linea)))
    return eventos


def percentil(valores: list[float], q: float) -> float:
    """El percentil honesto: los usuarios viven en la cola, no en la media."""
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    return ordenados[int(q * (len(ordenados) - 1))]


@dataclass
class PanelSemanal:
    """Las siete métricas del libro 3, leídas en cascada.

    volumen → router → latencia/coste → abstenciones → reintentos → fidelidad.
    """

    volumen: int
    latencia_p50: float
    latencia_p95: float
    coste_tokens: int
    tasa_abstencion: float
    tasa_reintentos: float
    acierto_router: float | None
    frases_sin_respaldo: int
    por_familia: dict[str, int]


def panel_semanal(eventos: list[EventoRespuesta]) -> PanelSemanal:
    """Las siete métricas sobre el diario de la semana — p50 y p95, nunca medias."""
    if not eventos:
        raise ValueError("semana sin eventos: o el panel no se alimenta, o el sistema no vive")
    familias: dict[str, int] = {}
    for e in eventos:
        familias[e.familia] = familias.get(e.familia, 0) + 1
    latencias = [e.latencia_s for e in eventos]
    con_router = [e for e in eventos if e.acierto_router is not None]
    return PanelSemanal(
        volumen=len(eventos),
        latencia_p50=percentil(latencias, 0.50),
        latencia_p95=percentil(latencias, 0.95),
        coste_tokens=sum(e.coste_tokens for e in eventos),
        tasa_abstencion=sum(e.abstencion for e in eventos) / len(eventos),
        tasa_reintentos=sum(1 for e in eventos if e.escalas > 0) / len(eventos),
        acierto_router=(
            sum(bool(e.acierto_router) for e in con_router) / len(con_router)
            if con_router else None
        ),
        frases_sin_respaldo=sum(e.frases_sin_respaldo for e in eventos),
        por_familia=familias,
    )


def filas_triaje(eventos: list[EventoRespuesta]) -> list[dict]:
    """La cuarta corriente: cada señal con su destino (libro 3, cap. 17).

    Ninguna señal sin destino, responsable y semana límite —
    lo inaceptable no es la cola, es la señal sin destino.
    """
    filas: list[dict] = []
    abstenciones = [e for e in eventos if e.abstencion]
    if abstenciones:
        familias = {}
        for e in abstenciones:
            familias[e.familia] = familias.get(e.familia, 0) + 1
        filas.append({
            "señal": "abstenciones agrupadas",
            "detalle": familias,
            "destino": "corpus",
            "canal": "roadmap de cobertura",
        })
    sin_respaldo = sum(1 for e in eventos if e.frases_sin_respaldo > 0)
    if sin_respaldo:
        filas.append({
            "señal": "respuestas con frases sin respaldo",
            "detalle": f"{sin_respaldo} respuestas",
            "destino": "generación",
            "canal": "plantilla con hipótesis y regresión",
        })
    fallos_router = [e for e in eventos if e.acierto_router is False]
    if fallos_router:
        filas.append({
            "señal": "errores de encaminamiento",
            "detalle": f"{len(fallos_router)} consultas",
            "destino": "decisión",
            "canal": "matriz de confusión del router",
        })
    return filas
