"""Los objetos del método: las piezas de datos que las fases se pasan entre sí.

Nada aquí conoce a SQLite, a BGE-M3 ni a ningún proveedor: el dominio
no sabe con qué se cocina — esa es la gracia de la arquitectura.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum

MAX_PILDORA = 1200  # caracteres: guardia contra bloques sin estructura, no objetivo


class Veredicto(str, Enum):
    """Los tres veredictos cerrados del juez de cosecha (libro 2, cap. 16).

    Cerrados a propósito: sin "en parte quizá". El juez que matiza
    no es una fuente, es un clima.
    """

    RESPONDE = "RESPONDE"
    PARCIAL = "PARCIAL"
    NO_RESPONDE = "NO_RESPONDE"


@dataclass(frozen=True)
class DocumentoEntrante:
    """Un documento que aspira a entrar en el corpus.

    Lo que no está en el manifiesto, no llega a ser píldora.
    """

    ruta: str
    contenido: str
    dominio: str
    vigencia: str | None = None

    @property
    def huella(self) -> str:
        # La huella del contenido, no de la fecha de captura:
        # la ingesta idempotente del libro 1 empieza aquí.
        return hashlib.sha256(self.contenido.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class Pildora:
    """La unidad mínima del corpus: texto legible, contexto y metadatos."""

    texto: str                  # lo que leerá el modelo: título de contexto + contenido
    titulo: str                 # ruta de encabezados del documento
    fuente: str                 # documento de origen, con su versión
    orden: int                  # posición en el documento: la usa el ensamblado
    tipo: str                   # "texto" | "tabla" | "sintesis"
    dominio: str = ""
    vigencia: str | None = None

    @property
    def id(self) -> str:
        # La identidad nace del CONTENIDO, no de la posición:
        # re-ingestar un documento sin cambios no crea píldoras nuevas.
        digesto = hashlib.sha1(f"{self.fuente}|{self.texto}".encode()).hexdigest()[:16]
        return f"{digesto}-{self.orden:03d}"


@dataclass(frozen=True)
class Hit:
    """Una píldora recuperada, con su canal y su puntuación fusionada."""

    pildora: Pildora
    score: float
    canales: tuple[str, ...] = ("hibrido",)   # ("denso",), ("lexico",) o ambos


@dataclass(frozen=True)
class Consulta:
    """Lo que pregunta el usuario, ya con la audiencia que le da contrato."""

    texto: str
    audiencia: str = "por_omision"
    dominio: str | None = None


@dataclass(frozen=True)
class Respuesta:
    """El producto terminado: texto ensamblado, citas y abstención declarada."""

    texto: str
    citas: tuple[str, ...] = ()
    abstencion: bool = False
    patron: str = "directo"
    motivo_abstencion: str | None = None


@dataclass(frozen=True)
class PlantillaGeneracion:
    """Las seis piezas del contrato de generación (libro 3, cap. 13).

    La plantilla es un dato, no un string pegado en el código:
    versionada, comparable, sometida a regresión.
    """

    audiencia: str
    papel: str
    material: str
    prohibiciones: str
    citas: str
    formato: str
    abstencion: str
    version: str = "v1"


@dataclass(frozen=True)
class RegistroEmbudo:
    """Una fase del embudo, medida: cuánto entró y cuánto salió."""

    fase: str
    entraron: int
    salieron: int

    @property
    def ruido(self) -> float:
        # El ruido no es un porcentaje decorativo: es la factura
        # de cocción de lo que el filtro descartó.
        return 0.0 if self.entraron == 0 else 1 - self.salieron / self.entraron


@dataclass(frozen=True)
class DecisionEncaminamiento:
    """Lo que el router decidió, con su motivo legible."""

    patron: str                 # directo | iterativo | autocorrectivo | agentico | abstencion
    motivo: str                 # la regla que disparó: auditable en el triaje
    senales: tuple[str, ...] = ()


@dataclass(frozen=True)
class EntradaDataset:
    """Una fila del dataset áureo: consulta y verdad firmada (ids de píldora)."""

    consulta: str
    relevantes: frozenset[str]
    firmada_por: str = ""


@dataclass(frozen=True)
class Metricas:
    """Las dos métricas contractuales de la vara (libro 2, cap. 18)."""

    recall_k: float
    mrr: float
    k: int
    consultas: int


@dataclass
class EventoRespuesta:
    """Lo que el panel registra de cada respuesta servida (libro 3, cap. 16)."""

    consulta: str
    patron: str
    latencia_s: float
    coste_tokens: int
    abstencion: bool
    escalas: int = 0                  # reintentos/escalas en caliente
    acierto_router: bool | None = None
    frases_sin_respaldo: int = 0
    familia: str = "por_omision"
    fecha: str = ""                   # ISO-8601


def validar_payload(*campos_criticos: str | None) -> None:
    """Cero nulos en campos críticos: la regla del paso 2 de la brújula del libro 2.

    Un metadato nulo no es un vacío: es un filtro que fallará en silencio.
    """
    nulos = [nombre for nombre, valor in zip(
        ("fuente", "dominio", "titulo"), campos_criticos) if not valor]
    if nulos:
        raise ValueError(f"payload con nulos en campos críticos: {nulos}")
