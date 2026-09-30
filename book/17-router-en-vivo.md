---
title: "17 · El router y la matriz en vivo"
---

# 17 · El router y la matriz en vivo

El piloto del cap. 12 del libro 3 investigaba *todo* — la pregunta de stock de toda la vida consumiendo cuatro minutos de planificación, herramientas y verificación — porque no tenía filtro de entrada: un caño único por donde pasaba todo a la misma velocidad. La vacuna cabe en cinco reglas escritas. Este capítulo es ese quinteto hecho código: la matriz como JSON que el negocio edita, las señales como tuplas que el triaje discute, cada decisión con su motivo citando la regla — **decisión legible primero, sofisticación medida después**.

## La decisión

El router ejecuta la matriz en vivo: consulta a consulta, sin guardar la cola. Tres decisiones de arquitectura lo sostienen. **La matriz es un documento del negocio** — un JSON versionado, no una constante del código: cambiar contratos y dominios no recompila nada, es la edición de un documento vivo que el triaje revisa. **El orden de las reglas ES el diseño** — la audiencia manda, la composición eleva, el dominio vacío abstiene antes del gasto, los sistemas vivos van al agente, y la omisión cae al directo. **Cada decisión lleva su motivo citando la regla** — "por qué esto fue al agente" tiene respuesta de una línea, auditable en el triaje.

## El código

`cocinando/aplicacion/encaminar.py`, completo:

```python
# cocinando/aplicacion/encaminar.py
# El router: las cinco reglas escritas y la matriz en JSON (libro 3, caps. 11-12).

from __future__ import annotations

import json
from pathlib import Path

from cocinando.dominio.modelos import Consulta, DecisionEncaminamiento

# Las señales de composición del cap. 5 del libro 3, traducidas a texto ejecutable.
SENALES_COMPOSICION = ("¿qué", "¿cuáles", "¿en cuáles", "diferencia", "compar",
                       "lista de", "todos los", "por cada")
SENALES_OPERACION = ("calcula", "nuestra base de datos", "el expediente", "sistema vivo", "base de datos")


class Encaminador:
    """El quinteto de reglas del cap. 12 del libro 3, en el orden que importa.

    La abstención se comprueba antes de encaminar a los patrones caros:
    ninguna investigación paga un vacío.
    """

    def __init__(self, fichero_matriz: Path) -> None:
        # La matriz es un documento de negocio: el router la ejecuta, no la sustituye.
        self.matriz: dict = json.loads(fichero_matriz.read_text("utf-8"))
        self.contratos: dict[str, str] = self.matriz.get("contratos", {})

    def encaminar(self, consulta: Consulta) -> DecisionEncaminamiento:
        # Regla uno: la audiencia manda — es la matriz ya resuelta para esa persona.
        contrato = self.contratos.get(consulta.audiencia, "")
        if contrato == "exhaustividad":
            return DecisionEncaminamiento(
                patron="agentic",
                motivo="regla uno: contrato de exhaustividad → patrón alto de partida",
                senales=("audiencia",),
            )

        texto = consulta.texto.lower()

        # Regla dos: señales de composición → iterativo como mínimo.
        if any(s in texto for s in SENALES_COMPOSICION):
            return DecisionEncaminamiento(
                patron="iterativo",
                motivo="regla dos: señales de composición → iterativo como mínimo",
                senales=("composicion",),
            )

        # Regla tres: dominios que no existen → abstención temprana, antes del gasto.
        dominios = set(self.matriz.get("dominios", []))
        if consulta.dominio and consulta.dominio not in dominios:
            return DecisionEncaminamiento(
                patron="abstencion",
                motivo=f"regla tres: dominio '{consulta.dominio}' fuera del corpus",
                senales=("dominios",),
            )

        # Regla cuatro: sistemas vivos u operaciones → agéntico.
        if any(s in texto for s in SENALES_OPERACION):
            return DecisionEncaminamiento(
                patron="agentic",
                motivo="regla cuatro: menciona sistemas vivos o pide operaciones → agéntico",
                senales=("operacion",),
            )

        # Regla cinco: la familia por omisión va al directo, con la réplica de guardia.
        return DecisionEncaminamiento(
            patron="directo",
            motivo="regla cinco: sin señal alguna → directo con réplica de guardia",
            senales=(),
        )
```

La matriz que lo alimenta es tan legible como todo en esta serie:

