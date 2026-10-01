---
title: "11 · La recuperación híbrida con RRF"
---

# 11 · La recuperación híbrida con RRF

Cada canal a solas pierde la mitad del mundo. El denso no ve la palabra exacta del convenio — "BGC-2024/17" no se parece a nada en el espacio de los vectores — y el léxico no ve la sinonimia — quien pregunta por "despido" no encontrará la píldora que dice "extinción del contrato". Por separado, dos motos medias; fundidos, un vehículo que cubre ambos mundos. El híbrido es la primera regresión que cualquier equipo debería correr — en la literatura de la serie, como en la de todos, **el híbrido gana**. Esta pieza es esa fusión, hecha código sobre los dos canales que el cap. 9 construyó en el mismo archivo.

## La decisión

El híbrido que gana (libro 2, cap. 12): el canal denso entiende sinonimia, el léxico acierta con los términos exactos, y la fusión es **RRF** — Reciprocal Rank Fusion — porque comparar el coseno del denso con el BM25 del léxico es comparar grados con kilos; RRF solo mira puestos. Dos decisiones más, ambas de gobierno: el filtro de dominio entra **antes** de fusionar — el ranking nunca discute al permiso —, y cada `Hit` declara **por qué canales salió**, porque esa información es señal, no un detalle interno.

## El código

`cocinando/infraestructura/sqlite_repo.py`, segunda mitad — la búsqueda (el esquema y `guardar` son el cap. 9, del mismo archivo):

```python
# cocinando/infraestructura/sqlite_repo.py — segunda mitad

CONSTANTE_RRF = 60   # la constante del paper de RRF: dos canales, un ranking


def buscar_hibrido(
    self,
    vector: list[float],
    lexico: str,
    k: int,
    dominio: str | None = None,
) -> list[Hit]:
    """Denso + léxico fundidos con RRF, con el dominio filtrando antes.

    Cada canal aporta su ranking; la fusión suma los recíprocos.
    Un Hit que salió por los dos canales lo declara en `canales` —
    y suele ser la mejor señal de pertinencia que existe.
    """

    candidato_x, filtro = k * 4, ""        # margen para que el filtro no vacíe el corte
    params_denso: list = [struct.pack(f"{len(vector)}f", *vector), candidato_x]
    if dominio:
        filtro = "AND p.dominio = ?"
        params_denso.append(dominio)
    denso = {
        fila[0]: fila[1]
        for fila in self.conn.execute(
            f"""SELECT p.id, v.distance
                FROM pildoras_vec v JOIN pildoras p ON p.rowid = v.rowid
                WHERE v.embedding MATCH ? AND k = ? {filtro}
                ORDER BY v.distance""",
            params_denso,
        )
    }

    lexico_consulta = " ".join(f'"{t}"' for t in lexico.split() if t)
    filtro_lex = "AND id IN (SELECT id FROM pildoras WHERE dominio = ?)" if dominio else ""
    params_lexico: list = [lexico_consulta] + ([dominio] if dominio else []) + [candidato_x]
    lexico_ranking = {
        fila[0]: fila[1]
        for fila in self.conn.execute(
            f"""SELECT id, bm25(pildoras_fts) AS score
                FROM pildoras_fts WHERE pildoras_fts MATCH ? {filtro_lex}
                ORDER BY score LIMIT ?""",
            params_lexico,
        )
    }

    return self._fundir(denso, lexico_ranking, k, dominio)


def _fundir(self, denso: dict[str, float], lexico: dict[str, float],
            k: int, dominio: str | None) -> list[Hit]:
    """Reciprocal Rank Fusion: simple, robusta y sin puntuaciones mezcladas."""
    puntuaciones: dict[str, float] = {}
    canales: dict[str, set[str]] = {}
    for nombre, ranking in (("denso", denso), ("lexico", lexico)):
        for puesto, pid in enumerate(sorted(ranking, key=ranking.get, reverse=True)):
            puntuaciones[pid] = puntuaciones.get(pid, 0.0) + 1.0 / (CONSTANTE_RRF + puesto + 1)
            canales.setdefault(pid, set()).add(nombre)

    filas = self.conn.execute(
        f"SELECT * FROM pildoras WHERE id IN ({','.join('?' * len(puntuaciones))})",
        list(puntuaciones),
    ).fetchall()
    por_id = {
        fila[0]: Pildora(texto=fila[1], titulo=fila[2], fuente=fila[3],
                         orden=fila[4], tipo=fila[5], dominio=fila[6], vigencia=fila[7])
        for fila in filas
    }
    ordenados = sorted(puntuaciones, key=puntuaciones.get, reverse=True)[:k]
    return [
        Hit(pildora=por_id[pid], score=round(puntuaciones[pid], 6),
            canales=tuple(sorted(canales[pid])))
        for pid in ordenados if pid in por_id
    ]
```

