"""Aprovisionamiento: manifiesto, ingesta idempotente y normalización (caps. 3-4).

La regla que gobierna todo el módulo es la del manifiesto:
lo que no está en él, no existe — a efectos del sistema, exactamente nada.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from cocinando.dominio.modelos import DocumentoEntrante, validar_payload

FECHA = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")


class Manifiesto:
    """El pacto sobre lo que entra en el corpus (libro 1, cap. 5).

    Un JSON versionado: cada fuente declarada con su dominio y su vigencia.
    Si el documento no tiene línea aquí, no se ingiere, no se valida,
    no se mantiene — es, a efectos del sistema, exactamente nada.
    """

    def __init__(self, fichero: Path) -> None:
        self.fuentes: dict[str, dict] = json.loads(fichero.read_text("utf-8"))

    def contiene(self, ruta: str) -> bool:
        return ruta in self.fuentes

    def de(self, ruta: str) -> dict:
        return self.fuentes[ruta]


def ingesta(ruta: Path, manifiesto: Manifiesto) -> DocumentoEntrante | None:
    """Toma un documento del disco solo si el manifiesto lo declara.

    Devuelve None para lo no declarado — y None no es un error:
    es el manifiesto funcionando. La huella del contenido es la que
    hace idempotente la ingesta aguas abajo.
    """
    ruta_texto = str(ruta).replace("\\", "/")
    if not manifiesto.contiene(ruta_texto):
        return None
    declarada = manifiesto.de(ruta_texto)
    entrada = DocumentoEntrante(
        ruta=ruta_texto,
        contenido=ruta.read_text("utf-8"),
        dominio=declarada["dominio"],
        vigencia=declarada.get("vigencia"),
    )
    validar_payload(entrada.ruta, entrada.dominio, entrada.ruta)
    return entrada


def normalizar(texto: str) -> str:
    """El Bronce honesto (libro 1, cap. 6): determinista, reversible en espíritu.

    Unicode NFC, espacios colapsados, puntuación de teclado normalizada
    y las fechas en ISO-8601 — porque la vigencia se compara, y no se puede
    comparar "03/07/2025" con "2025-07-03" sin mentir a alguno de los dos.
    """
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.replace("\u201c", '"').replace("\u201d", '"')
    texto = texto.replace("\u2018", "'").replace("\u2019", "'")
    texto = FECHA.sub(lambda m: f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}", texto)
    return re.sub(r"[ \t]+", " ", texto).strip()
