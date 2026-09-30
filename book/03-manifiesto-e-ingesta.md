---
title: "3 · El manifiesto y la ingesta"
---

# 3 · El manifiesto y la ingesta

La tarde que alguien pretendió ingerir un lote de PDFs "solo de prueba" que duplicaba convenios con versiones distintas — el mismo convenio, dos vigencias, los dos vivos —, el corpus aprendió su primera regla de gobierno: nada entra sin declaración. No por burocracia. Porque un documento que entra sin línea en el inventario no tiene dueño, no tiene vigencia conocida y no se le puede preguntar "¿quién te metió aquí?" cuando su respuesta equivocada aparezca en producción. Esta pieza es esa regla hecha código: un JSON que dice qué existe, y una función que se niega a existir fuera de él.

## La decisión

Lo que no está en el manifiesto no se ingiere, no se valida, no se mantiene — es, a efectos del sistema, exactamente nada (libro 1, caps. 5 y 22). La decisión tiene dos mitades y el módulo las ejecuta por separado. Primera: **la puerta con lista** — el manifiesto declara cada fuente con su dominio y su vigencia, y `ingesta` devuelve `None` para lo no declarado en lugar de lanzar un error, porque el intruso descartado no es un fallo del sistema: es el sistema funcionando. Segunda: **la huella del contenido** — `DocumentoEntrante.huella` es el SHA-256 del texto, y con ella la ingesta es idempotente desde el primer eslabón: la misma fuente capturada dos veces deja la misma huella, y el pipeline puede distinguir "documento nuevo" de "documento ya cocinado" sin fechas ni estados.

Sin el manifiesto, el corpus crece por disponibilidad — lo que alguien deja en la carpeta — en lugar de crecer por demanda, que es lo que alimenta el roadmap del libro 2. Sin la huella, cada re-ingesta semanal duplica píldoras con ids distintos y el índice envejece engordando. Las dos mitades son pequeñas; juntas sostienen todo lo que viene después.

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

Cómo se lee el listado: primero el manifiesto — una clase de tres métodos que envuelve un JSON, y con deliberación nada más. No hay descubrimiento automático de carpetas ni convenciones mágicas de nombres: **la puerta no adivina**. Después `ingesta`, que hace exactamente cuatro cosas — normaliza la ruta, consulta el pacto, levanta el documento y valida el payload crítico — en ese orden, de la más barata a la más cara: un intruso se descarta antes de abrir el fichero.

El manifiesto que lo alimenta es tan legible como cualquier documento de la serie:

```json
{
  "convenios/convenio_2024@v3.md": {"dominio": "convenios", "vigencia": "2024-01-01"},
  "sentencias/s88_2023.md": {"dominio": "sentencias", "vigencia": null},
  "circulares/rh_2025_07.md": {"dominio": "circulares", "vigencia": "2026-03-31"}
}
```

La fuente con versión (`@v3`), el dominio que la ubica en el mapa y la vigencia — o un `null` con causa: *esta sentencia no caduca*. Su prueba, en `pruebas/test_aprovisionamiento.py` — la puerta de salida es literal: el declarado pasa, el intruso no:

```python
def test_manifiesto_no_deja_pasar_lo_no_declarado(tmp_path):
    ...
    assert ingesta(declarado, manifiesto) is not None
    assert ingesta(intruso, manifiesto) is None   # no es un error: es el manifiesto funcionando
```

## Lo que importa

1. **`None` no es un fallo: es el contrato funcionando.** `ingesta` devuelve `None` para lo no declarado y no lanza excepción por ninguna parte. El error aquí sería lo contrario — ingerir de más —, porque el documento fantasma contamina el corpus en silencio y nadie sabe desde cuándo. Si algún día el triaje necesita saber qué se descartó, el `None` se puede contar en el bucle de ingesta; lo que no se puede deshacer es la píldora del intruso ya indexada.
2. **La huella nace del contenido, no del reloj.** `DocumentoEntrante.huella` es el SHA-256 del texto: la misma fuente capturada dos veces deja la misma huella, y el pipeline aguas abajo distingue "documento nuevo" de "documento ya cocinado". Es la manutención idempotente del libro 1 en su pieza más temprana — y la razón por la que re-ingestar el corpus entero cada noche es seguro por construcción.
3. **El manifiesto declara dominio y vigencia, no solo rutas.** Los metadatos críticos entran al sistema por la puerta — el filtro de permisos y vigencia del libro 2 no puede filtrar lo que nunca le dijeron. Por eso el `validar_payload` dispara ya aquí: cero nulos en lo crítico desde el minuto cero, cuando corregir cuesta un cambio de línea y no una re-cocción del corpus.
4. **Las rutas se normalizan a barra hacia delante.** El libro corre en Windows y en Linux; el manifiesto es un JSON portable y su clave no puede depender del sistema operativo de quien ingiere. Es la clase de detalle que no enseña ningún método y rompe el primer día — por eso lo enseña este capítulo.
5. **La alternativa descartada: el descubrimiento automático.** Escanear una carpeta y ingerir lo que aparezca era más cómodo — y es exactamente cómo nacen los duplicados de vigencias distintas. La carpeta no negocia vigencias ni declara dominios; el manifiesto sí. La comodidad de la carpeta es la factura del trimestre siguiente.
6. **Cómo se rompe esto: la deriva del manifiesto.** El modo de fallo propio de esta pieza no está en el código — está en la disciplina: ficheros que existen en el disco sin línea en el manifiesto (basura que no entra, pero estorba) y líneas del manifiesto cuyo fichero desapareció (puertas hacia la nada). El hábito que lo evita es de calendario: revisar el manifiesto en el triaje, como cualquier documento vivo de la serie.

## Los números

En el despacho, el manifiesto cuenta las fuentes por **decenas, no por cientos** — si necesitas miles de líneas, no es un manifiesto: es una carpeta sin gobierno. Las líneas nacen de las preguntas (el roadmap del bucle del libro 2: la demanda real, fechada) y nunca de la disponibilidad ("tenemos estos PDFs, mételos"). El coste de la ingesta completa es O(n) del texto — segundos para el corpus entero — y la huella añade un hash por documento: imperceptible en la factura, decisivo en la idempotencia.

## Enlaces

- Repo: `cocinando/aplicacion/aprovisionamiento.py` · `pruebas/test_aprovisionamiento.py`
- Web: fases [Corpus](https://ragcooking.info/biblioteca/) e [Ingesta](https://ragcooking.info/biblioteca/)
- Libro 1, caps. 5, 20 y 22: el manifiesto, la manutención idempotente, el pipeline repetible
