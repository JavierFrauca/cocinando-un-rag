---
title: "6 · El payload que filtra: metaetiquetado"
---

# 6 · El payload que filtra: metaetiquetado

El filtro de vigencia que no filtró — una circular derogada citada en una respuesta meses después de su muerte — no falló por el filtro: falló porque el campo llegó vacío. Un metadato nulo no es un vacío inocente; es un filtro que fallará en silencio el día que se le necesite, y el silencio es exactamente el modo de fallo que esta serie no perdona. La fase de metaetiquetado es la más poblada del recetario de la web — **10 piezas de 75** — y no es casualidad: el mapa que aquí se dibuja es el que el acceso recorre entero (libro 2, caps. 4-6). Esta pieza es ese mapa hecho esquema: los campos de la píldora, validados en la puerta y repetidos en el índice.

## La decisión

El esquema de metadatos es el territorio (libro 2, cap. 4): versionado, con **cero nulos en los campos críticos**. En esta implementación, el payload no es un diccionario suelto que crece por parches: son los campos de la `Pildora`, inmutables, validados en la puerta por `validar_payload` y escritos en el índice con la misma forma — porque el esquema del índice es el mismo contrato, escrito en SQL. La decisión de fondo: **los metadatos se declaran una vez y se respetan en todas las capas**, en lugar de ser un campo de más aquí y un campo olvidado allá.

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

Fíjese el lector en lo que el SQL dice con sus `NOT NULL` y su único campo que puede ser nulo: **el esquema repite la política del validador**. Fuente, dominio y título no pueden faltar ni en Python ni en SQLite; la vigencia puede — con causa.

## Lo que importa

1. **Los campos críticos son tres: fuente, dominio, título.** Fuente porque sin trazabilidad la respuesta no es comprobable — la cita de la serie remite a la píldora y la píldora a su documento. Dominio porque sin frontera el filtro no filtra: el RBAC/ABAC de la web y el pre-filtrado del libro 2 viven de este campo. Título porque el contexto que viaja con el trozo (cap. 5) es lo que evita la extrapolación. Todo lo demás admite nulo con causa.
2. **`vigencia` puede ser nulo — con causa.** No todo documento caduca: una sentencia firme no tiene fecha de muerte. El nulo aquí es una declaración ("este material no caduca"), no una omisión; por eso está fuera del validador y dentro del esquema. La diferencia entre ambos nulos es exactamente la diferencia entre el gobierno y el abandono.
3. **El dataclass es `frozen`.** Una píldora que se puede mutar a mitad de pipeline es una píldora que miente sobre su huella: el id garantiza el contenido solo si el contenido no cambia. La inmutabilidad aquí no es purismo — es la idempotencia sostenida en el tiempo: si el código de algún paso "mejorara" el texto a mitad de camino, el id dejaría de responder por lo que el índice contiene.
4. **El esquema SQL repite el dataclass a propósito.** Podría generarse automáticamente desde el dataclass; está escrito a mano para que cualquier divergencia entre dominio e índice aparezca en el diff de un commit — el mismo instinto que puso el manifiesto en un JSON legible y no en una base de datos de gobierno. En una serie que versiona documentos en Git, el esquema del índice también es un documento.
5. **Cómo se rompe esto: la evolución del esquema.** Añadir un campo descriptivo es aditivo y barato; renombrar uno crítico es una migración — el índice se recocina y la regresión del cap. 16 decide si el nuevo mapa filtra igual de bien. El error clásico es añadir el campo en el dataclass y olvidarlo en el SQL (o al revés): el diff manual no lo evita, lo hace visible el mismo día.
6. **Para qué sirve cada campo, dicho sin rodeos.** `dominio` filtra en el pre-filtrado y agrupa en el triaje; `vigencia` compara en el post-filtrado; `tipo` decide el tratamiento en el ensamblado (una tabla no se resume igual que una prosa); `fuente` sostiene la cita; `titulo` viaja dentro del texto; `orden` reconstruye el hilo. **Un campo que no responde a ninguna de estas preguntas es pasivo** — y el pasivo del payload se paga en mantenimiento.

## Los números

En la web, la fase de metaetiquetado es la más poblada del recetario: **10 piezas de 75** — el mapa manda. En el despacho, el esquema real lleva los mismos tres críticos y una media docena de descriptivos (tipo de documento, fecha de publicación, origen, etiquetas de faceta). Quien necesite cuarenta campos que revise cuáles filtran de verdad — la regla del libro 2: las facetas que no se consultan no son mapas, son equipaje. Y el número de diagnóstico que conviene mirar cada mes: **píldoras con vigencia nula** — si crece sin causa, el gobierno de vigencias se está relajando.

## Enlaces

- Repo: `cocinando/dominio/modelos.py` · `cocinando/infraestructura/sqlite_repo.py` (el mismo contrato en SQL)
- Web: fase [Metaetiquetado](https://ragcooking.info/biblioteca/) — la más poblada del recetario
- Libro 2, caps. 4-6: metadatos, dominios y coordenadas · Libro 1, cap. 9: la clasificación facetada de origen
