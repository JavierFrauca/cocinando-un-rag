---
title: "10 · El ruido y su medición"
---

# 10 · El ruido y su medición

La factura que llegó multiplicada por cuatro — el piloto agéntico del cap. 10 del libro 3 — no la produjo un error técnico: la produjo **nadie contando**. El dinero se gastó en llamadas que nadie sumaba, consulta a consulta, hasta el fin de mes. La cocción tiene el mismo riesgo con otro disfraz: píldoras que entran al modelo, tokens que se cocinan, índice que crece — sin nadie sumando. Este capítulo es la vacuna: la función que cocina devuelve su propio recuento, para que sea imposible cocinar sin contarlo.

## La decisión

El embudo se mide fase a fase: cuánto entra, cuánto sale, cuánto ruido dejó cada filtro (libro 2, cap. 13). La decisión de diseño aquí es pequeña y decisiva: **la medición no es un panel aparte** — es el mismo retorno de `cocer`, de modo que quien cocina recibe los números aunque no los pida. Un panel que hay que acordar mirar falla; un retorno que llega con el resultado no puede perderse. Tres fases en el embudo de esta pieza: lo que entra a cocer, lo que sobrevive a la ventana del embedding, lo que realmente quedó en el índice.

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

Cómo se leerlo: el flujo es lineal — apartar lo que desborda la ventana, incrustar por lotes, indexar, confirmar — y cada paso deja su fila en `embudo`. La función `leer_embudo` es el formato de triaje: una línea por fase con el porcentaje de ruido, para que el diagnóstico quepita en el diario de la semana.

## Lo que importa

1. **La cocción devuelve su embudo en lugar de un `OK`.** La función que indexa no puede no contar: su retorno ES el RegistroEmbudo. Es la forma más barata de que ningún despliegue cocine a ciegas — quien llama recibe los números aunque no los pida, y la costumbre de mirarlos se instala sola, porque llegan sin ceremonia.
2. **El filtro de ventana antes del gasto.** Lo que desborda la ventana del embedding no se incrusta truncado — se aparta y se cuenta. Una píldora truncada es un vector que no representa al texto: ocupa índice, aparece en búsquedas y respalda menos de lo que parece. Mejor una fila en el embudo (que pide arreglar la estructura del documento, cap. 5) que una mención cocida a medias.
3. **Los lotes son de método, no de tuning.** LOTE=64 para que una llamada fallida no tire la cocción entera y para que la factura sea legible lote a lote — si el modelo de embeddings empieza a fallar en el lote 40 de 60, el error apunta a una píldora concreta, no a "la cocción de ayer". El valor exacto es de infraestructura; el POR QUÉ hay lotes, del método.
4. **El `indexado` se mide contra el repositorio, no contra el bucle.** `repo.contar()` confirma lo que realmente quedó en el índice — no lo que el bucle *cree* que indexó. Si una píldora se pierde por el camino (un id repetido que se pisó, un error silencioso), la tercera fase del embudo la delata: entraron 100, indexaron 99, y nadie tuvo que sospechar para descubrirlo.
5. **El ruido tiene lecturas distintas por fase.** Ruido en `ventana` = documentos sin estructura que la guardia del cap. 5 tuvo que cortar (se arregla escribiendo mejor). Ruido en `indexado` = pérdidas de sincronía con el índice (se arregla en el repositorio). El embudo no solo cuenta: **localiza** — y esa es la diferencia entre un número y un diagnóstico.

## Los números

En una ingesta sana del despacho, el ruido de la fase **ventana es ~0%** — las píldoras del cap. 5 (máximo 1.200 caracteres contra 8.192 tokens de ventana) no rozan el techo. Si ese porcentaje deja de ser ~0, no es un problema de embeddings: es la estructura de encabezados de algún documento degradada. El **LOTE=64** del repo es un equilibrio de arranque — lotes más grandes cocinan más rápido y diagnosticán peor; el número que conviene vigilar una vez en producción es el coste por lote de la factura de embeddings, que con la variante local es cero y con la API se lee línea a línea.

## Enlaces

- Repo: `cocinando/aplicacion/cocer.py`
- Web: fase [Ruido](https://ragcooking.info/biblioteca/)
- Libro 2, cap. 13: el tope y el presupuesto · Libro 3, cap. 10: la factura que este embudo habría visto venir · Libro 3, cap. 16: el panel que hereda esta costumbre de contar
