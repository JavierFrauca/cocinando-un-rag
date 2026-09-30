---
title: "16 · La regresión en CI"
---

# 16 · La regresión en CI

Los sistemas que despliegan y miran después descubren sus regresiones en las quejas; los que examinan antes las descubren en la suite, donde cuestan un fallo verde en un panel y no una confianza de usuarios. La lección es del libro 2 (cap. 19) y este capítulo la instala en el lugar donde ya vive en toda disciplina seria: **la integración continua**. Dos puertas en cada cambio — el libro compila en estricto, el código pasa sus pruebas — y entre ellas, la comparación que decide: *cero diferencias sin explicación, no cero diferencias*.

## La decisión

La regresión admite el ruido estadístico y bloquea la caída, con la explicación escrita dentro del veredicto. La decisión de diseño: la tolerancia **vive en el código y está declarada** (`TOLERANCIA = 0.02`), porque una puerta sin margen aprende a ignorarse — cada re-cocción del índice bloquearía por una variación de la tercera decimal, y el equipo haría lo que hacen los equipos con las alarmas ruidosas: desactivarla. Con tolerancia, la caída real no cabe en el ruido: **lo que bloquea, duele; lo que duele, se mira**.

## El código

`cocinando/aplicacion/evaluar.py`, segunda mitad:

```python
# cocinando/aplicacion/evaluar.py — la segunda mitad

TOLERANCIA = 0.02  # el ruido estadístico admisible; más que esto, es una regresión


@dataclass(frozen=True)
class VeredictoRegresion:
    """El examen antes del despliegue: aprueba o bloquea, con su explicación."""

    aprueba: bool
    explicacion: str


def comparar_regresion(antes: Metricas, despues: Metricas) -> VeredictoRegresion:
    """Cero diferencias sin explicación, no cero diferencias.

    La regresión bloquea si el recall cae por debajo de la tolerancia.
    Las mejoras pasan; las caídas, no — y el número lo dice, no la intuición.
    """
    caida = antes.recall_k - despues.recall_k
    if caida > TOLERANCIA:
        return VeredictoRegresion(
            aprueba=False,
            explicacion=(
                f"regresión: recall {antes.recall_k:.3f} → {despues.recall_k:.3f} "
                f"(−{caida:.3f} > tolerancia {TOLERANCIA})"
            ),
        )
    return VeredictoRegresion(
        aprueba=True,
        explicacion=f"recall {antes.recall_k:.3f} → {despues.recall_k:.3f}: dentro de tolerancia",
    )
```

Y la puerta entera de la casa, `.github/workflows/ci.yml` — el Action que compila el libro y prueba el código en cada cambio:

```yaml
# .github/workflows/ci.yml — que el libro y el código "vivan bien", verificado
name: ci
on:
  push:
    branches: [main]
  pull_request:

jobs:
  libro:                          # el libro compila
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: mkdocs build --strict
  codigo:                         # el código pasa sus puertas de salida
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pytest sqlite-vec
      - run: pytest -q
```

Su prueba — los tres futuros posibles de cualquier cambio, en tres asserts:

```python
def test_la_regresion_bloquea_la_caida_y_pasa_la_mejora():
    antes = Metricas(recall_k=0.90, mrr=0.8, k=10, consultas=30)
    caida = Metricas(recall_k=0.80, mrr=0.7, k=10, consultas=30)
    estable = Metricas(recall_k=0.89, mrr=0.8, k=10, consultas=30)
    mejora = Metricas(recall_k=0.94, mrr=0.9, k=10, consultas=30)

    assert not comparar_regresion(antes, caida).aprueba       # la caída bloquea
    assert comparar_regresion(antes, estable).aprueba         # el ruido estadístico pasa
    assert comparar_regresion(antes, mejora).aprueba          # la mejora pasa
```

## Lo que importa

1. **La tolerancia está declarada y vale 0,02.** Sin tolerancia, cada re-cocción del índice bloquearía por una variación de la tercera decimal — y el equipo aprendería a ignorar la puerta. Con ella, la caída real no cabe en el ruido: lo que bloquea, duele. Y el número no es sagrado: con un dataset mayor y más estable, baja; con uno joven, sube — lo que no es negociable es que esté declarado y que la caída se mida contra él.
2. **El veredicto lleva su explicación dentro.** `explicacion` no es un log aparte: es parte del dato que la CI imprime. El "sin explicación" del libro 2 resuelto por construcción — nadie aprueba una regresión sin leer por qué bloqueó, porque la explicación es el primer campo del veredicto y la última palabra del log rojo.
3. **Dos trabajos en el Action: el libro y el código.** El libro compila con `--strict` — un enlace roto, un título duplicado o un error de markdown no se publican: el libro es también un artefacto con su puerta. El código corre sus 21 pruebas con sqlite-vec y sin claves — los falsos de las pruebas hacen que "saber que vive bien" cueste segundos de CI y cero facturas de API. La casa entera se verifica en cada push, no en las demos.
4. **La puerta es la misma para todos los cambios.** Cambiar la plantilla (cap. 14), el embedding (cap. 8), el `k` del tope (cap. 11) o la fusión del híbrido (cap. 11) pasa por `correr_vara` + `comparar_regresion` con números del dataset — el cap. 8 prometió que el cambio de embeddings sería "un despliegue con regresión", y esta es esa regresión. La igualdad de la puerta es lo que la hace creíble: si los cambios "pequeños" se saltan el examen, la vara mide solo lo que ya iba a ir bien.
5. **Qué ocurre cuando bloquea.** El despliegue no sale; la hipótesis se reescribe. La secuencia del libro 3 para la plantilla sirve entera: hipótesis escrita, examen ejecutado, inventario de cambios clasificado — mejoras, explicados, regresiones — y las regresiones bloquean. El cambio que bloquea dos veces seguidas no es mala suerte: es una señal de que la hipótesis era otra cosa.

## Los números

La tolerancia del repo es **0,02 de recall** — el ruido que un pequeño cambio de puntuaciones produce sin que nadie toque nada significativo. El dataset del cap. 15 (decenas de entradas) es lo bastante estable para que 0,02 distinga ruido de regresión; con un dataset mayor, la tolerancia puede bajar. El examen completo corre en la CI en **menos de diez segundos** — libro y código — porque las pruebas no pagan ni modelos ni red: el examen barato es el que se ejecuta siempre, y el que se ejecuta siempre es el que salva el trimestre.

## Enlaces

- Repo: `cocinando/aplicacion/evaluar.py` · `pruebas/test_evaluar.py` · `.github/workflows/ci.yml`
- Web: fase [Gobierno](https://ragcooking.info/biblioteca/)
- Libro 2, cap. 19: la regresión del acceso · Libro 3, cap. 15: la regresión de respuesta que esta misma puerta aplica a la capa final
