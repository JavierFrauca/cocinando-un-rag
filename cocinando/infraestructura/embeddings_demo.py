"""El adaptador de demostración: vectores deterministas por hash (sin red, sin modelos).

Sirve para las pruebas y para `sembrar.py --embeddings demo`: siembra la base
en un minuto sin descargar modelo ni pedir clave. Su calidad de recuperación
es de juguete — los vectores solo comparten fuerza entre textos que comparten
palabras. Para cocer de verdad, `embeddings_local` o `embeddings_api`.
"""

from __future__ import annotations

import hashlib


class ClienteEmbeddingsDemo:
    """64 dimensiones de juguete: misma palabra, mismo trozo de vector."""

    VENTANA_TOKENS = 8192
    DIMENSIONES = 64

    def incrustar(self, textos: list[str]) -> list[list[float]]:
        return [self._uno(t) for t in textos]

    def _uno(self, texto: str) -> list[float]:
        vector = [0.0] * self.DIMENSIONES
        for token in texto.lower().split():
            digesto = int(hashlib.md5(token.encode()).hexdigest(), 16)
            vector[digesto % self.DIMENSIONES] += 1.0
        norma = sum(v * v for v in vector) ** 0.5 or 1.0
        return [v / norma for v in vector]
