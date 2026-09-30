---
title: "6 · El payload que filtra: metaetiquetado"
---

# 6 · El payload que filtra: metaetiquetado

## La decisión

El esquema de metadatos es el mapa que el acceso recorre (libro 2, caps. 4-6): versionado, con **cero nulos en los campos críticos** — porque un metadato nulo no es un vacío, es un filtro que fallará en silencio. En esta implementación, el payload no es un diccionario suelto: son los campos de la píldora, validados en la puerta y en el índice.

## El código

La pieza central de `cocinando/dominio/modelos.py` — el payload son los campos de la píldora, y el validador es la regla del paso 2 de la brújula del libro 2 hecha función:

```python
# cocinando/dominio/modelos.py — extracto

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


def validar_payload(*campos_criticos: str | None) -> None:
    """Cero nulos en campos críticos: la regla del paso 2 de la brújula del libro 2.

    Un metadato nulo no es un vacío: es un filtro que fallará en silencio.
    """
    nulos = [nombre for nombre, valor in zip(
        ("fuente", "dominio", "titulo"), campos_criticos) if not valor]
    if nulos:
        raise ValueError(f"payload con nulos en campos críticos: {nulos}")
```

Y así viaja al índice — el `CREATE TABLE` del cap. 9 repite estos campos uno a uno, porque **el esquema del índice es el mismo contrato, escrito en SQL**:

```sql
CREATE TABLE IF NOT EXISTS pildoras (
    id        TEXT PRIMARY KEY,
    texto     TEXT NOT NULL,
    titulo    TEXT NOT NULL,
    fuente    TEXT NOT NULL,
    orden     INTEGER NOT NULL,
    tipo      TEXT NOT NULL,
    dominio   TEXT NOT NULL,
    vigencia  TEXT
);
```

## Lo que importa

1. **Los campos críticos son tres: fuente, dominio, título.** Fuente porque sin trazabilidad la respuesta no es comprobable; dominio porque sin frontera el filtro no filtra; título porque el contexto que viaja con el trozo (cap. 5) es el que evita la extrapolación. Todo lo demás admite nulo con causa.
2. **`vigencia` puede ser nulo — con causa.** No todo documento caduca. El nulo aquí es una declaración ("este material no caduca"), no una omisión; por eso está fuera del validador y dentro del esquema.
3. **El dataclass es frozen.** Una píldora que se puede mutar a mitad de pipeline es una píldora que miente sobre su huella: el id garantiza el contenido solo si el contenido no cambia. La inmutabilidad aquí no es purismo — es la idempotencia sostenida en el tiempo.
4. **El esquema SQL repite el dataclass a propósito.** Podría generarse automáticamente; está escrito a mano para que cualquier divergencia entre dominio e índice se vea en el diff — el mismo instinto que puso el manifiesto en un JSON legible.

## Los números

En la web, la fase de metaetiquetado es la más poblada del recetario: **10 piezas** — y no es casualidad, es el mapa. En el despacho, el esquema real lleva los mismos tres críticos y una media docena de descriptivos (tipo, fuente de publicación, fecha, etiquetas de faceta). Quien necesite cuarenta campos que revise si de verdad filtra con todos — el payload que nadie consulta es pasivo, no activo.

## Enlaces

- Repo: `cocinando/dominio/modelos.py` · `cocinando/infraestructura/sqlite_repo.py` (el mismo contrato en SQL)
- Web: fase [Metaetiquetado](https://ragcooking.info/biblioteca/) — la más poblada del recetario
- Libro 2, caps. 4-6: metadatos, dominios y coordenadas · Libro 1, cap. 9: la clasificación facetada de origen
