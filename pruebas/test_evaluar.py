"""La puerta de salida de los caps. 15-16: la vara mide y la regresión bloquea."""

import pytest

from cocinando.aplicacion.evaluar import comparar_regresion, correr_vara
from cocinando.dominio.modelos import EntradaDataset, Metricas, Pildora
from cocinando.infraestructura.sqlite_repo import RepositorioPildorasSqlite
from pruebas.fakes import EmbeddingsFalsos

from cocinando.dominio.pildoras import trocear

DOC = "# Convenio\n## Plazos\nEl plazo de reclamación es de veinte días.\n"


def test_vara_sobre_dataset_pequeño(tmp_path):
    repo = RepositorioPildorasSqlite(tmp_path / "p.db", dimensiones=64)
    embeddings = EmbeddingsFalsos()
    pildoras = trocear(DOC, fuente="c24.md", dominio="laboral")
    repo.guardar(pildoras, embeddings.incrustar([p.texto for p in pildoras]))

    dataset = [EntradaDataset(
        consulta="plazo de reclamación",
        relevantes=frozenset(p.id for p in pildoras),
        firmada_por="J. Frauca",
    )]
    metricas = correr_vara(dataset, embeddings, repo, k=5)
    assert metricas.recall_k > 0.0                     # la vara mide, no presume
    assert metricas.mrr > 0.0
    assert metricas.consultas == 1


def test_dataset_sin_firma_no_es_verdad():
    sin_firma = [EntradaDataset(consulta="x", relevantes=frozenset({"a"}), firmada_por="")]
    with pytest.raises(ValueError):
        correr_vara(sin_firma, EmbeddingsFalsos(),
                    RepositorioPildorasSqlite(":memory:", dimensiones=64))


def test_la_regresion_bloquea_la_caida_y_pasa_la_mejora():
    antes = Metricas(recall_k=0.90, mrr=0.8, k=10, consultas=30)
    caida = Metricas(recall_k=0.80, mrr=0.7, k=10, consultas=30)
    estable = Metricas(recall_k=0.89, mrr=0.8, k=10, consultas=30)
    mejora = Metricas(recall_k=0.94, mrr=0.9, k=10, consultas=30)

    assert not comparar_regresion(antes, caida).aprueba       # la caída bloquea
    assert comparar_regresion(antes, estable).aprueba         # el ruido estadístico pasa
    assert comparar_regresion(antes, mejora).aprueba          # la mejora pasa
