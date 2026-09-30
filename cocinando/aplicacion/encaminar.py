"""El router: las cinco reglas escritas y la matriz en JSON (libro 3, caps. 11-12).

Decisión legible primero, sofisticación medida después. Cada regla es
discutible en el triaje; ninguna es una red neuronal inescrutable.
"""

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
