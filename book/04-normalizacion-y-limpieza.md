---
title: "4 · Normalización y limpieza"
---

# 4 · Normalización y limpieza

## La decisión

El Bronce honesto (libro 1, cap. 6): la normalización es determinista, declarada y mínima. No hay un LLM aquí — ni lo necesita. Unicode NFC, espacios colapsados, puntuación de teclado normalizada y **las fechas en ISO-8601**, porque la vigencia se compara, y no se puede comparar `03/07/2025` con `2025-07-03` sin mentir a alguno de los dos.

## El código

La segunda mitad de `cocinando/aplicacion/aprovisionamiento.py`:

```python
FECHA = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")


def normalizar(texto: str) -> str:
    """El Bronce honesto (libro 1, cap. 6): determinista, declarada y mínima.

    Unicode NFC, espacios colapsados, puntuación de teclado normalizada
    y las fechas en ISO-8601 — porque la vigencia se compara, y no se puede
    comparar "03/07/2025" con "2025-07-03" sin mentir a alguno de los dos.
    """
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.replace("\u201c", '"').replace("\u201d", '"')
    texto = texto.replace("\u2018", "'").replace("\u2019", "'")
    texto = FECHA.sub(lambda m: f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}", texto)
    return re.sub(r"[ \t]+", " ", texto).strip()
```

Y su prueba:

```python
def test_normalizacion_fechas_a_iso():
    assert "2025-07-03" in normalizar("el plazo vence el 3/07/2025")
    assert normalizar("  espacios   dobles ") == "espacios dobles"
```

## Lo que importa

1. **Determinista, no inteligente.** La normalización del Bronce es una función pura: mismo entrada, mismo salida, siempre. La parte "inteligente" de la limpieza — qué jerga unificar, qué sinónimos — vive en el curado humano del Silver, no en una expresión regular con ínfulas.
2. **Las fechas son el metadato más caro de equivocarse.** La vigencia — segunda cláusula del contrato del libro 3 — se decide comparando fechas. Una fecha sin normalizar no es suciedad cosmética: es un filtro que fallará en silencio dejando pasar un procedimiento derogado.
3. **Las comillas tipográficas mueren aquí.** Parece pedantería hasta que el canal léxico busca `plazo "probatorio"` con comillas curvas y el FTS5 no encuentra la frase escrita con comillas rectas. El híbrido del cap. 11 agradece esta línea.
4. **Lo que esta función NO hace.** No corrige la ortografía del usuario (eso es la reescritura de consulta, cap. 12 — sobre la pregunta y no sobre el corpus), no resume, no "mejora" el texto. Cada mejora no determinista que se colara aquí rompería la huella idempotente de la ingesta, y con ella toda la cadena.

## Los números

La normalización corre sobre **todo** el corpus en cada ingesta — por eso es O(n) del texto y nada más. En el despacho, reprocesar el corpus entero cuesta segundos; si algún día deja de serlo, el problema serán las fuentes, no esta función.

## Enlaces

- Repo: `cocinando/aplicacion/aprovisionamiento.py` · `pruebas/test_aprovisionamiento.py`
- Web: fases [Normalización](https://ragcooking.info/biblioteca/) y [Limpieza](https://ragcooking.info/biblioteca/)
- Libro 1, cap. 6: normalización y OCR · Libro 3, cap. 3: la cláusula de frescura que depende de estas fechas
