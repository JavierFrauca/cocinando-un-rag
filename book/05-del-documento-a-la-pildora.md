---
title: "5 · Del documento a la píldora: el chunking"
---

# 5 · Del documento a la píldora: el chunking

La respuesta del cap. 14 del libro 3 citaba una sección que existía — y el dato vivía en otra. Nadie había mentido: el troceador había cortado el manual por tamaño fijo, la cita apuntaba al encabezado correcto de un trozo que ya no contenía el dato, y la verificación de citas solo pudo confirmar que la sección 7.3 no decía lo que la respuesta decía que decía. La mitad de los fallos de fidelidad nacen aquí, aguas arriba de toda la inteligencia del sistema: **en el momento en que alguien decide dónde corta el conocimiento.** Este capítulo es esa decisión, hecha código.

## La decisión

El corpus de la serie se construye sobre la **píldora de información**: la unidad mínima autocontenida, con su texto legible, su referencia y sus metadatos (libro 1, caps. 10-11). La puerta de salida de la fase es verificable — *píldora íntegra; tablas sin cortar* — y dos decisiones del método gobiernan el código. Primera: **la estructura del documento es el corte natural** — los encabezados que el redactor puso son semántica regalada, y el chunking contextual empieza por respetarla, no por ignorarla. Segunda: **la tabla es atómica** — una tabla partida en dos es dos medias verdades, y el modelo que recibe la mitad numérica completa el resto con imaginación (el modo de fallo "extrapolación" del cap. 14 del libro 3, servido por el propio chunking).

La alternativa del mercado — trocear a tamaño fijo con solape — resuelve el problema equivocado: reparte el texto en porciones intercambiables y luego remienda los cortes repitiendo trozos vecinos. Esta implementación no corta a lo loco ni remienda: corta donde el documento ya está cortado, le pone el contexto delante a cada trozo y deja que la guardia de tamaño solo actúe donde la estructura falla.

## El código

`cocinando/dominio/pildoras.py` — del documento a la lista de píldoras, en una pasada. Vive en el dominio y es lógica pura: sin I/O, sin índice, sin saber qué embedding lo cocerá.

```python
# cocinando/dominio/pildoras.py — del documento a la píldora
# Capítulo escrito contra la v0.1 del repositorio de los ejemplos.

from __future__ import annotations

import re

from cocinando.dominio.modelos import MAX_PILDORA, Pildora

ENCABEZADO = re.compile(r"^(#{1,4})\s+(.+)$")


class _Estado:
    """Lo que acumula la píldora en curso mientras se recorre el documento."""

    def __init__(self, fuente: str, dominio: str, vigencia: str | None) -> None:
        self.fuente = fuente
        self.dominio = dominio
        self.vigencia = vigencia
        self.titulo: list[str] = []   # la ruta de encabezados viva
        self.bloque: list[str] = []
        self.orden = 0
        self.en_tabla = False

    def subir(self, nivel: int, texto: str) -> None:
        self.titulo = self.titulo[: nivel - 1] + [texto]

    def cerrar(self, pildoras: list[Pildora]) -> None:
        texto = "\n".join(self.bloque).strip()
        if texto:
            ruta = " > ".join(self.titulo) if self.titulo else "(portada)"
            pildoras.append(Pildora(
                texto=f"[{ruta}]\n\n{texto}",      # el chunking contextual: el contexto viaja con el trozo
                titulo=ruta,
                fuente=self.fuente,
                orden=self.orden,
                tipo="tabla" if self.en_tabla else "texto",
                dominio=self.dominio,
                vigencia=self.vigencia,
            ))
            self.orden += 1
        self.bloque = []
        self.en_tabla = False


def trocear(documento: str, fuente: str, dominio: str = "",
            vigencia: str | None = None) -> list[Pildora]:
    estado = _Estado(fuente, dominio, vigencia)
    pildoras: list[Pildora] = []
    for linea in documento.splitlines():
        encabezado = ENCABEZADO.match(linea)
        if encabezado:
            estado.cerrar(pildoras)                 # la estructura manda: un encabezado cierra
            estado.subir(len(encabezado.group(1)), encabezado.group(2).strip())
            continue
        if linea.lstrip().startswith("|"):
            if not estado.en_tabla:
                estado.cerrar(pildoras)             # la tabla no se mezcla con la prosa
                estado.en_tabla = True
            estado.bloque.append(linea)
            continue
        if estado.en_tabla:
            estado.cerrar(pildoras)                 # la tabla terminó: sale entera
        estado.bloque.append(linea)
        if len("\n".join(estado.bloque)) >= MAX_PILDORA:
            estado.cerrar(pildoras)                 # la guardia: corta en el borde de línea
    estado.cerrar(pildoras)
    return pildoras
```

