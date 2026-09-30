---
title: "14 · La generación ensamblada"
---

# 14 · La generación ensamblada

La cita decorativa — la referencia plausible que apunta a un documento que nunca se entregó — no nace en la verificación: nace aquí, en la redacción, cuando el modelo compone libre y cita de oído. El antídoto del libro 3 (cap. 13) tiene dos mitades y ambas son de diseño, no de suerte: **la plantilla como contrato versionado** — seis piezas escritas, no improvisadas en un prompt — y **el material citado por construcción** — cada bloque de contexto numerado `[Fuente N]` para que toda afirmación remita a su píldora y toda cita sea verificable por máquina. Este capítulo pone las dos mitades en código, y de propina reúne el servicio entero: las cuatro fases — reescribir, buscar, juzgar, generar — en el orden del método y en ningún otro.

## La decisión

**Ensamlar, no componer.** La plantilla del libro 3 (cap. 13) hecha código con una decisión de arquitectura que lo cruza todo: **la plantilla es un dato** (`PlantillaGeneracion`), no un f-string pegado en el código. Las seis piezas — papel, material, prohibiciones, citas, formato, abstención — versionan, comparan y pasan la regresión del cap. 16 por separado; "cambiar una frase de la plantilla es un despliegue", dice el libro 3, y aquí el diff de ese despliegue se ve línea a línea. La segunda decisión: **la abstención se decide fuera del generador** — el juez habló antes, y si dijo NO_RESPONDE, ni se paga la llamada de redacción. Doble red: el servicio abstiene por veredicto, y la plantilla lleva su regla de abstención por si el modelo se encuentra el vacío dentro de una cosecha parcial.

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

Las seis piezas de la plantilla se reconocen al instante: el papel con su relación a la verdad, el material con sus reglas de uso de los bloques, las prohibiciones — el inventario de los modos de fallo del cap. 1 del libro 3 traducido a instrucciones —, el grado de cita, el formato de audiencia y la regla de abstención con su condición. No falta ninguna; ninguna sobra.

Y el servicio entero, `cocinando/aplicacion/servir.py` — la orquestación que reúne los caps. 11-13:

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

*(El listado del servicio está condensado aquí — el constructor completo está en el repo, y las piezas que orquesta son los caps. 11-13. La prueba del servicio verifica las tres conductas: el flujo feliz con cosecha citada, la abstención honesta con su motivo, y la reescritura corriendo una vez antes de buscar.)*

## Lo que importa

1. **La plantilla es un dataclass, no un f-string gigante.** Las seis piezas versionan, comparan y pasan la regresión del cap. 16 por separado — cambiar la regla de abstención es un diff de una línea con su hipótesis escrita. Es la diferencia entre "toca el prompt y reza" y el cap. 13 del libro 3 entero: hipótesis, regresión, despliegue. Las plantillas que crecen por parches de urgencia son el equivalente exacto del corpus sin manifiesto.
2. **La abstención se decide fuera del generador.** El juez habló antes; si dijo NO_RESPONDE, ni se paga la llamada de redacción — el servicio responde la abstención honesta directamente, con su motivo escrito (`"juez: NO_RESPONDE"`) para el diario del cap. 18. La plantilla lleva su regla de abstención por si el modelo se encuentra el vacío dentro de una cosecha parcial: doble red, por si una falla. Y la abstención del servicio es de las buenas: **nombra lo más cercano que contiene** — el "no" que orienta.
3. **El `temperatura=0` del cliente de chat — declarado en el cap. 13 y aquí decidivo.** La respuesta es un instrumento, no una prosa: mismo cosecha, mismo respuesta, para que la regresión compare cambios del sistema y no estados de ánimo del modelo. La prosa con temperamento es el enemigo que el cap. 13 del libro 3 nombró: fluido no es verdadero.
4. **El servicio no conoce adaptadores.** Recibe puertos y orquesta: el mismo `ServicioRespuesta` corre con BGE-M3 o con la API, con el juez real o con el falso de las pruebas. Es la prueba de fuego de la arquitectura del cap. 2 — y la razón por la que las pruebas del sistema entero corren sin red ni claves. Cuando toque cambiar el motor o el modelo, el cambio es de fábrica; el orden de las fases no se toca.
5. **El orden de las fases no se negocia.** Reescribir ANTES de buscar (la mejor formulación merece la búsqueda), juzgar ANTES de generar (el veredicto barato antes que la redacción cara), abstenerse ANTES de componer (el vacío no se rellena). Invertir el orden no rompe el código: rompe el método — y sus facturas.
6. **Lo que el generador NO hace.** No verifica sus citas — esa es la vara de fidelidad del cap. 14 del libro 3, que en esta implementación queda para la siguiente versión del repo (declarado, no fingido): el bloque de verificación de la respuesta — fidelidad frase a frase y control de contradicciones — es la pieza que falta entre este capítulo y el 15. Lo que sí devuelve es la cosecha entera junto a la respuesta, para que esa verificación futura tenga su material.

## Los números

Una respuesta completa del servicio cuesta en el sistema real: **1 llamada de reescritura + 1 de incrustación + 2 consultas SQLite + 1 veredicto + 1 redacción** — cinco llamadas en el orden de segundos, el directo del espectro del libro 3 con toda su ceremonia. La vara de coste la pone el cap. 10 del libro 3: el patrón caro solo donde la pregunta lo exige — y la escena del cap. 11 de este libro (el router) es quien decide qué consulta paga esta coreografía entera y cuál se va al directo en tres segundos.

## Enlaces

- Repo: `cocinando/aplicacion/servir.py` · `cocinando/infraestructura/llm.py` · `pruebas/test_servir.py`
- Web: fase [Generación](https://ragcooking.info/biblioteca/)
- Libro 3, caps. 13-14: el contrato de generación y la fidelidad que verificará estas citas · Libro 2, cap. 17: el ensamblado del contexto que entrega el material
