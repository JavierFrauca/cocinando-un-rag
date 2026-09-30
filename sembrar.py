"""Sembrar: cargar la base de datos con el corpus de ejemplo.

El arranque en un minuto, desde la raíz del repositorio:

    python sembrar.py                                       # siembra con embeddings de demo
    python sembrar.py --consultar "plazo de reclamación"    # siembra y consulta
    python sembrar.py --vara                                # siembra y mide la vara
    python sembrar.py --embeddings local                    # con BGE-M3 (descarga el modelo una vez)

La siembra es idempotente: correrla dos veces deja el mismo índice —
la misma promesa de la ingesta del cap. 3, ahora para el arranque entero.
Con `--embeddings demo` no se descarga ningún modelo ni se pide ninguna clave.

Nota: los datos de `datos/` son de demostración — existen para ver el sistema
funcionar de punta a punta, y las métricas que imprime con embeddings de demo
son de juguete. El corpus de verdad es el tuyo: `datos/corpus/` + manifiesto.
"""

from __future__ import annotations

import argparse
import json
import os
from contextlib import contextmanager
from pathlib import Path

from cocinando.aplicacion.aprovisionamiento import Manifiesto, ingesta, normalizar
from cocinando.aplicacion.cocer import cocer, leer_embudo
from cocinando.aplicacion.evaluar import EntradaDataset, Metricas, correr_vara
from cocinando.dominio.modelos import Consulta, Pildora
from cocinando.dominio.pildoras import trocear
from cocinando.dominio.puertos import ClienteEmbeddings, RepositorioPildoras
from cocinando.infraestructura.configuracion import Configuracion, repositorio

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "datos"


@contextmanager
def en_raiz():
    """El manifiesto declara rutas relativas a la raíz del repositorio."""
    anterior = Path.cwd()
    os.chdir(RAIZ)
    try:
        yield
    finally:
        os.chdir(anterior)


def elegir_cliente(nombre: str) -> ClienteEmbeddings:
    """Los mismos dos adaptadores del cap. 8 — y el de demo para arrancar."""
    if nombre == "local":
        from cocinando.infraestructura.embeddings_local import ClienteEmbeddingsLocal
        return ClienteEmbeddingsLocal()
    if nombre == "api":
        from cocinando.infraestructura.embeddings_api import ClienteEmbeddingsApi
        return ClienteEmbeddingsApi()
    from cocinando.infraestructura.embeddings_demo import ClienteEmbeddingsDemo
    return ClienteEmbeddingsDemo()


def sembrar_base(ruta_db: Path, embeddings: ClienteEmbeddings
                 ) -> tuple[RepositorioPildoras, ClienteEmbeddings, list[Pildora]]:
    """Manifiesto → ingesta → normalización → píldoras → cocción. Idempotente."""
    manifiesto = Manifiesto(DATOS / "manifiesto.json")
    repo = repositorio(Configuracion(ruta_db=ruta_db, dimensiones=embeddings.DIMENSIONES))
    pildoras: list[Pildora] = []
    with en_raiz():
        for clave in manifiesto.fuentes:
            entrada = ingesta(Path(clave), manifiesto)
            if entrada is None:
                continue
            pildoras.extend(trocear(
                normalizar(entrada.contenido),
                fuente=entrada.ruta, dominio=entrada.dominio, vigencia=entrada.vigencia,
            ))
    embudo = cocer(pildoras, embeddings, repo)
    print(leer_embudo(embudo))
    print(f"Base sembrada en {ruta_db}: {repo.contar()} píldoras de "
          f"{len(manifiesto.fuentes)} fuentes declaradas en el manifiesto.")
    return repo, embeddings, pildoras


def consultar(repo: RepositorioPildoras, embeddings: ClienteEmbeddings,
              texto: str, k: int = 5) -> list:
    """Una consulta de muestra: la cosecha híbrida, título y canales por Hit."""
    vector = embeddings.incrustar([texto])[0]
    hits = repo.buscar_hibrido(vector, lexico=texto, k=k)
    print(f"\n«{texto}»")
    if not hits:
        print("  (sin resultados — ni el híbrido encuentra lo que no está)")
        return hits
    for h in hits:
        print(f"  {h.score:.4f} [{'+'.join(h.canales)}] {h.pildora.titulo}")
    return hits


def vara_de_ejemplo(pildoras: list[Pildora], repo: RepositorioPildoras,
                    embeddings: ClienteEmbeddings) -> Metricas:
    """La vara sobre el dataset de ejemplo: los titulares del JSON se resuelven a ids."""
    declarado = json.loads((DATOS / "dataset.json").read_text("utf-8"))
    dataset = []
    for fila in declarado:
        ids = frozenset(p.id for p in pildoras
                        if any(titular in p.titulo for titular in fila["titulares"]))
        dataset.append(EntradaDataset(
            consulta=fila["consulta"], relevantes=ids,
            firmada_por=fila.get("firmada_por", ""),
        ))
    metricas = correr_vara(dataset, embeddings, repo)
    print(f"\nVara sobre el dataset de ejemplo: recall@{metricas.k} = "
          f"{metricas.recall_k:.2f} · MRR = {metricas.mrr:.2f} "
          f"sobre {metricas.consultas} consultas firmadas.")
    return metricas


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Sembrar la base de Cocinando un RAG")
    parser.add_argument("--db", default="cocinando.db", help="ruta del archivo SQLite")
    parser.add_argument("--embeddings", choices=("demo", "local", "api"), default="demo",
                        help="demo: hash determinista, instantáneo · local: BGE-M3 · api: OpenAI")
    parser.add_argument("--consultar", action="append", default=[], metavar="TEXTO",
                        help="consulta de muestra tras sembrar (repetible)")
    parser.add_argument("--vara", action="store_true",
                        help="corre la vara sobre el dataset de ejemplo")
    args = parser.parse_args(argv)

    embeddings = elegir_cliente(args.embeddings)
    repo, embeddings, pildoras = sembrar_base(Path(args.db), embeddings)
    if args.vara:
        vara_de_ejemplo(pildoras, repo, embeddings)
    for texto in args.consultar:
        consultar(repo, embeddings, texto)
    if not args.vara and not args.consultar:
        print('Prueba: python sembrar.py --consultar "plazo de reclamación" --vara')


if __name__ == "__main__":
    main()
