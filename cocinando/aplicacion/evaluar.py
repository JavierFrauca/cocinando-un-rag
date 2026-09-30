"""La vara y la regresión, en código (caps. 15-16).

El dataset áureo de consultas con verdad firmada, las dos métricas
contractuales (recall@k y MRR) y el examen que bloquea el despliegue:
cero diferencias sin explicación, no cero diferencias.
"""

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


@dataclass(frozen=True)
class VeredictoRegresion:
    """El examen antes del despliegue: aprueba o bloquea, con su explicación."""

    aprueba: bool
    explicacion: str


TOLERANCIA = 0.02  # el ruido estadístico admisible; más que esto, es una regresión


def comparar_regresion(antes: Metricas, despues: Metricas) -> VeredictoRegresion:
    """Cero diferencias sin explicación, no cero diferencias.

    La regresión bloquea si el recall cae por debajo de la tolerancia.
    Las mejoras pasan; las caídas, no — y el número lo dice, no la intuición.
    """
    caida = antes.recall_k - despues.recall_k
    if caida > TOLERANCIA:
        return VeredictoRegresion(
            aprueba=False,
            explicacion=(
                f"regresión: recall {antes.recall_k:.3f} → {despues.recall_k:.3f} "
                f"(−{caida:.3f} > tolerancia {TOLERANCIA})"
            ),
        )
    return VeredictoRegresion(
        aprueba=True,
        explicacion=f"recall {antes.recall_k:.3f} → {despues.recall_k:.3f}: dentro de tolerancia",
    )
