---
title: "4 · Normalización y limpieza"
---

# 4 · Normalización y limpieza

Dos circulares idénticas llegan al corpus por caminos distintos: una escrita en Word y otra pasada por OCR desde un escaneo. Al lector humano les pasa desapercibida la diferencia; al índice, no — los acentos descompuestos, las comillas curvas, los espacios dobles y las fechas en dos formatos las convierten en dos mundos que no se encuentran. El canal denso las aproxima por suerte; el léxico, que es el que acierta con los términos exactos, las trata como vocabularios distintos. La normalización es lo que hace que el corpus tenga **un** idioma en lugar de tantos como fuentes.

## La decisión

El Bronce honesto (libro 1, cap. 6): la normalización es determinista, declarada y mínima. No hay un LLM aquí — ni lo necesita. Unicode NFC, espacios colapsados, puntuación de teclado normalizada y **las fechas en ISO-8601**, porque la vigencia se compara, y no se puede comparar `03/07/2025` con `2025-07-03` sin mentir a alguno de los dos. Cada una de las cuatro reglas existe por un fallo real que produjo, y ninguna arregla por su cuenta algo que corresponde a otra fase: la ortografía del usuario es del cap. 12, la jerga del dominio del Silver, y el OCR mal hecho no se arregla — se re-escanea.

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

Cómo se lee el listado: cuatro reglas, en el orden en que conviene pensarlas. La NFC **compone** los acentos en una sola forma canónica — sin ella, "código" escrito con acento descompuesto y compuesto son dos tokens distintos para el hash, para FTS5 y para el embedding. Las comillas tipográficas se pliegan a las rectas de teclado — el FTS5 busca frases literales, y una comilla curva rompe la frase. Las fechas migran a ISO-8601 con ceros rellenos — el formato comparable. Y el colapso de espacios cierra, porque el espacio sobrante es el ruido más frecuente y más inútil del OCR.

Su prueba:

```python
def test_normalizacion_fechas_a_iso():
    assert "2025-07-03" in normalizar("el plazo vence el 3/07/2025")
    assert normalizar("  espacios   dobles ") == "espacios dobles"
```

## Lo que importa

1. **Determinista, no inteligente.** La normalización del Bronce es una función pura: mismo entrada, mismo salida, siempre. La razón no es estética — es la huella del cap. 3: si la normalización cambia entre ejecuciones (un modelo, una heurística "mejorada"), la huella del documento cambia, y la idempotencia de toda la cadena se va al suelo. La parte "inteligente" de la limpieza — qué jerga unificar, qué sinónimos — vive en el curado humano del Silver, no en una expresión regular con ínfulas.
2. **Las fechas son el metadato más caro de equivocarse.** La vigencia — segunda cláusula del contrato del libro 3 — se decide comparando fechas: el post-filtrado del acceso deja fuera lo caducado comparando la fecha de la píldora con la de hoy. Una fecha sin normalizar no es suciedad cosmética: es un filtro que fallará en silencio dejando pasar un procedimiento derogado con la serenidad de quien nunca duda.
3. **Las comillas tipográficas mueren aquí.** Parece pedantería hasta que el canal léxico busca `plazo "probatorio"` con comillas curvas y el FTS5 no encuentra la frase escrita con comillas rectas. El híbrido del cap. 11 agradece esta línea cada vez que un abogado copia una frase del PDF al buscador.
4. **Lo que esta función NO hace — y por qué importa tanto.** No corrige la ortografía del usuario (eso es la reescritura de consulta, cap. 12 — sobre la pregunta y no sobre el corpus), no resume, no "mejora" el texto, no rellena huecos del OCR. Cada mejora no determinista que se colara aquí rompería la huella idempotente de la ingesta, y con ella toda la cadena: el mismo documento dejaría huellas distintas en ingestas distintas.
5. **El límite declarado: la regex valida formato, no calendario.** `31/02/2025` pasa la normalización — la fecha existe como texto aunque no exista en el calendario. Validar el calendario exigiría una política sobre fechas imposibles (¿se descarta el documento? ¿se marca?) y es decisión del curado Silver, no de una función determinista de Bronce. La serie prefiere el límite declarado a la política implícita.

## Los números

La normalización corre sobre **todo** el corpus en cada ingesta — por eso es O(n) del texto y nada más: sin modelo, sin red, sin llamadas. En el despacho, reprocesar el corpus entero cuesta segundos; si algún día deja de serlo, el problema serán las fuentes, no esta función. La regla presupuestaria que la acompaña: **lo determinista se puede reejecutar siempre; lo inteligente, solo cuando haga falta** — por eso la inteligencia vive en el curado (que se paga una vez por documento) y no aquí (que se paga en cada ingesta).

## Enlaces

- Repo: `cocinando/aplicacion/aprovisionamiento.py` · `pruebas/test_aprovisionamiento.py`
- Web: fases [Normalización](https://ragcooking.info/biblioteca/) y [Limpieza](https://ragcooking.info/biblioteca/)
- Libro 1, cap. 6: normalización y OCR · Libro 3, cap. 3: la cláusula de frescura que depende de estas fechas · Cap. 12 de este libro: la normalización del otro lado — la de la pregunta
