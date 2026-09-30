"""El adaptador de embeddings local: BGE-M3, por omisión (cap. 8).

Gratis, multilingüe, corre en el portátil sin clave de API:
el lector cocina offline y el corpus nunca sale de su máquina.
La importación pesada es perezosa a propósito — importar este módulo
no descarga el modelo; usarlo, sí (una vez).
"""

from __future__ import annotations


class ClienteEmbeddingsLocal:
    """BGE-M3: 1024 dimensiones, ventana de 8192 tokens, multilingüe."""

    MODELO = "BAAI/bge-m3"
    VENTANA_TOKENS = 8192
    DIMENSIONES = 1024

    def __init__(self) -> None:
        self._modelo = None

    @property
    def modelo(self):
        if self._modelo is None:
            from sentence_transformers import SentenceTransformer  # importación perezosa
            self._modelo = SentenceTransformer(self.MODELO)
        return self._modelo

    def incrustar(self, textos: list[str]) -> list[list[float]]:
        vectores = self.modelo.encode(textos, normalize_embeddings=True)
        return [v.tolist() for v in vectores]
