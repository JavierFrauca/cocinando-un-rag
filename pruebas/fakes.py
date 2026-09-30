"""Los dobles de prueba: deterministas, sin red, sin claves, sin modelos.

Un juez falso, un reescritor falso y unos embeddings falsos que comparten
diccionario — la prueba tiene que poder correr en la CI de un portátil.
Los adaptadores reales (BGE-M3, OpenAI) se prueban a mano contra el
sistema real; aquí se prueba el método.
"""

from __future__ import annotations

from cocinando.dominio.modelos import Consulta, Hit, Respuesta, Veredicto
from cocinando.infraestructura.embeddings_demo import ClienteEmbeddingsDemo

# El doble de embeddings ES el adaptador de demostración del paquete:
# el mismo código sirve para las pruebas y para `sembrar.py --embeddings demo`.
EmbeddingsFalsos = ClienteEmbeddingsDemo


class ReescritorFalso:
    """La reescritura determinista del sistema de pruebas: da igual, cuenta veces."""

    def __init__(self) -> None:
        self.veces = 0

    def reescribir(self, consulta: Consulta) -> Consulta:
        self.veces += 1
        return consulta


class JuezFalso:
    """El juez que responde lo que la prueba le programa."""

    def __init__(self, veredicto: Veredicto = Veredicto.RESPONDE) -> None:
        self._veredicto = veredicto
        self.consultas_vistas = 0

    def veredictar(self, consulta: Consulta, cosecha: list[Hit]) -> Veredicto:
        self.consultas_vistas += 1
        return self._veredicto


class GeneradorFalso:
    """El generador que devuelve lo que la prueba le programa."""

    def __init__(self, texto: str = "El plazo es de veinte días. [Fuente 1]") -> None:
        self._texto = texto
        self.ultima_cosecha: list[Hit] | None = None

    def generar(self, consulta: Consulta, cosecha: list[Hit]) -> Respuesta:
        self.ultima_cosecha = cosecha
        return Respuesta(texto=self._texto, citas=tuple(f"Fuente {i + 1}" for i in range(len(cosecha))))