Cómo leerlo: la función es una máquina de tres estados — texto abierto, tabla abierta, encabezado recién llegado — y cada línea del documento dispara una de tres acciones: cerrar y abrir (encabezado), acumular (línea cualquiera) o cerrar por guardia (tamaño desbordado). Toda la inteligencia está en **cuándo se llama a `cerrar`**: esa función es la única que crea píldoras, y los cuatro sitios desde los que se invoca son las cuatro razones por las que una píldora termina — encabezado nuevo, inicio de tabla, fin de tabla, desborde de tamaño.

Y su puerta de salida, `pruebas/test_pildoras.py` — tres pruebas que son el criterio de salida de la fase hecho `assert`:

```python
def test_tabla_atomica():
    pildoras = trocear(DOC, fuente="c24.md", dominio="convenios")
    tablas = [p for p in pildoras if p.tipo == "tabla"]
    assert len(tablas) == 1
    assert "| Hora extra | 22 € |" in tablas[0].texto        # entera
    assert "Ámbito" not in tablas[0].texto                  # sin mezclar con la prosa


def test_contexto_viaja_con_el_trozo():
    pildoras = trocear(DOC, fuente="c24.md")
    ambito = [p for p in pildoras if "Ámbito" in p.titulo]
    assert ambito and ambito[0].texto.startswith("[Convenio 2024 > 1. Ámbito]")


def test_identidad_idempotente():
    a = trocear(DOC, fuente="x.md")
    b = trocear(DOC, fuente="x.md")
    assert [p.id for p in a] == [p.id for p in b]           # re-ingestar no duplica
    c = trocear(DOC.replace("toda la plantilla", "todo el personal"), fuente="x.md")
    assert [p.id for p in a] != [p.id for p in c]           # cambiar el texto cambia el id
```

## Lo que importa

