"""La puerta de salida de los caps. 9 y 11: índice idempotente, híbrido con RRF, filtro por dominio.

Corre con sqlite-vec y EmbeddingsFalsos: sin modelos, sin red, sin claves.
"""

import pytest

from cocinando.dominio.modelos import Pildora
from cocinando.dominio.pildoras import trocear
from cocinando.infraestructura.sqlite_repo import RepositorioPildorasSqlite
from pruebas.fakes import EmbeddingsFalsos

DOC_A = """# Convenio 2024
## Plazos
El plazo de reclamación es de veinte días hábiles.
## Tarifas
| Concepto | Importe |
|---|---|
| Hora extra | 22 € |
"""

DOC_B = """# Sentencia 88/23
## Plazo de prescripción
La prescripción de la sanción es de un año.
"""


@pytest.fixture()
def repo(tmp_path):
    return RepositorioPildorasSqlite(tmp_path / "prueba.db", dimensiones=64)


def _cocer(repo, doc, fuente):
    embeddings = EmbeddingsFalsos()
    pildoras = trocear(doc, fuente=fuente, dominio="laboral")
    repo.guardar(pildoras, embeddings.incrustar([p.texto for p in pildoras]))
    return pildoras


def test_ingesta_idempotente(repo):
    primera = _cocer(repo, DOC_A, "c24.md")
    _cocer(repo, DOC_A, "c24.md")                     # la misma ingesta, dos veces
    assert repo.contar() == len(primera)              # y el índice no crece


def test_hibrido_devuelve_lo_relevante(repo):
    _cocer(repo, DOC_A, "c24.md")
    _cocer(repo, DOC_B, "s88.md")
    embeddings = EmbeddingsFalsos()
    vector = embeddings.incrustar(["plazo de reclamación veinte días"])[0]
    hits = repo.buscar_hibrido(vector, lexico="plazo de reclamación", k=3)
    assert hits
    assert any("reclamación" in h.pildora.texto for h in hits)
    assert all(h.canales for h in hits)               # cada Hit declara su canal


def test_dominio_filtra_antes_de_fusionar(repo):
    _cocer(repo, DOC_A, "c24.md")
    _cocer(repo, DOC_B, "s88.md")
    embeddings = EmbeddingsFalsos()
    vector = embeddings.incrustar(["plazo"])[0]
    hits = repo.buscar_hibrido(vector, lexico="plazo", k=10, dominio="inexistente")
    assert hits == []                                 # el filtro manda, no el ranking


def test_pildora_guardada_recupera_modelos_completos(repo):
    pildoras = _cocer(repo, DOC_A, "c24.md")
    embeddings = EmbeddingsFalsos()
    objetivo = pildoras[0]
    vector = embeddings.incrustar([objetivo.texto])[0]
    hits = repo.buscar_hibrido(vector, lexico=objetivo.titulo, k=1)
    assert hits[0].pildora == objetivo                # el Hit trae la Pildora entera, no un id suelto
