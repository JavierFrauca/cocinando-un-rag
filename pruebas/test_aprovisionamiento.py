"""Las puertas de salida de los caps. 3-4 y 7: manifiesto, normalización, Gold firmado."""

import pytest

from cocinando.aplicacion.aprovisionamiento import Manifiesto, ingesta, normalizar
from cocinando.aplicacion.sintesis import registrar_sintesis


def test_manifiesto_no_deja_pasar_lo_no_declarado(tmp_path):
    fichero = tmp_path / "manifiesto.json"
    declarado = tmp_path / "c24.md"
    declarado.write_text("# C24\nVigente.", encoding="utf-8")
    # El manifiesto declara la ruta exacta que la ingesta recibirá.
    clave = str(declarado).replace("\\", "/")
    fichero.write_text(
        f'{{"{clave}": {{"dominio": "convenios", "vigencia": "2024-01-01"}}}}',
        encoding="utf-8",
    )
    manifiesto = Manifiesto(fichero)
    assert ingesta(declarado, manifiesto) is not None

    intruso = tmp_path / "intruso.md"
    intruso.write_text("# Intruso\nNo estoy en el manifiesto.", encoding="utf-8")
    assert ingesta(intruso, manifiesto) is None   # no es un error: es el manifiesto funcionando


def test_normalizacion_fechas_a_iso():
    assert "2025-07-03" in normalizar("el plazo vence el 3/07/2025")
    assert normalizar("  espacios   dobles ") == "espacios dobles"


def test_sintesis_gold_exige_firma_humana():
    with pytest.raises(ValueError):
        registrar_sintesis("texto", dominio="convenios", firmada_por="   ")
    pildora = registrar_sintesis("texto", dominio="convenios", firmada_por="J. Frauca")
    assert pildora.tipo == "sintesis" and "J. Frauca" in pildora.texto
