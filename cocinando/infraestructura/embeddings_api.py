"""El segundo adaptador de embeddings: la API propietaria (cap. 8).

Mismo puerto que el local, otro proveedor — la lección del capítulo:
el cambio de embeddings es un despliegue con regresión (libro 2, cap. 19),
no una sustitución de piezas transparente. Ojo: las dimensiones cambian
(1536 vs 1024) y el índice se cocina de nuevo — por eso la ventana y las
dimensiones viven en el puerto, no en el servicio.
"""

from __future__ import annotations


class ClienteEmbeddingsApi:
    """text-embedding-3-small: 1536 dimensiones, ventana de 8191 tokens."""

    MODELO = "text-embedding-3-small"
    VENTANA_TOKENS = 8191
    DIMENSIONES = 1536

    def __init__(self) -> None:
        self._cliente = None

    @property
    def cliente(self):
        if self._cliente is None:
            from openai import OpenAI  # importación perezosa
            self._cliente = OpenAI()   # exige OPENAI_API_KEY en el entorno
        return self._cliente

    def incrustar(self, textos: list[str]) -> list[list[float]]:
        respuesta = self.cliente.embeddings.create(input=textos, model=self.MODELO)
        return [d.embedding for d in respuesta.data]
