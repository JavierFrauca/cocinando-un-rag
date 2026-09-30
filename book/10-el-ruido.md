---
title: "10 · El ruido y su medición"
---

# 10 · El ruido y su medición

## La decisión

El embudo se mide fase a fase: cuánto entra, cuánto sale, cuánto ruido dejó cada filtro (libro 2, cap. 13). La cocción sin embudo medido es una factura con sorpresas — y aquí la medición no es un panel aparte: es el mismo retorno de la función `cocer`, para que sea imposible cocinar sin contarlo.

## El código

`cocinando/aplicacion/cocer.py`, completo — el servicio que convierte píldoras en índice:

```python
# cocinando/aplicacion/cocer.py
# Cocción: incrustar, indexar y medir el embudo (caps. 8-10).

from __future__ import annotations

from cocinando.dominio.modelos import Pildora, RegistroEmbudo
from cocinando.dominio.puertos import ClienteEmbeddings, RepositorioPildoras

LOTE = 64  # píldoras por llamada al modelo: grande para el rendimiento, pequeña para el error


def cocer(pildoras: list[Pildora], embeddings: ClienteEmbeddings,
          repo: RepositorioPildoras) -> list[RegistroEmbudo]:
    """Del texto al índice, por lotes y con el embudo medido.

    Los lotes existen por dos razones de método: el error de una llamada
    no tira la cocción entera, y la factura es legible lote a lote.
    """
    embudo = [RegistroEmbudo("cocer", len(pildoras), 0)]
    vivas = [p for p in pildoras if len(p.texto) <= embeddings.VENTANA_TOKENS * 4]
    embudo.append(RegistroEmbudo("ventana", len(pildoras), len(vivas)))

    vectores: list[list[float]] = []
    for i in range(0, len(vivas), LOTE):
        tro = vivas[i:i + LOTE]
        vectores.extend(embeddings.incrustar([p.texto for p in tro]))
    repo.guardar(vivas, vectores)

    embudo.append(RegistroEmbudo("indexado", len(vivas), repo.contar()))
    return embudo


def leer_embudo(embudo: list[RegistroEmbudo]) -> str:
    """El embudo, en una línea por fase — el ruido donde se vea."""
    return "\n".join(
        f"{r.fase}: {r.salieron}/{r.entraron} (ruido {r.ruido:.1%})" for r in embudo
    )
```

## Lo que importa

1. **La cocción devuelve su embudo en lugar de un `OK`.** La función que indexa no puede no contar: su retorno ES el RegistroEmbudo. Es la forma más barata de que ningún despliegue cocine a ciegas — quien llama recibe los números aunque no los pida.
2. **El filtro de ventana antes del gasto.** Lo que desborda la ventana del embedding no se incrusta truncado — se aparta y se cuenta. Una píldora truncada es un vector que no representa al texto; mejor una fila en el embudo (que pide arreglar la estructura del documento, cap. 5) que una mención cocida a medias en el índice.
3. **Los lotes son de método, no de tuning.** LOTE=64 para que una llamada fallida no tire la cocción entera y para que la factura sea legible lote a lote. El valor exacto es de la infraestructura; el POR QUÉ hay lotes, del método.
4. **El `indexado` se mide contra el repositorio, no contra el bucle.** `repo.contar()` confirma lo que realmente quedó en el índice — si una píldora se perdió por el camino, el embudo la delata en la tercera fase sin que nadie tenga que sospechar y auditar a mano.

## Los números

En una ingesta sana del despacho, el ruido de la fase **ventana es ~0%** — las píldoras del cap. 5 (máximo 1.200 caracteres contra 8.192 tokens de ventana) no rozan el techo. Si ese porcentaje deja de ser ~0, no es un problema de embeddings: es la estructura de encabezados de algún documento que se ha degradado. El embudo también diagnostica aguas arriba.

## Enlaces

- Repo: `cocinando/aplicacion/cocer.py`
- Web: fase [Ruido](https://ragcooking.info/biblioteca/)
- Libro 2, cap. 13: el tope y el presupuesto · Libro 3, cap. 16: el panel que hereda esta costumbre de contar
