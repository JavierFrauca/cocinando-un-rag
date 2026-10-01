---
title: Cocinando un RAG
description: Las notas del código — la implementación de referencia del método de la serie
---

# COCINANDO UN RAG

### Las notas del código — la implementación de referencia del método de la serie

---

Los tres libros anteriores no contienen ni una línea de código, y lo declaran sin disimulo: *método, criterio y plantillas*. Este libro es la otra mitad del pacto: **el código que ejecuta ese método**, con sus anotaciones — no un tutorial que copiar, sino las notas de taller sobre las partes que más importan, tal como quedaron escritas en el RAG real de un despacho laboral.

El catálogo de ingredientes vive en [ragcooking.info](https://ragcooking.info/) — 5 estaciones, 18 fases, 75 piezas, con sus comparativas de modelos y motores. El porqué de cada decisión vive en los tres libros. Aquí vive el cómo: **la receta entera, cocinada**, con el código abierto sobre la mesa.

## El género de este libro

Cada capítulo es una pieza de la implementación, siempre con la misma anatomía:

| Sección | Qué contiene |
|---------|--------------|
| **La decisión** | Qué decisión del método resuelve este código — y en qué libro se enseña |
| **El código** | El listado completo, con su ruta en el repositorio de los ejemplos |
| **Lo que importa** | Las notas sobre las líneas que deciden — el corazón del libro |
| **Los números** | Los valores del sistema real: tamaños, umbrales, resultados medidos |
| **Enlaces** | Repo, fase de la web, capítulos de los libros |

## El mapa

| Parte | Fases de la web | Capítulos |
|-------|-----------------|-----------|
| El taller | — | cómo se lee este libro · la receta entera |
| I · Aprovisionamiento | Corpus · Ingesta · Normalización · Limpieza | manifiesto e ingesta · normalización y limpieza |
| II · Preparación | Estructura · Chunking · Metaetiquetado · Síntesis | la píldora · el payload · la síntesis Gold |
| III · Cocción | Embedding · Almacenamiento · Ruido | embeddings · el índice · el ruido |
| IV · Servicio | Recuperación · Reranking · Generación | híbrido RRF · la reescritura que faltaba · rerank y juez · generación ensamblada |
| V · Calidad y gobierno | Evaluación · Gobierno | dataset y vara · regresión en CI · router en vivo · panel y triaje |

## Con qué se cocina

**Python** · **SQLite con `sqlite-vec` + FTS5** — dos canales, un archivo, sin servidor ni contenedor (Qdrant, a una regresión de distancia por el puerto del repositorio) · **BGE-M3 local por omisión** (la API como segundo adaptador) · **tres capas** — dominio, aplicación, infraestructura — con el patrón repository como contrato: `cocinando/`, en este mismo repositorio, con sus pruebas.

## Por dónde empezar

- El **prólogo**, para el pacto de este libro con los tres anteriores.
- **Cómo se lee este libro**, para el formato de las notas (dos páginas que ahorran malentendidos).
- El capítulo **5 · Del documento a la píldora**, completo, como muestra del género entero.

## Estado

✅ **Borrador completo** — prólogo, método de lectura, mapa y 17 capítulos con su código; la implementación de referencia (`cocinando/`) vive en este mismo repositorio con sus 26 pruebas y su CI. Pendiente de revisión final y de publicar el sitio.

## Licencia y citación

Texto bajo **CC BY-NC-SA 4.0**. Para citarla: *Frauca, J., & ZCode (GLM, Z.ai), 2026. Cocinando un RAG — Las notas del código*. Coautoría humano-IA declarada.
