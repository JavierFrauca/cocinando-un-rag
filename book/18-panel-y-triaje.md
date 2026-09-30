---
title: "18 · El panel y el triaje"
---

# 18 · El panel y el triaje

El panel del cap. 16 del libro 3 era un panel tranquilo — todo verde, todo dentro de umbrales — mientras el equipo juraba que el asistente iba más lento. Tenían la sensación y no el dato, porque la media sonreía mientras la cola engordaba. Este capítulo es la vacuna de esa mañana: **de un diario de eventos en JSONL a las siete métricas con p50 y p95 — nunca medias — y a las filas de triaje con destino**. La reunión de media hora que cierra el ciclo de la serie entera empieza aquí, y su material cabe en dos funciones.

## La decisión

Dos decisiones y ambas de disciplina. **El panel se calcula, no se monta**: sin base de datos de métricas ni dashboard que mantener — las líneas de la semana, `panel_semanal`, `filas_triaje`, y la reunión tiene su material. **El p50 y el p95 son la única forma honesta de prometer latencia**, porque los usuarios no viven en la media: viven en la cola — y la función `percentil` es corta a propósito, para que nadie tenga excusa de calcular otra cosa. Y sobre el triaje, la regla que la serie repite desde el libro 2: **ninguna señal sin destino** — lo inaceptable no es la cola, es la señal sin destino.

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

Y la prueba que fija las dos doctrinas en `assert`:

```python
def test_siete_metricas_con_p95_no_media():
    eventos = [_evento(latencia_s=l) for l in (1.0, 1.0, 1.0, 2.0, 10.0)] + [...]
    panel = panel_semanal(eventos)
    assert panel.latencia_p95 > panel.latencia_p50     # la cola, donde viven los usuarios
    ...

def test_triaje_reparte_destinos():
    eventos = [_evento(abstencion=True), _evento(frases_sin_respaldo=1), _evento(acierto_router=False)]
    filas = filas_triaje(eventos)
    destinos = {f["destino"] for f in filas}
    assert destinos == {"corpus", "generación", "decisión"}   # tres señales, tres destinos
```

## Lo que importa

1. **`panel_semanal` sin eventos lanza excepción.** Una semana sin diario no es un panel a cero: es el sistema silencioso que el libro 3 llama "degradarse sin que nadie lo sepa". El error de la primera línea es la alarma más barata del panel — y su mensaje dice la verdad doble: o el panel no se alimenta, o el sistema no vive.
2. **El percentil, no la media — otra vez, en código.** La escena de apertura del cap. 16 del libro 3 (la cola que engorda mientras la media sonríe) es la razón de que `percentil` exista como función propia y de que la prueba la ejerza con una cola de verdad: nueve consultas, la más lenta diez segundos, y el `assert` exigiendo que el p95 la vea. La media habría sonreído; el p95 grita.
3. **Las abstenciones se agrupan por familia antes de ir al triaje.** Cuatro "no consta" sueltos son ruido; cuatro del mismo dominio son un hueco de cobertura con nombre. El agrupamiento es lo que convierte la señal en fila de roadmap — la cuarta corriente no reparte eventos sueltos, **reparte patrones**: es la diferencia entre una lista de quejas y un plan de corpus.
4. **Los tres destinos del reparto son los del libro.** Corpus, generación, decisión — con su canal anotado en cada fila. Falta el cuarto (acceso, los fallos de cosecha confirmados por la respuesta), que llega conectando la vara del cap. 15 al diario: cada suspensión del juez con contexto pobre es una fila para el dataset del acceso. Está declarado aquí y en el repo — este libro no finge que la casa está acabada.
5. **El diario es JSONL y el panel es una función.** Sin base de datos de métricas, sin dashboards que montar, sin un proveedor de observabilidad para empezar: cada respuesta appendea una línea y la reunión de media hora tiene su material. Cuando el volumen pida más — retención, agregación, historia — el libro 2 ya dio la política (cap. 20: registrar decisiones, retención con política) y la función cambia de fuente, no de método.
6. **La lectura en cascada, escrita en el dataclass.** El orden de los campos de `PanelSemanal` es el orden de lectura del libro 3: volumen primero (qué semana ha traído el tráfico), router después (qué encaminó mal), latencia y coste, abstenciones, reintentos, fidelidad al final — de la causa a la consecuencia. Un panel no se lee en cualquier orden; el que lo lee al revés diagnostica consecuencias sin causas.

## Los números

Los umbrales de alerta no viven en este código — viven en el contrato de cada audiencia (cap. 3 del libro 3) y se recalibran con **treinta días de datos reales**, como manda el cap. 16: el error común es fijar umbrales perfectos antes de tener base. La regla del panel que sí es código y doctrina a la vez: **las bandas se ponen por métrica, pero las alertas se leen por pares** — abstención baja con reintentos al alza dice más que cualquier umbral solo, porque cada métrica se disimula en otra. Y el número del círculo completo — el tiempo desde que una respuesta delata una carencia hasta que la carencia está resuelta — es el que esta reunión deja escrito semana a semana: su tendencia cayendo es la prueba de que el organismo aprende.

## Enlaces

- Repo: `cocinando/aplicacion/triaje.py` · `pruebas/test_encaminar_triaje.py`
- Web: fase [Gobierno](https://ragcooking.info/biblioteca/)
- Libro 3, cap. 16: el panel y los guardarraíles · Libro 3, cap. 17: la cuarta corriente, destino por destino · Cap. 17 de este libro: el diario que este panel lee