```json
{
  "dominios": ["convenios", "sentencias", "circulares"],
  "contratos": {"letrado": "exhaustividad", "gestora": "segundos", "portal": "segundos"}
}
```

Y las tres puertas de salida que prueban el orden — el orden que importa:

```python
def test_regla_uno_audiencia_exhaustividad(tmp_path):
    ...
    decision = Encaminador(matriz).encaminar(Consulta(texto="plazo", audiencia="letrado"))
    assert decision.patron == "agentic"                # la audiencia manda aunque parezca fácil

def test_regla_tres_abstencion_antes_del_gasto(tmp_path):
    ...
    decision = Encaminador(matriz).encaminar(
        Consulta(texto="stock", audiencia="gestora", dominio="inventario"))
    assert decision.patron == "abstencion"             # el guard antes de los patrones caros

def test_regla_cinco_omision_directo(tmp_path):
    ...
    decision = Encaminador(matriz).encaminar(Consulta(texto="cuántos días tengo", audiencia="gestora"))
    assert decision.patron == "directo"
```

## Lo que importa

1. **El orden de las reglas ES el diseño.** La audiencia manda (es la matriz resuelta para esa persona), la composición eleva, el dominio vacío **abstiene antes de gastar**, los sistemas vivos encaminan al agente, y la omisión va al directo. Cambiar el orden cambia el sistema: una pregunta fuera de dominio que mencione "la base de datos" no pagará minutos de investigación — la regla tres la frena antes de que la cuatro la dispare. La prueba de la regla tres existe precisamente para fijar ese orden en un `assert`.
2. **La matriz es un JSON del negocio, no una constante del código.** Cambiar contratos y dominios no recompila nada: es la edición de un documento vivo que el triaje revisa — exactamente el reparto de papeles del libro 3 (el negocio decide, el router aplica). Y como todo documento vivo de la serie, el JSON lleva su fecha de revisión en el Git: la matriz de hace tres meses explica las decisiones de hace tres meses.
3. **Cada decisión lleva su motivo con el número de regla.** El `motivo` es lo que el diario del cap. 18 registra y la matriz de confusión del libro 3 audita: "por qué esto fue al agente" tiene respuesta de una línea. Sin motivo, el router es un oráculo; con motivo, es un funcionario que firma lo que hace.
4. **Las señales de composición son una tupla editable, no un clasificador.** Aquí está el "legible y versionado" del libro 3 hecho literal: añadir una señal es añadir una palabra a una tupla con su diff — y su regresión en el cap. 16. La sofisticación (un clasificador entrenado con las familias) llega después, cuando la matriz de confusión muestre dónde el quinteto se queda corto; y cuando llegue, no sustituye la matriz: la lee mejor.
5. **El router no responde: reparte.** `DecisionEncaminamiento` no lleva ni una palabra de respuesta — en esta implementación de referencia el iterativo y el agéntico se simulan escalando el servicio; los patrones completos son material del libro 3 (caps. 5-8) y de la siguiente versión del repo. Lo que ya es real aquí es lo que el cap. 12 del libro 3 pidió primero: **el filtro de entrada**, que es lo que al piloto le faltaba.
6. **Lo que falta, declarado: la señal de historia.** La cuarta señal del libro 3 — la repetición como firma del falso barato — necesita el diario de consultas pasadas para leerse, y el diario llega con el panel del cap. 18. Cuando se conecten, la regla dos gana su lectura en segunda visita: el router que corrige en la repetición lo que la primera pasada se dejó.

## Los números

El quinteto cubre la **mayoría del encaminamiento** en los sistemas reales, como prometió el cap. 12 del libro 3 — con una precisión que viene de la matriz, no de un modelo, y a coste de **milisegundos**: cinco comparaciones de strings y una consulta a un JSON cargado en memoria. Cada consulta enrutada añade su fila al diario con su motivo: la tasa de acierto contra la matriz — la matriz de confusión del cap. 12 — se revisa semanalmente en el triaje, que es donde este capítulo y el siguiente se dan la mano.

## Enlaces

- Repo: `cocinando/aplicacion/encaminar.py` · `pruebas/test_encaminar_triaje.py`
- Web: estación [Servicio](https://ragcooking.info/biblioteca/)
- Libro 3, cap. 11: la matriz de decisión — el documento más importante del libro · Libro 3, cap. 12: el router y sus cinco señales
