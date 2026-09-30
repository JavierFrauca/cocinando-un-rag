---
title: "12 · La reescritura de la consulta: la pieza que faltaba"
---

# 12 · La reescritura de la consulta: la pieza que faltaba

## La decisión

Ninguno de los tres libros enseñó esto y todo sistema de producción lo necesita: **normalizar y reescribir la consulta antes de la primera búsqueda**. La regla de la web lo dice en cuatro palabras — *primero determinista, luego semántico* — y aquí es código: el determinismo ya corrió en el cap. 4 (sobre el corpus); el semántico reescribe la pregunta del usuario — ortografía, jerga, sinónimos del dominio — **sin responderla jamás**. La reescritura ocurre siempre, antes de la primera búsqueda, sin mirar resultados: si la segunda búsqueda dependiera de lo que devolvió la primera, ya sería el iterativo del cap. 5 del libro 3.

## El código

El puerto, en `cocinando/dominio/puertos.py`:

```python
class ReescritorConsulta(Protocol):
    """Normaliza y reescribe ANTES de la primera búsqueda: la pieza que faltaba.

    Determinista primero (ortografía, jerga del corpus), semántico después.
    Nunca responde: solo reescribe.
    """

    def reescribir(self, consulta: Consulta) -> Consulta: ...
```

Y el adaptador semántico, en `cocinando/infraestructura/llm.py`:

```python
class ReescritorLLM(ReescritorConsulta):
    """La pieza que faltaba: normalizar y reescribir ANTES de la primera búsqueda.

    Semántico después de lo determinista; nunca responde — solo reescribe.
    """

    SISTEMA = (
        "Eres el normalizador de consultas de un sistema de conocimiento. "
        "Corrige la ortografía, sustituye la jerga ambigua por el término del dominio "
        "y añade los sinónimos oficiales entre paréntesis. NO respondas la consulta, "
        "NO añadas información: devuelve solo la consulta reescrita."
    )

    def __init__(self, chat: ClienteChat | None = None) -> None:
        self.chat = chat or ClienteChat()

    def reescribir(self, consulta: Consulta) -> Consulta:
        texto = self.chat.completar(self.SISTEMA, consulta.texto)
        return Consulta(texto=texto.strip(), audiencia=consulta.audiencia,
                        dominio=consulta.dominio)
```

El servicio del cap. 14 lo llama primero, siempre — y su prueba lo verifica:

```python
def test_reescritura_antes_de_buscar(tmp_path):
    servicio, _ = _servicio(tmp_path)
    servicio.responder(Consulta(texto="plazo"))
    assert servicio.reescritor.veces == 1              # siempre, antes de la primera búsqueda
```

## Lo que importa

1. **El prompt prohíbe responder.** La instrucción dice dos veces que no — "NO respondas, NO añadas información" — porque el modelo está entrenado para agradar y el agradamiento aquí produce lo peor: una respuesta disfrazada de consulta. El reescritor que contesta envenena la búsqueda entera.
2. **La reescritura devuelve un `Consulta`, no un texto suelto.** La audiencia y el dominio sobreviven intactos — el reescritor trabaja para el texto, no para la decisión: el router del cap. 17 seguirá leyendo quién pregunta, no qué le pasó a la frase.
3. **Es un puerto, como todo.** La versión del sistema real añade el diccionario de sinónimos del dominio al prompt — el que el Silver normalizó (cap. 4). Un equipo sin presupuesto de LLM puede empezar con un reescritor determinista puro (el diccionario sin modelo) y calentar el semántico después: la interfaz no cambia.
4. **Va con su prueba de orden, no solo de efecto.** `veces == 1` verifica que corre UNA vez y ANTES de la búsqueda. Los fallos de orquestación — reescribir dos veces, o después de recuperar — no se cazan probando el resultado; se cazan contando las llamadas.

## Los números

La reescritura añade **una llamada corta** al camino de cada consulta — el coste del cap. 12 del libro 3 aplicado a sí mismo: milisegundos y céntimos de céntimo por la mejor formulación de todas las búsquedas siguientes. En el despacho, las consultas que necesitan reescritura son la mayoría de las que llegan con prisa — exactamente las que menos pueden permitirse una búsqueda mal formulada.

## Enlaces

- Repo: `cocinando/dominio/puertos.py` · `cocinando/infraestructura/llm.py` · `pruebas/test_servir.py`
- Web: la pieza nueva de la fase [Recuperación](https://ragcooking.info/biblioteca/recuperacion/)
- Libro 2, cap. 1: la anatomía de la pregunta · Libro 3, cap. 5: la frontera exacta — la reescritura previa no es iteración
