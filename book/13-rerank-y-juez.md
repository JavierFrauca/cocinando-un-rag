---
title: "13 · El rerank y el juez de cosecha"
---

# 13 · El rerank y el juez de cosecha

## La decisión

El tamiz del libro 2 (cap. 15) reordena la cosecha con un modelo más fino que el índice, y el juez del cap. 16 emite **veredictos cerrados** — responde, parcial, no responde — sobre lo recuperado, solo donde el error cobra. Dos límites que aquí son código: el juez certifica encaje consulta-cosecha, **no verdad**; y un veredicto ininteligible no se acepta como viene — se degrada a PARCIAL y se declara.

## El código

Los tres veredictos viven en el dominio, `cocinando/dominio/modelos.py`:

```python
class Veredicto(str, Enum):
    """Los tres veredictos cerrados del juez de cosecha (libro 2, cap. 16).

    Cerrados a propósito: sin "en parte quizá". El juez que matiza
    no es una fuente, es un clima.
    """

    RESPONDE = "RESPONDE"
    PARCIAL = "PARCIAL"
    NO_RESPONDE = "NO_RESPONDE"
```

Y el juez, en `cocinando/infraestructura/llm.py`:

```python
class JuezCosechaLLM(JuezCosecha):
    """El juez con veredictos cerrados: responde, parcial, no responde.

    Cerrados a propósito — el antídoto del veredicto complaciente (libro 2, cap. 16).
    Certifica encaje consulta-cosecha; jamás verdad jurídica.
    """

    SISTEMA = (
        "Eres el juez de cosecha de un sistema de conocimiento. Dado el material "
        "recuperado, emite UNO de estos tres veredictos y nada más:\n"
        "RESPONDE — la cosecha cubre la pregunta entera.\n"
        "PARCIAL — la cubre a medias.\n"
        "NO_RESPONDE — es de otro asunto o no alcanza.\n"
        "Devuelve solo la palabra del veredicto."
    )

    def __init__(self, chat: ClienteChat | None = None) -> None:
        self.chat = chat or ClienteChat()

    def veredictar(self, consulta: Consulta, cosecha: list[Hit]) -> Veredicto:
        if not cosecha:
            return Veredicto.NO_RESPONDE
        material = "\n\n".join(f"[{i + 1}] {h.pildora.titulo}\n{h.pildora.texto}"
                               for i, h in enumerate(cosecha))
        palabra = self.chat.completar(
            self.SISTEMA, f"Consulta: {consulta.texto}\n\nCosecha:\n{material}"
        ).strip().upper()
        try:
            return Veredicto(palabra.split()[0])
        except ValueError:
            return Veredicto.PARCIAL   # un juez ininteligible no es libre: es parcial de fábrica
```

## Lo que importa

1. **Los veredictos son un `Enum`, no un string suelto.** El dominio declara que solo existen tres — el antídoto del veredicto complaciente del libro 2 es estructural: el "en parte quizá" no cabe en el tipo. Y `Veredicto(str, Enum)` viaja serializable para el diario del cap. 18.
2. **La temperatura es cero en toda la infraestructura de LLM.** La respuesta del juez no es una prosa: es un instrumento. La creatividad aquí no añade valor — añade inconsistencia, y un juez que cambia de opinión no es una fuente: es un clima.
3. **El veredicto ininteligible degrada a PARCIAL, no a RESPONDE.** La dirección del fallo por omisión es la conservadora: ante la duda, el servicio abstendrá o marcará la respuesta — jamás firmará en verde. Es la misma asimetría que el libro 2 pidió para el juez: decir no es una opción honorable.
4. **`NO_RESPONDE` con cosecha vacía ni llega al modelo.** La guardia de la primera línea: no se paga una llamada de juicio para certificar que no hay nada que juzgar. Los céntimos del cap. 10 del libro 3 se ahorran también en el camino del juez.
5. **El rerank (el tamiz) y el juez comparten mesa pero no función.** El tamiz reordena por encaje fino; el juez decide si la cosecha entera sirve. Esta implementación los funde en el veredicto sobre la cosecha ordenada — para un rerank dedicado (un cross-encoder local) el puerto `JuezCosecha` no cambia: otra pieza del mismo contrato.

## Los números

El juez corre **solo donde el error cobra** — fácticas críticas y todo lo que llegue a un cliente, como sentenció el cap. 16 del libro 2. Su factura se paga en segundos de camino: una llamada de veredicto sobre la cosecha ya recuperada. La tasa de rechazo medida — el termómetro del cap. 6 del libro 3 — es la que decide endurecer o aflojar la rúbrica, nunca la intuición de quien lee veredictos sueltos.

## Enlaces

- Repo: `cocinando/dominio/modelos.py` · `cocinando/infraestructura/llm.py`
- Web: fase [Reranking](https://ragcooking.info/biblioteca/)
- Libro 2, caps. 15-16: el tamiz y el LLM como juez · Libro 3, cap. 6: la réplica interna que este juez entra a servir
