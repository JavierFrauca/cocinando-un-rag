---
title: "7 · La síntesis Gold"
---

# 7 · La síntesis Gold

La panorámica que el iterativo resuelve mal dos semanas seguidas — siempre se le queda fuera el mismo protocolo — tiene dos salidas: seguir rehaciendo vueltas cada vez que alguien la pregunte, o sentarse una tarde, escribir la vista agregada, firmarla y convertir esa pregunta compuesta en una pasada directa. El Gold es la segunda salida (libro 1, caps. 13-15). Y esta pieza es pequeña a propósito: toda su inteligencia está en la puerta que no deja pasar una síntesis sin nombre y apellidos detrás — porque la frontera entre el corpus y lo que el LLM se inventaría por su cuenta no se cruza con un `warning`: se cruza con una firma.

## La decisión

El Gold es la síntesis de conocimiento validada que convierte preguntas compuestas en pasadas directas. Su regla de gobernanza es la firma de toda la serie — **quien resuelve a mano, firma la verdad** — y aquí es una precondición de función: sin firma, `ValueError` y fuera. La decisión que esconde: **automatizar la redacción del Gold es posible; firmarla por máquina es la espiral** que el cap. 17 del libro 3 prohíbe (el sistema confirmando lo que ya cree con la elegancia añadida de la estadística). El código de esta pieza no redacta síntesis — las admite. La redacción es del oficio; el alta, del código.

## El código

`cocinando/aplicacion/sintesis.py`, completo — es corto porque lo decisivo cabe en un `if`:

```python
# cocinando/aplicacion/sintesis.py
# La síntesis Gold con guía humana (libro 1, caps. 13-15).

from __future__ import annotations

from cocinando.dominio.modelos import Pildora


def registrar_sintesis(texto: str, dominio: str, firmada_por: str,
                       fuente: str = "gold/sintesis") -> Pildora:
    """Da de alta una síntesis Gold — si y solo si una persona la firma.

    La regla de la serie: quien resuelve a mano, firma la verdad.
    Un ValueError aquí no es un fastidio: es la frontera entre el corpus
    y lo que el LLM se inventaría por su cuenta.
    """
    if not firmada_por.strip():
        raise ValueError("una síntesis Gold sin firma humana no entra en el corpus")
    return Pildora(
        texto=f"[Síntesis · {dominio} · firmada por {firmada_por}]\n\n{texto}",
        titulo=f"Síntesis Gold · {dominio}",
        fuente=fuente,
        orden=0,
        tipo="sintesis",
        dominio=dominio,
    )
```

Cómo se lee el listado: el flujo natural de trabajo es doble. El borrador lo puede redactar un LLM — con el corpus delante, citando —; la firma la pone una persona que lo ha leído y verificado. `registrar_sintesis` recibe la pareja (borrador, firma) y solo da el alta cuando la segunda existe: **el LLM propone, la persona firma**, que es la regla de gobernanza del cap. 15 del libro 3 aplicada a la capa de corpus. La firma viaja dentro del texto — no en un campo aparte — para que quien reciba esta píldora en una respuesta sepa, sin consultar nada, que es Gold y quién respondió por ella.

Y su prueba:

```python
def test_sintesis_gold_exige_firma_humana():
    with pytest.raises(ValueError):
        registrar_sintesis("texto", dominio="convenios", firmada_por="   ")
    pildora = registrar_sintesis("texto", dominio="convenios", firmada_por="J. Frauca")
    assert pildora.tipo == "sintesis" and "J. Frauca" in pildora.texto
```

El primer caso prueba la frontera con una firma de espacios en blanco — porque la firma vacía no siempre viene como `None`: a veces viene como el resultado de un campo de formulario que nadie rellenó. `strip()` es la diferencia entre validar y aparentar validar.

## Lo que importa

1. **La firma no es un metadato decorativo: es una precondición.** El `ValueError` sin firma es la diferencia entre el corpus y lo que el LLM se inventaría por su cuenta. Podría ser un `warning`; es una excepción, porque una síntesis anónima no es una síntesis — es una hipótesis vestida de Gold, y el Gold que miente es peor que el corpus que no alcanza: se le cree más.
2. **La síntesis es un `tipo` más en el payload.** Viaja como píldora (`tipo="sintesis"`) para que el ensamblado del libro 2 la trate como lo que es: la vista agregada y mantenida, no otra pieza de prosa. El capítulo 5 del libro 2 ya contó qué hace el acceso con ella — servirla en una pasada donde antes hacían falta vueltas; aquí solo la produce el oficio.
3. **El título declara su origen.** `[Síntesis · convenios · firmada por J. Frauca]` delante del texto: la trazabilidad empieza en el texto mismo, no en un log aparte. Si una síntesis caduca y hay que retirarla, el mismo título la hace localizable — y el bucle de retorno sabe a quién preguntar por la siguiente versión.
4. **Aquí no hay LLM — y eso también es una decisión.** La pieza más tentadora de automatizar (redactar la síntesis) queda fuera del código a propósito. El borrador por LLM es legítimo y deseable; lo que no es negociable es que el alta exija firma humana verificada. En esta implementación, la frontera está en esta función — y cualquier herramienta que la automatice más allá tendrá que declarar por qué.
5. **Cómo se rompe esto: el Gold fosilizado.** La síntesis firmada en enero sigue viva en julio aunque el convenio cambió en marzo. El modo de fallo no es de esta función — es del ciclo de vida (libro 1, cap. 18): cada síntesis lleva su vigencia heredada de sus fuentes, y el triaje del cap. 18 de este libro es quien la revisa. El código entrega la píldora con su `vigencia`; que se revise, es del bucle.

## Los números

El Gold del despacho cuenta las síntesis también por **decenas** — una por pregunta recurrente de cruce, no una por documento: si hay una síntesis por cada cosa, no es síntesis, es el corpus copiado con otra cara. El retorno de cada una se mide en el propio bucle: la familia de consultas que la motivó deja de consumir vueltas del iterativo — cada síntesis firmada es una familia que baja de patrón, y esa caída se ve en el panel del cap. 18.

## Enlaces

- Repo: `cocinando/aplicacion/sintesis.py` · `pruebas/test_aprovisionamiento.py`
- Web: fase [Síntesis](https://ragcooking.info/biblioteca/)
- Libro 1, caps. 13-15: auditoría de coherencia, síntesis de conocimiento, ingesta del Gold · Libro 2, cap. 5: lo que el acceso hace con el Gold · Libro 3, cap. 17: la firma en el triaje
