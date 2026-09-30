---
title: "15 · El dataset áureo y la vara, en código"
---

# 15 · El dataset áureo y la vara, en código

## La decisión

El dataset de consultas con verdad firmada (libro 1, cap. 16) y las dos métricas contractuales del acceso (libro 2, cap. 18): **recall@k** — de lo que debía salir, ¿cuánto salió? — y **MRR** — ¿en qué puesto salió el primer acierto?. Y una regla que aquí es código: la vara se niega a medir verdades sin firma — un dataset sin autor no es verdad, es una opinión con formato.

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

Su prueba — la vara mide de verdad sobre un corpus de juguete:

```python
def test_vara_sobre_dataset_pequeño(tmp_path):
    ...
    metricas = correr_vara(dataset, embeddings, repo, k=5)
    assert metricas.recall_k > 0.0                     # la vara mide, no presume
    assert metricas.mrr > 0.0
```

## Lo que importa

1. **La firma es una precondición, otra vez.** La misma disciplina que el cap. 7 — quien resuelve a mano firma la verdad — aquí en el dataset: `cargar_dataset` y `correr_vara` ambas rechazan lo anónimo. Dos puertas porque el dataset entra por muchas manos, y basta una puerta floja para que la vara mida opiniones.
2. **El recall se promedia por consulta, no por píldora.** `len(set(ids) & relevantes) / len(relevantes)` por fila: una consulta con tres verdades cuenta cada tercio, y una con una cuenta entera o cero. Promediar píldoras solas premiaría a las consultas fáciles — el promedio que "va bien" mientras las difíciles naufragian, que es lo que el libro 2 prohibió.
3. **La MRR solo mira el primer acierto** — `1/puesto` del primero, cero si no hubo. Es la métrica de la cabeza: la que captura la experiencia de quien pregunta, porque nadie mira el puesto nueve.
4. **La vara corre sobre el MISMO servicio que produce.** Incrusta con el `ClienteEmbeddings` real y busca con el `RepositorioPildoras` real — no hay una vara de laboratorio y otra de producción. Por eso sus números se pueden firmar en el contrato.

## Los números

El tamaño honesto del dataset, como dijo el libro 2: **unas decenas de entradas bien elegidas** — las familias de la matriz, los bordes del corpus, los incidentes de los últimos meses — sostienen una regresión útil. Crece por heridas: cada incidente entra con su verdad firmada, y convierte la herida de un usuario en inmunidad del sistema. En el despacho, el objetivo contractual del recall es **90% en top-10 para fácticas** — el número del contrato, no el del folleto.

## Enlaces

- Repo: `cocinando/aplicacion/evaluar.py` · `pruebas/test_evaluar.py`
- Web: fase [Evaluación](https://ragcooking.info/biblioteca/)
- Libro 1, cap. 16: el dataset áureo de origen · Libro 2, cap. 18: recall@k, MRR y nDCG, con los objetivos por tipo
