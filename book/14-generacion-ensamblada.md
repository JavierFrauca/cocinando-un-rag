---
title: "14 · La generación ensamblada"
---

# 14 · La generación ensamblada

## La decisión

La plantilla del libro 3 (cap. 13) hecha código: **ensamblar, no componer**. Las seis piezas del contrato de generación — papel, material, prohibiciones, citas, formato, abstención — son un dato versionado, no un string pegado en el código; el material entra citado con sus `[Fuente N]`; y el servicio entero — reescribir, buscar, juzgar, generar — orquesta los puertos en el orden que el método manda y en ningún otro.

## El código

La plantilla por omisión y el generador, en `cocinando/infraestructura/llm.py`:

```python
# cocinando/infraestructura/llm.py — el generador y la plantilla como dato

PLANTILLA_POR_OMISION = PlantillaGeneracion(
    audiencia="por_omision",
    papel=(
        "Redactas la respuesta para [audiencia] a partir exclusivamente del contexto "
        "entregado. No tienes conocimiento propio aplicable: todo lo que digas debe "
        "venir del contexto."
    ),
    material=(
        "Cada bloque de contexto lleva su identificador [Fuente N]; úsalo para citar. "
        "Los bloques caducados no responden. Si dos bloques contradicen, "
        "expón la discrepancia, no elijas."
    ),
    prohibiciones=(
        "No añadas conocimiento externo. No completes lo que el contexto deja a medias. "
        "No redondees cifras. No unifiques versiones distintas. Sin cortesía inflada."
    ),
    citas="Cada cifra, plazo y condición lleva su referencia [Fuente N].",
    formato="Dato primero, desarrollo después, referencias al final. Respuesta corta.",
    abstencion=(
        "Si el contexto no respalda la respuesta, no respondas: di que no consta en el "
        "corpus y señala lo más cercano que contiene. Toda abstención queda anotada."
    ),
)


class GeneradorEnsamblado:
    """La plantilla del libro 3 hecha código: ensamblar, no componer.

    Las seis piezas de la plantilla son datos (PlantillaGeneracion) y el
    material entra citado — [Fuente N] — para que toda afirmación sea
    comprobable y toda cita verificable por máquina (libro 3, cap. 14).
    """

    def __init__(self, chat: ClienteChat | None = None,
                 plantilla: PlantillaGeneracion | None = None) -> None:
        self.chat = chat or ClienteChat()
        self.plantilla = plantilla or PLANTILLA_POR_OMISION

    def _contexto(self, cosecha: list[Hit]) -> str:
        return "\n\n".join(
            f"[Fuente {i + 1} · {h.pildora.titulo}]\n{h.pildora.texto}"
            for i, h in enumerate(cosecha)
        )

    def generar(self, consulta: Consulta, cosecha: list[Hit]) -> Respuesta:
        p = self.plantilla
        sistema = f"{p.papel}\n\nMATERIAL:\n{p.material}\n\nPROHIBICIONES:\n{p.prohibiciones}"
        usuario = (
            f"CONSULTA: {consulta.texto}\n\nCONTEXTO:\n{self._contexto(cosecha)}\n\n"
            f"CITAS: {p.citas}\nFORMATO: {p.formato}\nABSTENCIÓN: {p.abstencion}"
        )
        texto = self.chat.completar(sistema, usuario)
        return Respuesta(
            texto=texto,
            citas=tuple(f"Fuente {i + 1}" for i in range(len(cosecha))),
            patron="directo",
        )
```

Y el servicio entero, `cocinando/aplicacion/servir.py` — las cuatro fases en el orden del método:

```python
class ServicioRespuesta:
    """El momento de la verdad: una consulta entra, una respuesta — o una abstención — sale."""

    def __init__(self, repo, embeddings, reescritor, juez, generador, k=10):
        ...

    def responder(self, consulta: Consulta) -> tuple[Respuesta, list]:
        reescrita = self.reescritor.reescribir(consulta)          # 1 · reescribir ANTES de buscar
        vector = self.embeddings.incrustar([reescrita.texto])[0]  # 2 · el vector de lo reescrito
        cosecha = self.repo.buscar_hibrido(                       # 3 · la cosecha híbrida
            vector, lexico=reescrita.texto, k=self.k, dominio=reescrita.dominio
        )
        veredicto = self.juez.veredictar(reescrita, cosecha)      # 4 · el juez, antes de generar
        if not cosecha or veredicto is Veredicto.NO_RESPONDE:
            return (Respuesta(                                    # 5 · la abstención honesta
                        texto="No consta en el corpus; lo más cercano que contiene es "
                              + (cosecha[0].pildora.titulo if cosecha else "nada relacionado") + ".",
                        abstencion=True,
                        motivo_abstencion=f"juez: {veredicto.value}" if cosecha else "cosecha vacía",
                    ), cosecha)
        return self.generador.generar(reescrita, cosecha), cosecha  # 6 · ensamblar
```

*(El listado del servicio está condensado aquí — el constructor completo está en el repo y las piezas que orquesta son los caps. 11-13.)*

## Lo que importa

1. **La plantilla es un dataclass, no un f-string gigante.** Las seis piezas versionan, comparan y pasan la regresión del cap. 16 por separado — "cambiar una frase de la plantilla es un despliegue", dice el libro 3, y aquí el diff de un despliegue se ve línea a línea.
2. **La abstención se decide fuera del generador.** El juez habló antes; si dijo NO_RESPONDE, ni se paga la llamada de redacción — el servicio responde la abstención honesta directamente, con su motivo escrito (`"juez: NO_RESPONDE"`) para el diario del cap. 18. La plantilla lleva su regla de abstención por si el modelo se encuentra el vacío dentro de una cosecha parcial: doble red, por si una falla.
3. **El `temperatura=0` del cliente de chat** — declarado en el cap. 13 y aquí decidivo: la respuesta es un instrumento. La prosa con temperamento es el enemigo que el cap. 13 del libro 3 nombró: fluido no es verdadero.
4. **El servicio no conoce adaptadores.** Recibe puertos y orquesta: el mismo `ServicioRespuesta` corre con BGE-M3 o con la API, con el juez real o con el falso de las pruebas. Es la prueba de fuego de la arquitectura del cap. 2 — y la razón por la que las pruebas del sistema entero corren sin red ni claves.

## Los números

Una respuesta completa del servicio cuesta en el sistema real: **1 llamada de reescritura + 1 de incrustación + 2 consultas SQLite + 1 veredicto + 1 redacción** — cinco llamadas en el orden de segundos, el directo del espectro del libro 3 con toda su ceremonia. La vara de coste la pone el cap. 10 del libro 3: el patrón caro solo donde la pregunta lo exige.

## Enlaces

- Repo: `cocinando/aplicacion/servir.py` · `cocinando/infraestructura/llm.py` · `pruebas/test_servir.py`
- Web: fase [Generación](https://ragcooking.info/biblioteca/)
- Libro 3, caps. 13-14: el contrato de generación y la fidelidad que verificará estas citas · Libro 2, cap. 17: el ensamblado del contexto que entrega el material