1. **Un encabezado cierra la píldora.** El corte natural ya está en el documento: el redactor le dio estructura, y esa estructura es semántica regalada. Los troceadores de tamaño fijo la destruyen — cortan frases por la mitad y obligan al solape a remendar lo roto. Aquí la estructura manda y el tamaño solo arbitra. La consecuencia práctica: **la calidad del chunking se hereda de la calidad de la escritura** — un documento sin encabezados será troceado por la guardia, y el embudo del cap. 10 lo delatará.
2. **Las tablas son atómicas y viajan con tipo propio.** Una tabla cortada en dos píldoras produce lo que el cap. 14 del libro 3 llama extrapolación: el modelo recibe la mitad numérica y completa el resto con imaginación. La tabla entra, se completa y sale entera, marcada `tipo="tabla"` para que el ensamblado (libro 2, cap. 17) la trate distinto de la prosa — y para que la vara sepa que una tabla citada entera es la única forma legítima de citarla.
3. **El encabezado viaja con el texto.** El prefijo `[Convenio 2024 > 3. Plazos]` es el *chunking contextual*: el embedding se cocina con el contexto dentro, la búsqueda encuentra la píldora por su contenido, y el modelo que la recibe aislada sabe de qué habla. Sin él, cada píldora es un huérfano que el modelo rellena con lo que le parece — y las respuestas heredan la imaginación ajena.
4. **La identidad nace del contenido, no de la posición.** El `id` es el hash de fuente+texto: re-ingestar el mismo documento no duplica el índice, y cambiar un párrafo solo regenera las píldoras afectadas. Es la **manutención idempotente** del libro 1 (caps. 18 y 20) hecha una línea de código — sin ella, la ingesta semanal duplica el corpus en silencio, y el primer síntoma es una respuesta que cita la misma tabla dos veces.
5. **El máximo es una guardia, no un objetivo.** El corte por tamaño solo dispara cuando un bloque desborda, y corta en el borde de línea más próximo — nunca dentro de una tabla ni a mitad de palabra. Si la guardia dispara a menudo, el problema no es el número: es que la estructura de encabezados del documento es demasiado gruesa, y eso se arregla aguas arriba, en el documento.
6. **Sin solape.** El *overlap* de los troceadores de tamaño fijo no existe aquí por decisión: el solape es duplicidad, y la duplicidad la paga el ensamblado (el libro 2, cap. 14, la llama fotocopia — dos píldoras casi iguales ocupando el tope). El contexto que un trozo "olvida" viaja en su título, no repitiendo el texto del vecino.
7. **La alternativa descartada: el corte semántico por embeddings.** Existen troceadores que agrupan frases por similitud de vectores. Para documentos legales — donde la jerarquía del documento YA es la semántica — añaden un modelo, una factura y una opacidad para reinventar lo que el redactor ya escribió con sus encabezados. Su terreno sería el documento sin estructura; y ahí, esta implementación prefiere que el embudo delate la falta de estructura antes que la disimule.
8. **`orden` no es decoración: es el orden del ensamblado.** El ensamblado del libro 2 reordena y recorta dentro del presupuesto; saber qué píldora iba antes en el documento es lo que permite reconstruir el hilo cuando la respuesta necesita dos secciones contiguas. Sin `orden`, el ensamblado solo tendría puntuaciones — y las puntuaciones no dicen si la sección 3 va antes que la 4.

## Los números

- **1.200 caracteres** es el valor por omisión del repositorio — del orden de 300 tokens en español. El techo real lo fija tu modelo de embeddings: su ventana de tokens menos lo que ocupe el título de contexto (la [fase Embedding de la web](https://ragcooking.info/biblioteca/embedding/) lleva la tabla de ventanas por modelo). Con BGE-M3 y sus 8.192 tokens, el margen es de más de veinte veces: el título y el contexto no son nunca el problema — el problema sería un documento sin encabezados.
- Una **tabla que desborda la ventana del embedding no se corta aquí**: va entera al índice y se truncará al cocer. Eso no se arregla en esta fase — se detecta en la medición del ruido (cap. 10), y su arreglo es de estructura del documento, no de esta función.
- La fuente lleva **versión** (`fuente="convenio_2024@v3"` en el sistema real): el id hereda la versión, y una revisión del convenio genera píldoras nuevas que conviven con las viejas hasta que el ciclo de vida retira las muertas — tal como manda el libro 1.
- El número que conviene medir en el sistema propio al arrancar: **píldoras por documento** (la granularidad que produce tu estructura) y **proporción de cortes por guardia** (debería ser baja; si no, tus encabezados mienten).

## Enlaces

- Repo: `cocinando/dominio/pildoras.py` · `pruebas/test_pildoras.py`
- Web: fase [Chunking](https://ragcooking.info/biblioteca/chunking/) · [fase Estructura](https://ragcooking.info/biblioteca/)
- Libro 1, caps. 10-11: chunking contextual y tablas atómicas · Libro 2, caps. 14 y 17: la diversidad y el ensamblado que reciben estas píldoras · Libro 3, cap. 14: la extrapolación que este corte evita
