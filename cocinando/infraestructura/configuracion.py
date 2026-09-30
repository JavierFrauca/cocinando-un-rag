"""La configuración: los modelos y motores en un solo sitio.

El cambio de embedding o de motor es un despliegue con regresión
(libro 2, cap. 19) — no una caza de cadenas de texto por el código.
Aquí vive la única fábrica que sabe qué adaptadores hay montados.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from cocinando.dominio.puertos import ClienteEmbeddings, RepositorioPildoras
from cocinando.infraestructura.sqlite_repo import RepositorioPildorasSqlite


@dataclass(frozen=True)
class Configuracion:
    ruta_db: Path = Path("cocinando.db")
    dimensiones: int = 1024              # BGE-M3; la API pide 1536 — el índice se recocina
    k: int = 10
    embeddings: str = "local"            # "local" | "api" — variable COCINANDO_EMBEDDINGS


def cliente_embeddings(config: Configuracion | None = None) -> ClienteEmbeddings:
    """El puerto ClienteEmbeddings con sus dos adaptadores (cap. 8)."""
    config = config or Configuracion(embeddings=os.environ.get("COCINANDO_EMBEDDINGS", "local"))
    if config.embeddings == "api":
        from cocinando.infraestructura.embeddings_api import ClienteEmbeddingsApi
        return ClienteEmbeddingsApi()
    from cocinando.infraestructura.embeddings_local import ClienteEmbeddingsLocal
    return ClienteEmbeddingsLocal()


def repositorio(config: Configuracion | None = None) -> RepositorioPildoras:
    """El puerto RepositorioPildoras: SQLite por omisión; Qdrant, a una regresión."""
    config = config or Configuracion()
    return RepositorioPildorasSqlite(config.ruta_db, dimensiones=config.dimensiones)
