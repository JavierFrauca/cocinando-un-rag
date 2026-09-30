"""La puerta de salida de los caps. 12-14: el servicio completo con dobles de prueba."""

from cocinando.aplicacion.servir import ServicioRespuesta
from cocinando.dominio.modelos import Consulta, Veredicto
from pruebas.fakes import EmbeddingsFalsos, GeneradorFalso, JuezFalso, ReescritorFalso

from cocinando.infraestructura.sqlite_repo import RepositorioPildorasSqlite

DOC = "# Convenio\n## Plazos\nEl plazo de reclamación es de veinte días hábiles.\n"


def _servicio(tmp_path, veredicto=Veredicto.RESPONDE):
    repo = RepositorioPildorasSqlite(tmp_path / "p.db", dimensiones=64)
    embeddings = EmbeddingsFalsos()
    pildoras = __import__("cocinando.dominio.pildoras", fromlist=["trocear"]).trocear(
        DOC, fuente="c24.md", dominio="laboral")
    repo.guardar(pildoras, embeddings.incrustar([p.texto for p in pildoras]))
    return ServicioRespuesta(
        repo=repo, embeddings=embeddings, reescritor=ReescritorFalso(),
        juez=JuezFalso(veredicto), generador=GeneradorFalso(),
    ), pildoras


def test_flujo_completo_genera_con_cosecha(tmp_path):
    servicio, _ = _servicio(tmp_path)
    respuesta, cosecha = servicio.responder(Consulta(texto="plazo de reclamación"))
    assert not respuesta.abstencion
    assert cosecha                                     # el generador recibió material citado


def test_juez_no_responde_produce_abstencion_honesta(tmp_path):
    servicio, cosecha = _servicio(tmp_path, veredicto=Veredicto.NO_RESPONDE)
    respuesta, _ = servicio.responder(Consulta(texto="plazo de reclamación"))
    assert respuesta.abstencion                        # la abstención es un éxito, no un fallo
    assert "No consta en el corpus" in respuesta.texto
    assert "juez" in respuesta.motivo_abstencion


def test_reescritura_antes_de_buscar(tmp_path):
    servicio, _ = _servicio(tmp_path)
    servicio.responder(Consulta(texto="plazo"))
    assert servicio.reescritor.veces == 1              # siempre, antes de la primera búsqueda
