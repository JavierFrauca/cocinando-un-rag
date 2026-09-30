---
title: "7 · La síntesis Gold"
---

# 7 · La síntesis Gold

## La decisión

El Gold es la síntesis de conocimiento validada que convierte preguntas compuestas en pasadas directas (libro 1, caps. 13-15). Su regla de gobernanza es la firma de toda la serie — **quien resuelve a mano, firma la verdad** — y esta pieza es pequeña a propósito: toda su inteligencia está en la puerta que no deja pasar una síntesis sin nombre y apellidos detrás.

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

Y su prueba:

```python
def test_sintesis_gold_exige_firma_humana():
    with pytest.raises(ValueError):
        registrar_sintesis("texto", dominio="convenios", firmada_por="   ")
    pildora = registrar_sintesis("texto", dominio="convenios", firmada_por="J. Frauca")
    assert pildora.tipo == "sintesis" and "J. Frauca" in pildora.texto
```

## Lo que importa

1. **La firma no es un metadato decorativo: es una precondición.** El `ValueError` sin firma es la diferencia entre el corpus y lo que el LLM se inventaría por su cuenta. Podría ser un `warning`; es una excepción, porque una síntesis anónima no es una síntesis — es una hipótesis vestida de Gold.
2. **La síntesis es un `tipo` más en el payload.** Viaja como píldora (`tipo="sintesis"`) para que el ensamblado del libro 2 la trate como lo que es: la vista agregada y mantenida, no otra pieza de prosa. El capítulo 5 del libro 2 ya contó qué hace el acceso con ella; aquí solo la produce el oficio.
3. **El título declara su origen.** `[Síntesis · convenios · firmada por J. Frauca]` delante del texto: quien reciba esta píldora en una respuesta sabe que es Gold, quién la firmó y de qué dominio — la trazabilidad empieza en el texto mismo, no en un log aparte.
4. **Aquí no hay LLM.** La síntesis la redacta una persona con guía — el cap. 14 del libro 1 lo cuenta — y el código solo la admite. Automatizar la redacción del Gold es posible; firmarla por máquina es la espiral que el libro 3 prohíbe.

## Los números

El Gold del despacho cuenta las síntesis también por **decenas** — una por pregunta recurrente de cruce, no una por documento. Su mantenimiento es del triaje: cada panorámica que el iterativo resuelve mal dos semanas seguidas es candidata a ser la próxima síntesis firmada.

## Enlaces

- Repo: `cocinando/aplicacion/sintesis.py` · `pruebas/test_aprovisionamiento.py`
- Web: fase [Síntesis](https://ragcooking.info/biblioteca/)
- Libro 1, caps. 13-15: auditoría de coherencia, síntesis de conocimiento, ingesta del Gold · Libro 3, cap. 17: la firma en el triaje
