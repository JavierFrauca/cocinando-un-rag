"""La sincronía libro ↔ paquete: lo que el libro lista es el código que corre.

La CI tiene dos puertas — ``mkdocs build --strict`` compila el libro y
``pytest`` pasa el paquete — pero ninguna comprueba que los listados del
libro sean el código real. Este test sí: cada bloque ```python``` o
```yaml``` de book/ que declara su fichero en la primera línea se compara
contra ese fichero del repositorio, símbolo a símbolo.

La comparación es de estructura (ast), no de caracteres: el libro
sustituye docstrings por comentarios, elide líneas con ``...`` y ajusta
el formato — todo eso es legítimo. Lo que no lo es: otra lógica, otra
firma, otro número.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LIBRO = RAIZ / "book"

BLOQUE = re.compile(r"```(python|yaml)\n(.*?)```", re.DOTALL)
CABECERA = re.compile(r"^#\s+([\w./\-]+?\.(?:py|yml|yaml))(?:\s.*)?$")
CITA = re.compile(r"((?:cocinando|pruebas)/[\w/\-]+\.py)")


def bloques_declarados():
    """Los (capítulo, fichero, lenguaje, código) cuyo listado declara su ruta."""
    for md in sorted(LIBRO.glob("*.md")):
        for lenguaje, cuerpo in BLOQUE.findall(md.read_text(encoding="utf-8")):
            primera = next((linea for linea in cuerpo.splitlines() if linea.strip()), "")
            cabecera = CABECERA.match(primera.strip())
            if cabecera:
                yield md.name, RAIZ / cabecera.group(1), lenguaje, cuerpo


# --------------------------------------------------------------- normalización

def _sin_docstrings(arbol: ast.AST) -> ast.AST:
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            cuerpo = nodo.body
            if (cuerpo and isinstance(cuerpo[0], ast.Expr)
                    and isinstance(cuerpo[0].value, ast.Constant)
                    and isinstance(cuerpo[0].value.value, str)):
                nodo.body = cuerpo[1:]
    return arbol


def _simbolos(codigo: str) -> dict[str, list[str]]:
    """nombre → líneas normalizadas, para cada función o clase del código."""
    arbol = _sin_docstrings(ast.parse(codigo))
    return {
        nodo.name: ast.unparse(nodo).splitlines()
        for nodo in ast.walk(arbol)
        if isinstance(nodo, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _cabecera(codigo: str) -> list[str]:
    """Las líneas de imports y constantes de módulo de un listado."""
    arbol = _sin_docstrings(ast.parse(codigo))
    lineas: list[str] = []
    for nodo in arbol.body:
        if isinstance(nodo, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign)):
            lineas.extend(ast.unparse(nodo).splitlines())
    return lineas


def _canonica(linea: str) -> str:
    """La línea con sus espacios colapsados: el SQL dentro de las cadenas
    cambia de sangría según dónde presente el libro el listado."""
    return " ".join(linea.split())


def _primera_ausente(heno: list[str], aguja: list[str]) -> str | None:
    """La primera línea de `aguja` que no sale en orden dentro de `heno`.

    Una línea ``...`` en la aguja es elisión del libro: salta lo que haga
    falta. None si la aguja completa cabe dentro del heno.
    """
    restantes = iter(_canonica(linea) for linea in heno)
    for linea in (_canonica(linea) for linea in aguja):
        if linea == "...":
            continue
        for candidata in restantes:
            if candidata == linea:
                break
        else:
            return linea
    return None


def _sin_comentarios_ni_blancos(texto: str) -> list[str]:
    return [
        linea.rstrip()
        for linea in texto.splitlines()
        if linea.strip() and not linea.lstrip().startswith("#")
    ]


# -------------------------------------------------------------------- avisos

def _aviso_por_simbolos(capitulo: str, fichero: Path, cuerpo: str, real: str,
                        avisos: list[str]) -> None:
    reales = _simbolos(real)
    for nombre, lineas in _simbolos(cuerpo).items():
        if nombre not in reales:
            avisos.append(f"{capitulo}: «{nombre}» del listado no existe en {fichero.name}")
            continue
        ausente = _primera_ausente(reales[nombre], lineas)
        if ausente:
            avisos.append(
                f"{capitulo}: {fichero.name}::{nombre} difiere del fichero real "
                f"— primera línea sin correspondencia: {ausente}"
            )
    pool = {_canonica(linea) for linea in ast.unparse(_sin_docstrings(ast.parse(real))).splitlines()}
    for linea in _cabecera(cuerpo):
        if _canonica(linea) not in pool:
            avisos.append(
                f"{capitulo}: el listado de {fichero.name} declara «{linea}» "
                f"y el fichero real no lo tiene"
            )


def _aviso_por_lineas(capitulo: str, fichero: Path, cuerpo: str, avisos: list[str]) -> None:
    if not fichero.exists():
        avisos.append(f"{capitulo}: el listado declara «{fichero.name}» y el fichero no existe")
        return
    real = fichero.read_text(encoding="utf-8")
    ausente = _primera_ausente(
        _sin_comentarios_ni_blancos(real), _sin_comentarios_ni_blancos(cuerpo)
    )
    if ausente:
        avisos.append(
            f"{capitulo}: {fichero.name} difiere del fichero real "
            f"— primera línea sin correspondencia: {ausente}"
        )


def _aviso_python(capitulo: str, fichero: Path, cuerpo: str, avisos: list[str]) -> None:
    if not fichero.exists():
        avisos.append(f"{capitulo}: el listado declara «{fichero.name}» y el fichero no existe")
        return
    real = fichero.read_text(encoding="utf-8")
    try:
        _aviso_por_simbolos(capitulo, fichero, cuerpo, real, avisos)
    except SyntaxError:  # el listado es un fragmento sin cabecera: línea a línea
        _aviso_por_lineas(capitulo, fichero, cuerpo, avisos)


# --------------------------------------------------------------------- test

def test_los_listados_del_libro_son_el_codigo_del_paquete():
    avisos: list[str] = []
    for capitulo, fichero, lenguaje, cuerpo in bloques_declarados():
        if lenguaje == "python":
            _aviso_python(capitulo, fichero, cuerpo, avisos)
        else:
            _aviso_por_lineas(capitulo, fichero, cuerpo, avisos)
    assert not avisos, "\n\n".join(avisos)


def test_las_rutas_que_el_libro_cita_existen():
    citadas: set[str] = set()
    for md in sorted(LIBRO.glob("*.md")):
        citadas.update(CITA.findall(md.read_text(encoding="utf-8")))
    fantasmas = [ruta for ruta in sorted(citadas) if not (RAIZ / ruta).exists()]
    assert not fantasmas, f"El libro cita ficheros que no existen: {fantasmas}"
