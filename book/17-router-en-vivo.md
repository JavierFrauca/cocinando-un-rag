---
title: "17 · El router y la matriz en vivo"
---

# 17 · El router y la matriz en vivo

## La decisión

El quinteto de reglas del cap. 12 del libro 3, traducido a texto ejecutable: la decisión legible primero, la sofisticación medida después. La matriz es un JSON — un documento de negocio que el router **ejecuta sin sustituir** —, el orden de las reglas importa (la abstención temprana antes del gasto), y cada decisión sale con su motivo: auditable en el triaje, discutible en la reunión.

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

Y las tres puertas de salida que prueban el orden:

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

1. **El orden de las reglas ES el diseño.** La audiencia manda (es la matriz resuelta para esa persona), la composición eleva, el dominio vacío **abstiene antes de gastar**, los sistemas vivos encaminan al agente, y la omisión va al directo. Cambiar el orden cambia el sistema: una pregunta fuera de dominio que mencione "la base de datos" no pagará minutos de investigación — la regla tres la frena antes que la cuatro la dispare.
2. **La matriz es un JSON del negocio, no una constante del código.** Cambiar contratos y dominios no recompila nada: es la edición de un documento vivo que el triaje revisa — exactamente el reparto de papeles del libro 3 (el negocio decide, el router aplica).
3. **Cada decisión lleva su motivo con el número de regla.** El `motivo` es lo que el diario del cap. 18 registra y la matriz de confusión del libro 3 audita: "por qué esto fue al agente" tiene respuesta de una línea, citando la regla.
4. **Las señales de composición son una tupla editable, no un clasificador.** Aquí está el "legible y versionado" del libro 3 hecho literal: añadir una señal es añadir una palabra a una tupla con su diff — y su regresión en el cap. 16. La sofisticación (un clasificador entrenado) llega después, cuando la matriz de confusión muestre dónde el quinteto se queda corto.
5. **El router no responde: reparte.** `DecisionEncaminamiento` no lleva ni una palabra de respuesta — en esta implementación de referencia el agéntico y el iterativo se simulan escalando el servicio; los patrones completos son material del libro 3 y de la siguiente versión del repo.

## Los números

El quinteto cubre la **mayoría del encaminamiento** en los sistemas reales, como prometió el cap. 12 del libro 3 — con una precisión que viene de la matriz, no de un modelo. Cada consulta enrutada añade su fila al diario: el coste del router es una función de milisegundos y la de acierto, un porcentaje que se revisa semanalmente en el triaje.

## Enlaces

- Repo: `cocinando/aplicacion/encaminar.py` · `pruebas/test_encaminar_triaje.py`
- Web: estación [Servicio](https://ragcooking.info/biblioteca/)
- Libro 3, cap. 11: la matriz de decisión — el documento más importante del libro · Libro 3, cap. 12: el router y sus cinco señales
