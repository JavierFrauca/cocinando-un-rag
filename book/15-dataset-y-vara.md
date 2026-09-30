---
title: "15 · El dataset áureo y la vara, en código"
---

# 15 · El dataset áureo y la vara, en código

El embedding nuevo "se notaba mucho mejor" — cinco consultas a mano, cinco vuelos — y la vara lo midió sobre el dataset completo: tres puntos de recall menos, todos en las bordes, que son las que compran la vara. La diferencia entre la anécdota y la arquitectura está en este capítulo: **un dataset de consultas con verdad firmada** y **dos métricas contractuales** — recall@k y MRR — que convierten "se nota mejor" en un número con firma. El dataset áureo que el libro 1 instituyó para validar el Gold y que el libro 2 convirtió en vara del acceso (cap. 18), aquí con su código — que es donde deja de ser doctrina y se vuelve práctica de equipo.

## La decisión

Tres decisiones, todas de gobierno más que de ingeniería. **La vara se niega a medir verdades sin firma** — un dataset sin autor no es verdad, es una opinión con formato; el chequeo corre en las dos puertas (al cargar y al medir) porque el dataset entra por muchas manos. **El recall se promedia por consulta, no por píldora** — una consulta con tres verdades cuenta cada tercio; promediar píldoras solas premia a las consultas fáciles, que es el promedio que "va bien" mientras las difíciles naufragian. **La vara corre sobre el mismo servicio que produce** — incrusta con el cliente real y busca con el repositorio real: no hay una vara de laboratorio y otra de producción, y por eso sus números se pueden firmar en el contrato.

## El código

`cocinando/aplicacion/evaluar.py` — la primera mitad:

```python
# cocinando/aplicacion/evaluar.py
# La vara y la regresión, en código (caps. 15-16).

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from cocinando.dominio.modelos import EntradaDataset, Metricas
from cocinando.dominio.puertos import ClienteEmbeddings, RepositorioPildoras


def cargar_dataset(fichero: Path) -> list[EntradaDataset]:
    """Las filas firmadas del dataset áureo — sin firma, no son verdad."""
    filas = json.loads(fichero.read_text("utf-8"))
    dataset = [
        EntradaDataset(
            consulta=f["consulta"],
            relevantes=frozenset(f["relevantes"]),
            firmada_por=f.get("firmada_por", ""),
        )
        for f in filas
    ]
    sin_firma = [e.consulta for e in dataset if not e.firmada_por]
    if sin_firma:
        raise ValueError(f"entradas de dataset sin firma humana: {sin_firma}")
    return dataset


def correr_vara(dataset: list[EntradaDataset], embeddings: ClienteEmbeddings,
                repo: RepositorioPildoras, k: int = 10) -> Metricas:
    """Recall@k y MRR sobre el dataset: las dos métricas del contrato del acceso.

    recall@k: de lo que debía salir, ¿cuánto salió dentro del tope? — la métrica
    del olvido. MRR: ¿en qué puesto salió el primer acierto? — la métrica de la cabeza.
    La vara se niega a medir verdades sin firma: un dataset sin autor no es verdad.
    """
    sin_firma = [e.consulta for e in dataset if not e.firmada_por]
    if sin_firma:
        raise ValueError(f"entradas de dataset sin firma humana: {sin_firma}")
    aciertos_recall = 0
    inversos = 0.0
    for entrada in dataset:
        vector = embeddings.incrustar([entrada.consulta])[0]
        cosecha = repo.buscar_hibrido(vector, lexico=entrada.consulta, k=k)
        ids = [h.pildora.id for h in cosecha]
        aciertos_recall += len(set(ids) & entrada.relevantes) / len(entrada.relevantes)
        puestos = [i + 1 for i, pid in enumerate(ids) if pid in entrada.relevantes]
        inversos += 1.0 / puestos[0] if puestos else 0.0
    n = len(dataset)
    return Metricas(recall_k=aciertos_recall / n, mrr=inversos / n, k=k, consultas=n)
```

