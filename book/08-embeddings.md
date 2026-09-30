---
title: "8 · Embeddings: la elección y la cocción"
---

# 8 · Embeddings: la elección y la cocción

El embedding nuevo "se notaba mucho mejor" — el equipo lo había probado con cinco consultas a mano y las cinco volaban. La vara del cap. 18 del libro 2 lo midió sobre el dataset completo y el recall cayó tres puntos: volaba en las consultas fáciles y naufragaba en las bordes, que son las que compran la vara. Esta es la escena que este capítulo quiere hacer imposible de repetir: la elección de embeddings no se discute en el folleto ni en la demo — se discute con números del sistema propio, y el cambio se ejecuta como lo que es: **un despliegue con regresión**.

## La decisión

El puerto `ClienteEmbeddings` con **dos adaptadores**: BGE-M3 local por omisión — gratis, multilingüe, corre en el portátil sin clave; el corpus nunca sale de la máquina, que en un despacho laboral no es un detalle de marketing — y `text-embedding-3-small` como variante de API. La lección del capítulo no es qué modelo elegir (para eso está la tabla de 11 modelos de la [fase Embedding de la web](https://ragcooking.info/biblioteca/embedding/)): es que **el cambio de embeddings es un despliegue con regresión**, no una sustitución de piezas transparente — y por eso la ventana y las dimensiones viven en el puerto, no en el servicio. El servicio que cocina no sabe qué modelo hay montado; sabe cuánto cabe y cuánto mide.

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

Y la variante, `cocinando/infraestructura/embeddings_api.py` — nótese que es idéntica en forma y distinta en números:

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

La fábrica que decide cuál corre, en `cocinando/infraestructura/configuracion.py` — la única línea del sistema que sabe qué adaptador está montado:

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

1. **La importación perezosa es honestidad con el lector.** `import cocinando` no descarga dos gigabytes de modelo ni exige una clave de API: los tests corren con un falso determinista (ver `pruebas/fakes.py`) y el modelo real se carga solo cuando se usa, una vez. La dependencia cara existe en el adaptador, no en el dominio — la misma razón por la que la CI del cap. 16 cuesta segundos y cero facturas.
2. **La ventana vive en el puerto y manda sobre el chunking.** El límite de tokens del embedding es el techo real del tamaño de la píldora — la fase Embedding de la web lo dice y aquí es código: `cocer()` aparta lo que desborda (cap. 10) porque un vector truncado es una píldora cocida a medias que ocupa índice y no respalda lo que parece respaldar. Por eso `VENTANA_TOKENS` es un atributo del puerto y no una constante suelta: el servicio lo lee de quien esté montado.
3. **Las dimensiones no son un detalle: son un re-cocinado.** Cambiar de BGE-M3 (1024d) a la API (1536d) invalida el índice entero — los vectores viejos y nuevos no viven en la misma tabla ni hablan el mismo espacio. Por eso `configuracion.py` lleva las dimensiones, el cap. 9 guarda la guardia del esquema, y el cap. 16 exige regresión: el índice se cocina de nuevo y la vara decide si el cambio merece la pena.
4. **`normalize_embeddings=True` no es opcional.** Los vectores normalizados hacen que la distancia del coseno y la euclídea ordenen igual — y que las comparaciones de la vara no dependan de la longitud del texto. Sin normalizar, el ranking miente sutilmente a favor de los textos largos, y nadie se entera hasta que el dataset lo dice.
5. **La elección, cuando toque, se hace con la vara — no con la tabla.** La tabla de la web sirve para descartar (sin multilingüe, no; con 512 tokens y píldoras de 300, no) y para presupuestar. La elección final es `correr_vara` del cap. 15 con el dataset propio: dos candidatos, dos cocciones, un recall comparado. El "se nota mucho mejor" no es un argumento; es el síntoma de que nadie midió.

## Los números

Valores por omisión del repo: **1024 dimensiones** (BGE-M3) y **ventana de 8192 tokens** — que deja a las píldoras del cap. 5 (máximo 1.200 caracteres ≈ 300 tokens) un margen de holgura de más de veinte veces: el título de contexto y el solape no son nunca el problema. En la elección real del despacho pesaron el multilingüe (el corpus tiene catalán y euskera en las circulares — un embedding solo inglés habría creado dos clases de píldoras: las que se encuentran y las que no) y el coste cero de re-cocinado. El coste de la variante API se paga en céntimos por millón de tokens, pero también en política: **el corpus sale del portátil** — y en un despacho, esa línea del presupuesto no está en dinero.

## Enlaces

- Repo: `cocinando/infraestructura/embeddings_local.py` · `embeddings_api.py` · `configuracion.py`
- Web: fase [Embedding](https://ragcooking.info/biblioteca/embedding/) — la tabla de 11 modelos con ventanas y dimensiones
- Libro 2, cap. 12: el híbrido que se cocina con estos vectores · Libro 2, cap. 18: la vara que elige · Libro 2, cap. 19: el cambio con regresión obligada
