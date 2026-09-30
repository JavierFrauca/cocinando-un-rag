---
title: "11 · La recuperación híbrida con RRF"
---

# 11 · La recuperación híbrida con RRF

## La decisión

El híbrido que gana (libro 2, cap. 12): el canal denso entiende sinonimia, el léxico acierta con los términos exactos, y ninguno basta solo. La fusión es **RRF** — Reciprocal Rank Fusion — porque comparar el coseno del denso con el BM25 del léxico es comparar grados con kilos; RRF solo mira puestos. Y el filtro de dominio entra **antes** de fusionar: el ranking nunca discute al permiso.

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
    import struct

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

## Lo que importa

1. **El filtro de dominio entra en cada canal, antes de la fusión.** El permiso no es un post-filtro elegante: es una condición de existencia (libro 2, cap. 9). Si filtrara después, una píldora ajena habría ocupado un puesto del top-k y desplazado a una legítima — la cuenta que el usuario nunca ve.
2. **`candidato_x = k * 4`: el margen del corte.** Cada canal trae cuatro veces lo pedido para que el filtro y la fusión tengan de dónde elegir. Pedir exactamente k por canal es servirse el ranking sin margen — y la RRF premia a quien sale en los dos canales, que solo ocurre si los cortes se solapan.
3. **El léxico va entre comillas por token.** La consulta se trocea en frases exactas (`"plazo" "reclamación"`): evita que el FTS5 interprete como sintaxis lo que el usuario escribió como texto — la misma razón por la que el cap. 4 mató las comillas tipográficas.
4. **Los Hit declaran sus canales.** Un resultado que salió por denso y léxico a la vez (`canales=("denso", "lexico")`) suele ser la señal de pertinencia más barata que existe — y el panel del cap. 18 la podrá usar. El canal por el que salió una píldora es información, no un detalle interno.
5. **La constante 60 no se toca sin vara.** Es la del paper de RRF y funciona porque solo compara puestos. Si alguien quiere afinar la fusión, el camino es la vara del cap. 15 con un dataset — nunca ajustar a ojo el número que ordena las respuestas.

## Los números

Sobre decenas de miles de píldoras en el archivo SQLite, la búsqueda híbrida completa responde en **milisegundos**: dos consultas indexadas y una fusión en memoria. En la vara del cap. 15, el híbrido contra el denso solo es la primera regresión que cualquier equipo debería correr — en la literatura de la serie, como en la de todos, el híbrido gana.

## Enlaces

- Repo: `cocinando/infraestructura/sqlite_repo.py` · `pruebas/test_repositorio.py`
- Web: fase [Recuperación](https://ragcooking.info/biblioteca/recuperacion/)
- Libro 2, caps. 11-13: vectorial, híbrido con fusión declarada, el tope · Libro 3, cap. 12: el router que decide quién llega hasta aquí