Cómo se leerlo: dos métricas en un solo pase, porque comparten cosecha. El **recall@k** suma, por consulta, la fracción de las verdades que aparecieron dentro del tope — la métrica del olvido: la evidencia existía y no llegó. La **MRR** toma el inverso del puesto del primer acierto — 1 si salió primera, 0,2 si salió quinta, 0 si no salió — la métrica de la cabeza: la que captura la experiencia de quien pregunta, porque nadie mira el puesto nueve.

Y su prueba — la vara mide de verdad sobre un corpus de juguete, y se niega a lo anónimo:

```python
def test_vara_sobre_dataset_pequeño(tmp_path):
    ...
    metricas = correr_vara(dataset, embeddings, repo, k=5)
    assert metricas.recall_k > 0.0                     # la vara mide, no presume
    assert metricas.mrr > 0.0

def test_dataset_sin_firma_no_es_verdad():
    sin_firma = [EntradaDataset(consulta="x", relevantes=frozenset({"a"}), firmada_por="")]
    with pytest.raises(ValueError):
        correr_vara(sin_firma, EmbeddingsFalsos(),
                    RepositorioPildorasSqlite(":memory:", dimensiones=64))
```

## Lo que importa

1. **La firma es una precondición, otra vez.** La misma disciplina que el cap. 7 — quien resuelve a mano firma la verdad — aquí en el dataset: `cargar_dataset` y `correr_vara` ambas rechazan lo anónimo. Dos puertas porque el dataset entra por muchas manos, y basta una puerta floja para que la vara mida opiniones. El detalle de `firmada_por=""` en la prueba: la firma vacía no siempre llega como `None`.
2. **El recall se promedia por consulta, no por píldora.** `len(set(ids) & relevantes) / len(relevantes)` por fila: una consulta con tres verdades cuenta cada tercio, y una con una cuenta entera o cero. Promediar píldoras solas premiaría a las consultas fáciles — el promedio global que esconde a las víctimas, que es lo que el libro 2 prohibió con sus "objetivos por tipo, no objetivos globales".
3. **La MRR solo mira el primer acierto** — `1/puesto` del primero, cero si no hubo. Es la métrica de la cabeza: la que más se movió cuando el despacho instaló su rerank, y la que mejor captura la experiencia vivida. Un sistema puede tener recall decente y MRR penosa: encuentra todo, en el lugar equivocado — el usuario lo vive como un sistema que nunca acierta.
4. **La vara corre sobre el MISMO servicio que produce.** Incrusta con el `ClienteEmbeddings` real y busca con el `RepositorioPildoras` real — no hay una vara de laboratorio y otra de producción. Por eso sus números se pueden firmar en el contrato: miden exactamente la máquina que los usuarios padecen o disfrutan.
5. **El `k` de la vara es el k del contrato.** Medir recall@50 cuando el contrato promete @10 es inflar el número: el recall que no está dentro del tope servido no existe para el usuario. Por eso `Metricas` lleva el `k` dentro — el número viaja con las condiciones de su medición.
6. **Lo que falta, declarado: el nDCG.** Para las consultas sintéticas — panoramas donde importa qué tan bien está cada puesto y a qué distancia de la cabeza — el libro 2 añadió la tercera métrica (nDCG). Esta implementación la deja fuera a propósito: su dataset de arranque es de fácticas y cruces, y añadir nDCG sin consultas de escalera sería métrica por cumplir. Cuando las sintéticas entren por la puerta, la vara crece con ellas.

## Los números

El tamaño honesto del dataset, como dijo el libro 2: **unas decenas de entradas bien elegidas** — las familias de la matriz, los bordes del corpus, los incidentes de los últimos meses — sostienen una regresión útil. Crece por heridas: cada incidente entra con su verdad firmada, y convierte la herida de un usuario en inmunidad del sistema. En el despacho, el objetivo contractual es **90% de recall en top-10 para fácticas** — el número del contrato, no el del folleto — con la regla de oro de siempre: ningún cambio del acceso se aplica sin su número antes-después.

## Enlaces

- Repo: `cocinando/aplicacion/evaluar.py` · `pruebas/test_evaluar.py`
- Web: fase [Evaluación](https://ragcooking.info/biblioteca/)
- Libro 1, cap. 16: el dataset áureo de origen · Libro 2, cap. 18: recall@k, MRR y nDCG, con los objetivos por tipo · Cap. 16 de este libro: lo que la vara bloquea
