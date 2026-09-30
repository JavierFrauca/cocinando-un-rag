"""La puerta de salida del cap. 5: la píldora íntegra, la tabla entera, la identidad estable."""

from cocinando.dominio.pildoras import trocear

DOC = """# Convenio 2024
## 1. Ámbito
Aplica a toda la plantilla.
## 2. Tarifas
| Concepto | Importe |
|---|---|
| Hora extra | 22 € |
| Nocturnidad | 4 € |
Vigente desde 2024-01-01.
"""


def test_tabla_atomica():
    pildoras = trocear(DOC, fuente="c24.md", dominio="convenios")
    tablas = [p for p in pildoras if p.tipo == "tabla"]
    assert len(tablas) == 1
    assert "| Hora extra | 22 € |" in tablas[0].texto        # entera
    assert "Ámbito" not in tablas[0].texto                  # sin mezclar con la prosa


def test_contexto_viaja_con_el_trozo():
    pildoras = trocear(DOC, fuente="c24.md")
    ambito = [p for p in pildoras if "Ámbito" in p.titulo]
    assert ambito and ambito[0].texto.startswith("[Convenio 2024 > 1. Ámbito]")


def test_identidad_idempotente():
    a = trocear(DOC, fuente="x.md")
    b = trocear(DOC, fuente="x.md")
    assert [p.id for p in a] == [p.id for p in b]           # re-ingestar no duplica
    c = trocear(DOC.replace("toda la plantilla", "todo el personal"), fuente="x.md")
    assert [p.id for p in a] != [p.id for p in c]           # cambiar el texto cambia el id
