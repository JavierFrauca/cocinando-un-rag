"""La puerta de salida de los caps. 17-18: las cinco reglas y las siete métricas."""

import json

from cocinando.aplicacion.encaminar import Encaminador
from cocinando.aplicacion.triaje import filas_triaje, panel_semanal
from cocinando.dominio.modelos import Consulta, EventoRespuesta

MATRIZ = {
    "dominios": ["convenios", "sentencias"],
    "contratos": {"letrado": "exhaustividad", "gestora": "segundos"},
}


def test_regla_uno_audiencia_exhaustividad(tmp_path):
    matriz = tmp_path / "matriz.json"
    matriz.write_text(json.dumps(MATRIZ), encoding="utf-8")
    decision = Encaminador(matriz).encaminar(Consulta(texto="plazo", audiencia="letrado"))
    assert decision.patron == "agentic"                # la audiencia manda aunque parezca fácil


def test_regla_tres_abstencion_antes_del_gasto(tmp_path):
    matriz = tmp_path / "matriz.json"
    matriz.write_text(json.dumps(MATRIZ), encoding="utf-8")
    decision = Encaminador(matriz).encaminar(
        Consulta(texto="stock", audiencia="gestora", dominio="inventario"))
    assert decision.patron == "abstencion"             # el guard antes de los patrones caros


def test_regla_cinco_omision_directo(tmp_path):
    matriz = tmp_path / "matriz.json"
    matriz.write_text(json.dumps(MATRIZ), encoding="utf-8")
    decision = Encaminador(matriz).encaminar(Consulta(texto="cuántos días tengo", audiencia="gestora"))
    assert decision.patron == "directo"


def _evento(**k):
    base = dict(consulta="x", patron="directo", latencia_s=1.0, coste_tokens=100,
                abstencion=False, familia="plazos", fecha="2026-09-30T10:00:00")
    base.update(k)
    return EventoRespuesta(**base)


def test_siete_metricas_con_p95_no_media():
    eventos = [_evento(latencia_s=l) for l in (1.0, 1.0, 1.0, 2.0, 10.0)] + [
        _evento(latencia_s=1.0, abstencion=True),
        _evento(latencia_s=1.0, escalas=1),
        _evento(latencia_s=1.0, acierto_router=False),
        _evento(latencia_s=1.0, frases_sin_respaldo=2, familia="salarios"),
    ]
    panel = panel_semanal(eventos)
    assert panel.volumen == 9
    assert panel.latencia_p95 > panel.latencia_p50     # la cola, donde viven los usuarios
    assert abs(panel.tasa_abstencion - 1 / 9) < 1e-9
    assert panel.por_familia == {"plazos": 8, "salarios": 1}


def test_triaje_reparte_destinos():
    eventos = [_evento(abstencion=True), _evento(frases_sin_respaldo=1), _evento(acierto_router=False)]
    filas = filas_triaje(eventos)
    destinos = {f["destino"] for f in filas}
    assert destinos == {"corpus", "generación", "decisión"}   # tres señales, tres destinos
