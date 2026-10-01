---
title: "13 · El rerank y el juez de cosecha"
---

# 13 · El rerank y el juez de cosecha

El veredicto complaciente es el vicio número uno del juez según el libro 2 (cap. 16): preguntado en crudo — ¿es esto relevante? —, el modelo tiende a decir que sí, sobre todo si el candidato es largo, técnico y con aspecto de respuesta. Un juez que aprueba todo convierte la segunda mirada en teatro: cuesta llamadas y no captura nada. El antídoto del libro es de diseño — **veredictos cerrados y forzados**, tres clases sin "en parte quizá" — y este capítulo es ese antídoto hecho tipo de dato: un `Enum` de tres valores que no deja sitio al matiz, con la regla de oro escrita en el docstring — **el juez certifica encaje consulta-cosecha, no verdad jurídica**.

## La decisión

El tamiz del libro 2 (cap. 15) reordena la cosecha con un modelo más fino que el índice, y el juez del cap. 16 decide si la cosecha sirve — solo donde el error cobra: fácticas críticas y todo lo que llegue a un cliente. Dos límites que aquí son código. Primero: **los veredictos viven en el dominio como `Enum`**, no como strings sueltos — el "en parte quizá" no cabe en el tipo, y el juez que matiza no es una fuente: es un clima. Segundo: **un veredicto ininteligible no se acepta como viene** — se degrada a PARCIAL y se declara, porque la dirección del fallo por omisión debe ser la conservadora.

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

Cómo leerlo: el método hace tres cosas y su orden es el diseño. La guardia de la primera línea — cosecha vacía, `NO_RESPONDE` sin gastar una llamada. El montaje del material numerado — el juez ve cada píldora con su título, porque juzgar texto sin contexto es juzgar a ciegas, y el libro 2 prohibió juzgar a ciegas. Y el parseo defensivo — la respuesta del modelo se limpia, se mayusculiza, se toma su primera palabra y se convierte en `Veredicto`; lo que no convierta, no es RESPONDE por cortesía: es PARCIAL.

## Lo que importa

1. **Los veredictos son un `Enum`, no un string suelto.** El dominio declara que solo existen tres — el antídoto del veredicto complaciente del libro 2 es estructural: el "en parte quizá" no cabe en el tipo. Y `Veredicto(str, Enum)` viaja serializable para el diario del cap. 18: la tasa de cada veredicto es una métrica del panel, y una tasa que se dispara diagnostica — juez paranoico o familia mal asignada, como dijo el cap. 16 del libro 3.
2. **La temperatura es cero en toda la infraestructura de LLM.** La respuesta del juez no es una prosa: es un instrumento. La creatividad aquí no añade valor — añade inconsistencia, y un juez que cambia de opinión sobre el mismo material no es una fuente: es un clima. El libro 2 lo llamó el segundo vicio del juez y pidió revisión muestral semanal; la temperatura cero es la primera mitad del antídoto, la que se escribe una vez.
3. **El veredicto ininteligible degrada a PARCIAL, no a RESPONDE.** La dirección del fallo por omisión es la conservadora: ante la duda, el servicio abstendrá o marcará la respuesta — jamás firmará en verde. Es la misma asimetría que el libro 2 pidió para el juez: decir no es una opción honorable, y descifrar mal no puede premiar al modelo vago.
4. **`NO_RESPONDE` con cosecha vacía ni llega al modelo.** La guardia de la primera línea: no se paga una llamada de juicio para certificar que no hay nada que juzgar. Los céntimos del cap. 10 del libro 3 se ahorran también en el camino del juez — la frugalidad no es una fase del sistema, es una costumbre transversal.
5. **El juez no juzga la verdad — y el docstring lo dice.** "Certifica encaje consulta-cosecha; jamás verdad jurídica": la lección que el libro 2 cobró caro el día que el juez rechazó una píldora correcta "porque sabía" que el plazo era otro, con su memoria de preentrenamiento desactualizada. La verdad la trae el corpus validado; el juez solo decide si el candidato la transporta intacta hasta la pregunta.
6. **El rerank (el tamiz) y el juez comparten mesa pero no función.** El tamiz reordena por encaje fino; el juez decide si la cosecha entera sirve. Esta implementación los funde en el veredicto sobre la cosecha ordenada por RRF — para un rerank dedicado (un cross-encoder local reordenando antes del juez) el puerto `JuezCosecha` no cambia: otra pieza del mismo contrato, y la vara del cap. 15 dirá si el puesto extra de latencia lo paga el recall.

## Los números

El juez corre **solo donde el error cobra** — fácticas críticas y todo lo que llegue a un cliente, como sentenció el cap. 16 del libro 2. Su factura se paga en segundos de camino: una llamada de veredicto sobre la cosecha ya recuperada. La **tasa de rechazo medida** — el termómetro del cap. 6 del libro 3 — es la que decide endurecer o aflojar la rúbrica: en un corpus sano debe estar en un rango razonable y estable; al cero absoluto, juez complaciente; disparada, paranoico o familia mal asignada. Ninguno de los tres estados se corrige a ojo: se corrige con ejemplos de rechazo real en la rúbrica, y midiendo de nuevo.

## Enlaces

- Repo: `cocinando/dominio/modelos.py` · `cocinando/infraestructura/llm.py`
- Web: fase [Reranking](https://ragcooking.info/biblioteca/)
- Libro 2, caps. 15-16: el tamiz y el LLM como juez · Libro 3, cap. 6: la réplica interna que este juez entra a servir · Cap. 14 de este libro: lo que el servicio hace con el veredicto