Cómo leerlo: dos consultas paralelas — cada canal trae su propio ranking con `candidato_x = k * 4` puestos — y una fusión que solo mira posiciones: el primer puesto de cada canal aporta `1/61`, el segundo `1/62`, y así. Quien sale bien en los dos canales suma dos veces; quien solo sale en uno, compite con lo que aportó. Al final, las píldoras completas se traen del índice en una única consulta y se devuelven ordenadas hasta `k`.

## Lo que importa

1. **El filtro de dominio entra en cada canal, antes de la fusión.** El permiso no es un post-filtro elegante: es una condición de existencia (libro 2, cap. 9). Si filtrara después, una píldora ajena habría ocupado un puesto del top-k y desplazado a una legítima — la cuenta que el usuario nunca ve pero paga en respuestas que no debían salir. La prueba `test_dominio_filtra_antes_de_fusionar` lo verifica con un dominio vacío: el ranking entero no puede contra el filtro.
2. **`candidato_x = k * 4`: el margen del corte.** Cada canal trae cuatro veces lo pedido para que el filtro y la fusión tengan de dónde elegir. Pedir exactamente k por canal es servirse el ranking sin margen — y la RRF premia a quien sale en los dos canales, que solo ocurre si los cortes se solapan. Cuatro es un margen de arranque: si el dominio filtra mucho, cinco o seis; el límite lo pone la vara, no el entusiasmo.
3. **El léxico va entre comillas por token.** La consulta se trocea en frases exactas (`"plazo" "reclamación"`): evita que el FTS5 interprete como sintaxis lo que el usuario escribió como texto — la misma razón por la que el cap. 4 mató las comillas tipográficas. Es la lección de siempre del oficio: **la interfaz normaliza lo que recibe antes de confiárselo a la máquina**.
4. **Los Hit declaran sus canales.** Un resultado que salió por denso y léxico a la vez (`canales=("denso", "lexico")`) suele ser la señal de pertinencia más barata que existe: dos mundos distintos lo apuntaron. El panel del cap. 18 puede leer esa proporción; un rerank futuro puede usarla como rasgo. El canal por el que salió una píldora es información, no un detalle interno.
5. **La constante 60 no se toca sin vara.** Es la del paper de RRF y funciona porque solo compara puestos — es inmune a las escalas distintas de los dos canales, que era la razón de existir. Si alguien quiere afinar la fusión, el camino es la vara del cap. 15 con un dataset — nunca ajustar a ojo el número que ordena las respuestas de todo el sistema.
6. **Lo que la RRF no hace — y quién lo hace.** La RRF no entiende de matices: no sabe que un puesto en el denso vale más que otro en el léxico para esta consulta. Esa sofisticación es del **rerank** — el tamiz de la siguiente pieza, que reordena la cosecha ya fusionada con un modelo más fino. La arquitectura del libro 2 en tres actos — recuperar híbrido, reordenar fino, juzgar — empieza aquí.

## Los números

Sobre decenas de miles de píldoras en el archivo SQLite, la búsqueda híbrida completa responde en **milisegundos**: dos consultas indexadas y una fusión en memoria de 8k puestos. En la vara del cap. 15, el híbrido contra el denso solo es la primera regresión que cualquier equipo debería correr — en la literatura de la serie, como en la de todos, el híbrido gana; y el tamaño exacto de la ganancia en tu corpus, solo lo dice tu dataset. El `k` por omisión es **10**: el tope del cap. 13 del libro 2 como política, no como número copiado — tu tope lo firma tu presupuesto de contexto y tu ensamblado.

## Enlaces

- Repo: `cocinando/infraestructura/sqlite_repo.py` · `pruebas/test_repositorio.py`
- Web: fase [Recuperación](https://ragcooking.info/biblioteca/recuperacion/)
- Libro 2, caps. 11-13: vectorial, híbrido con fusión declarada, el tope · Libro 3, cap. 12: el router que decide quién llega hasta aquí
