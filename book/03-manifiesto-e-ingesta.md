---
title: "3 · El manifiesto y la ingesta"
---

# 3 · El manifiesto y la ingesta

## La decisión

Lo que no está en el manifiesto no se ingiere, no se valida, no se mantiene — es, a efectos del sistema, exactamente nada (libro 1, caps. 5 y 22). Y la ingesta que sigue es idempotente: la huella del contenido decide, no la fecha de captura. Las dos reglas caben en un módulo pequeño, y que el módulo sea pequeño es la prueba de que no hacían falta más.

## El código

`cocinando/aplicacion/aprovisionamiento.py` — la primera mitad del módulo (la segunda, la normalización, es el capítulo siguiente):

```python
# cocinando/aplicacion/aprovisionamiento.py
# Aprovisionamiento: manifiesto, ingesta idempotente y normalización (caps. 3-4).

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
```

Su prueba, en `pruebas/test_aprovisionamiento.py` — la puerta de salida es literal: el declarado pasa, el intruso no:

```python
def test_manifiesto_no_deja_pasar_lo_no_declarado(tmp_path):
    ...
    assert ingesta(declarado, manifiesto) is not None
    assert ingesta(intruso, manifiesto) is None   # no es un error: es el manifiesto funcionando
```

## Lo que importa

1. **`None` no es un fallo: es el contrato funcionando.** `ingesta` devuelve `None` para lo no declarado y no lanza excepción por ninguna parte. El error aquí sería lo contrario — ingerir de más —, porque el documento fantasma contamina el corpus en silencio y nadie sabe desde cuándo.
2. **La huella nace del contenido, no del reloj.** `DocumentoEntrante.huella` es el SHA-256 del texto: la misma fuente capturada dos veces deja la misma huella, y el pipeline aguas abajo distingue "documento nuevo" de "documento ya cocinado". Es la manutención idempotente del libro 1 en su pieza más temprana.
3. **El manifiesto declara dominio y vigencia, no solo rutas.** Los metadatos críticos entran al sistema por la puerta — el filtro de permisos y vigencia del libro 2 no puede filtrar lo que nunca le dijeron. Por eso el `validar_payload` dispara ya aquí: cero nulos en lo crítico desde el minuto cero.
4. **Las rutas se normalizan a barra hacia delante.** El libro corre en Windows y en Linux; el manifiesto es un JSON portable y su clave no puede depender del sistema operativo de quien ingiere.

## Los números

En el despacho, el manifiesto cuenta las fuentes por **decenas, no por cientos** — si necesitas miles de líneas, no es un manifiesto: es una carpeta sin gobierno. Cada línea lleva su dominio y su vigencia, o un `null` con causa — que es distinto de un `null` con pereza.

## Enlaces

- Repo: `cocinando/aplicacion/aprovisionamiento.py` · `pruebas/test_aprovisionamiento.py`
- Web: fases [Corpus](https://ragcooking.info/biblioteca/) e [Ingesta](https://ragcooking.info/biblioteca/)
- Libro 1, caps. 5, 20 y 22: el manifiesto, la manutención idempotente, el pipeline repetible
