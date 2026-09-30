---
title: "18 · El panel y el triaje"
---

# 18 · El panel y el triaje

## La decisión

Las siete métricas del panel por familia (libro 3, cap. 16), leídas en cascada con **p50 y p95, nunca medias**; y la cuarta corriente del retorno (cap. 17): cada señal con destino — abstenciones al corpus, frases sin respaldo a la generación, errores de encaminamiento a la decisión. De un diario en JSONL al panel de quince minutos y las filas de triaje, en dos funciones.

## El código

`cocinando/aplicacion/triaje.py` — el panel:

```python
# cocinando/aplicacion/triaje.py
# El panel y el triaje: las siete métricas y la cuarta corriente (libro 3, caps. 16-17).

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
```

Y el triaje — la cuarta corriente repartiendo destinos:

```python
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
```

## Lo que importa

1. **`panel_semanal` sin eventos lanza excepción.** Una semana sin diario no es un panel a cero: es el sistema silencioso que el libro 3 llama "degradarse sin que nadie lo sepa". El error de la primera línea es la alarma más barata del panel.
2. **El percentil, no la media — otra vez, en código.** La escena de apertura del cap. 16 del libro 3 (la cola que engorda mientras la media sonríe) es la razón de que `percentil` exista como función propia. Con 9 consultas y una de 10 segundos, la media sonríe y el p95 grita; la prueba lo verifica.
3. **Las abstenciones se agrupan por familia antes de ir al triaje.** Cuatro "no consta" sueltos son ruido; cuatro del mismo dominio son un hueco de cobertura con nombre. El agrupamiento es lo que convierte la señal en fila de roadmap — la cuarta corriente no reparte eventos sueltos, reparte patrones.
4. **Los tres destinos del reparto son los del libro.** Corpus, generación, decisión — con su canal anotado en cada fila. Falta el cuarto (acceso, los fallos de cosecha confirmados), que llega con la evaluación en vivo del cap. 15 conectada al diario: la siguiente pieza del repo, con su hueco declarado — este libro no finge que la casa está acabada.
5. **El diario es JSONL y el panel es una función.** Sin base de datos de métricas, sin dashboards que montar: las líneas de la semana, `panel_semanal`, `filas_triaje` — y la reunión de media hora tiene su material.

## Los números

Los umbrales de alerta no viven en este código — viven en el contrato de cada audiencia (cap. 3 del libro 3) y se recalibran con treinta días de datos reales, como manda el cap. 16. La regla del panel que sí es código y doctrina a la vez: **las bandas se ponen por métrica, pero las alertas se leen por pares** — abstención baja con reintentos al alza dice más que cualquier umbral solo.

## Enlaces

- Repo: `cocinando/aplicacion/triaje.py` · `pruebas/test_encaminar_triaje.py`
- Web: fase [Gobierno](https://ragcooking.info/biblioteca/)
- Libro 3, cap. 16: el panel y los guardarraíles · Libro 3, cap. 17: la cuarta corriente, destino por destino
