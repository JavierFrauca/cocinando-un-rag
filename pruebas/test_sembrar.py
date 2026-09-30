"""La puerta de salida del sembrador: la base se carga, se re-carga sin crecer y se consulta."""

import sembrar


def test_sembrar_idempotente_y_consultable(tmp_path):
    embeddings = sembrar.elegir_cliente("demo")
    repo, embeddings, pildoras = sembrar.sembrar_base(tmp_path / "demo.db", embeddings)
    primera = repo.contar()
    assert primera > 0
    assert len(pildoras) >= 6                       # tres documentos con estructura

    repo2, _, _ = sembrar.sembrar_base(tmp_path / "demo.db", embeddings)
    assert repo2.contar() == primera                # la segunda siembra no duplica


def test_consulta_encuentra_lo_sembrado(tmp_path):
    embeddings = sembrar.elegir_cliente("demo")
    repo, embeddings, _ = sembrar.sembrar_base(tmp_path / "demo.db", embeddings)
    hits = sembrar.consultar(repo, embeddings, "permiso por asuntos propios", k=3)
    assert hits
    assert any("Permisos" in h.pildora.titulo for h in hits)


def test_vara_de_ejemplo_mide(tmp_path):
    embeddings = sembrar.elegir_cliente("demo")
    repo, embeddings, pildoras = sembrar.sembrar_base(tmp_path / "demo.db", embeddings)
    metricas = sembrar.vara_de_ejemplo(pildoras, repo, embeddings)
    assert metricas.consultas == 3                  # las tres consultas firmadas del dataset
    assert metricas.recall_k > 0.0
