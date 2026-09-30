---
title: "1 · Cómo se lee este libro"
---

# 1 · Cómo se lee este libro

Este libro es de un género poco servido: el comentario anotado de una implementación de referencia. Conviene fijar en dos páginas cómo se lee, porque no se lee como los tres anteriores.

## De dónde sale el código

Todo el código de este libro vive en el **repositorio de los ejemplos** — ejecutable, versionado y con sus pruebas. Los listados que aparecen aquí son fragmentos de ese repositorio, congelados en la fecha de publicación de cada capítulo; el repo lleva la versión corriente. Conviene la regla de siempre de la serie, aplicada al software: **las notas no envejecen; las versiones, sí**. Si un listado de este libro y el repo discrepan, gana el repo — y la nota debería seguir explicando el porqué de lo que ambos hacen.

Cada capítulo declara contra qué versión se escribió. Es lo honesto: este código corre contra modelos y motores que cambian cada trimestre, y fingir lo contrario sería traicionar la propia serie.

## La anatomía de cada capítulo

Cada capítulo es una pieza de la implementación, siempre con las mismas cinco secciones:

**La decisión.** Dos o tres frases que sitúan qué regla del método ejecuta el código — y en qué libro se enseña. Este libro no rejustifica las decisiones: las cita. El porqué vive en *El Origen del Conocimiento*, en *Accediendo al Conocimiento* y en *Aplicando el Conocimiento*; el cómo vive aquí.

**El código.** El listado completo de la pieza, con su ruta real en el repositorio. Los listados son completos en lo que enseñan: sin `# ...resto del código...` ni elipsis que obliguen a adivinar. Lo que se omite es lo que otra pieza del libro cubre — y se dice.

**Lo que importa.** El corazón del libro: las notas numeradas sobre las líneas que deciden. No todo el código merece explicación — el andamiaje se lee solo. Las notas señalan las líneas donde el método vive dentro del software: el convenio que sostiene la función, el error que pagó la salvaguarda, el porqué de un valor que parece arbitrario. Quien lea solo esta sección de cada capítulo se llevará el sistema entero; quien las lea con el código delante, lo podrá reconstruir.

**Los números.** Los valores del sistema real — tamaños, umbrales, resultados medidos — con su fecha. Cuando un número sea un valor por omisión del repositorio y no una medida del sistema, se dice. La serie no falsifica cifras; este libro tampoco.

**Enlaces.** La ruta en el repo, la fase correspondiente de [ragcooking.info](https://ragcooking.info/), y los capítulos de los libros que enseñan la decisión.

## Dos convenciones

**Primera: el vocabulario es el de la serie — también en el código.** Los identificadores hablan el idioma del método: `Pildora`, `Veredicto`, `trocear`, `correr_vara` — para que el libro y el código compartan diccionario y nadie traduzca dos veces. Solo lo que no tiene buena traducción queda en inglés (`embedding`, `Hit`); el [diccionario de la web](https://ragcooking.info/diccionario) traduce al vocabulario estándar de la industria quien lo necesite.

**Segunda: los números de omisión no son receta universal.** Cuando el código traiga un valor por omisión — un tamaño máximo de píldora, un k, un umbral — es el punto de partida que el sistema real usa como hipótesis inicial, no la cifra que tu corpus necesita. El método de los libros mide; este libro ejecuta. El número lo fija tu dataset, no este libro.

**Tercera: la implementación vive en tres capas.** *Dominio* — los modelos, los puertos (los contratos, escritos como `Protocol`) y la lógica pura del método: el chunking no sabe qué embedding lo cocerá. *Aplicación* — los casos de uso, uno por fase: orquestan puertos y no conocen SQLite ni BGE-M3. *Infraestructura* — los adaptadores intercambiables: sqlite-vec, embeddings locales o de API, el LLM. El patrón repository no es un adorno de arquitecto: **el repositorio es el contrato de recuperación de la serie hecho interfaz** — y por eso cambiar de motor es un despliegue con regresión, no una reescritura.

## Por dónde empezar

Si has leído los tres libros: en orden, el mapa de la receta primero y luego la pieza que más te duela. Si vienes solo por una pieza: cada capítulo se lee solo, con su decisión citada en dos frases. Si diriges sin programar: las secciones "La decisión" y "Los números" de cada capítulo bastan para discutir la implementación con quien la construye.
