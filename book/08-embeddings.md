---
title: "8 · Embeddings: la elección y la cocción"
---

# 8 · Embeddings: la elección y la cocción

## La decisión

El puerto `ClienteEmbeddings` con **dos adaptadores**: BGE-M3 local por omisión — gratis, multilingüe, corre en el portátil sin clave; el corpus nunca sale de la máquina — y `text-embedding-3-small` como variante de API. La lección del capítulo no es qué modelo elegir (para eso está la tabla de la web): es que **el cambio de embeddings es un despliegue con regresión**, no una sustitución de piezas transparente — y por eso la ventana y las dimensiones viven en el puerto, no en el servicio.

## El código

El adaptador por omisión, `cocinando/infraestructura/embeddings_local.py`, completo:

```python
# cocinando/infraestructura/embeddings_local.py
# BGE-M3: el open multilingüe de referencia según la propia web.

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
```

Y la variante, `cocinando/infraestructura/embeddings_api.py`:

```python
# cocinando/infraestructura/embeddings_api.py
# Mismo puerto, otro proveedor — y otro par de números que importan.

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
```

La fábrica que decide cuál corre, en `cocinando/infraestructura/configuracion.py`:

```python
def cliente_embeddings(config: Configuracion | None = None) -> ClienteEmbeddings:
    """El puerto ClienteEmbeddings con sus dos adaptadores (cap. 8)."""
    config = config or Configuracion(embeddings=os.environ.get("COCINANDO_EMBEDDINGS", "local"))
    if config.embeddings == "api":
        from cocinando.infraestructura.embeddings_api import ClienteEmbeddingsApi
        return ClienteEmbeddingsApi()
    from cocinando.infraestructura.embeddings_local import ClienteEmbeddingsLocal
    return ClienteEmbeddingsLocal()
```

## Lo que importa

1. **La importación perezosa es honestidad con el lector.** `import cocinando` no descarga 2 GB de modelo ni exige una clave de API: los tests corren con un falso determinista (ver `pruebas/fakes.py`) y el modelo real se carga solo cuando se usa. La dependencia cara existe en el adaptador, no en el dominio.
2. **La ventana vive en el puerto y manda sobre el chunking.** El límite de tokens del embedding es el techo real del tamaño de la píldora — la fase Embedding de la web lo dice y aquí es código: `cocer()` descarta lo que desborda (cap. 10) porque un vector truncado es una píldora cocida a medias.
3. **Las dimensiones no son un detalle: son un re-cocinado.** Cambiar de BGE-M3 (1024d) a la API (1536d) invalida el índice entero — los vectores viejos y nuevos no viven en la misma tabla. Por eso `configuracion.py` lleva las dimensiones y el cap. 16 exige regresión: el índice se cocina de nuevo y la vara decide si el cambio merece la pena.
4. **`normalize_embeddings=True` no es opcional.** Los vectores normalizados hacen que la distancia del coseno y la euclídea ordenen igual — y que las comparaciones de la vara no dependan de la longitud del texto. Sin normalizar, el ranking miente sutilmente y nadie se entera hasta el dataset.

## Los números

Valores por omisión del repo: **1024 dimensiones** (BGE-M3) y **ventana de 8192 tokens** — que deja a las píldoras del cap. 5 (máximo 1.200 caracteres ≈ 300 tokens) un margen de holgura de más de veinte veces: el título de contexto y el solape no son nunca el problema. En la elección real del despacho pesaron el multilingüe (el corpus tiene catalán y euskera en las circulares) y el coste cero de re-cocinado; la tabla de decisión completa, en la [fase Embedding de la web](https://ragcooking.info/biblioteca/embedding/).

## Enlaces

- Repo: `cocinando/infraestructura/embeddings_local.py` · `embeddings_api.py` · `configuracion.py`
- Web: fase [Embedding](https://ragcooking.info/biblioteca/embedding/) — la tabla de 11 modelos con ventanas y dimensiones
- Libro 2, cap. 12: el híbrido que se cocina con estos vectores · Libro 2, cap. 19: el cambio con regresión obligada
