"""El adaptador de LLM: reescritor, juez de cosecha y generador ensamblado (caps. 12-14).

Tres papeles del mismo modelo, tres contratos distintos — y una regla
de la serie que aquí es código: el juez certifica encaje consulta-cosecha,
no verdad; y el generador ensambla, nunca compone.
"""

from __future__ import annotations

from cocinando.dominio.modelos import (
    Consulta,
    Hit,
    PlantillaGeneracion,
    Respuesta,
    Veredicto,
)
from cocinando.dominio.puertos import JuezCosecha, ReescritorConsulta


class ClienteChat:
    """El cliente de chat mínimo: un solo punto donde el proveedor existe."""

    MODELO = "gpt-4o-mini"  # el de omisión del repo; el real del despacho, en configuracion.py

    def __init__(self) -> None:
        self._cliente = None

    @property
    def cliente(self):
        if self._cliente is None:
            from openai import OpenAI  # importación perezosa
            self._cliente = OpenAI()
        return self._cliente

    def completar(self, sistema: str, usuario: str, temperatura: float = 0.0) -> str:
        respuesta = self.cliente.chat.completions.create(
            model=self.MODELO,
            temperature=temperatura,   # cero: la respuesta es un instrumento, no una prosa
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user", "content": usuario},
            ],
        )
        return respuesta.choices[0].message.content or ""


class ReescritorLLM(ReescritorConsulta):
    """La pieza que faltaba: normalizar y reescribir ANTES de la primera búsqueda.

    Semántico después de lo determinista; nunca responde — solo reescribe.
    """

    SISTEMA = (
        "Eres el normalizador de consultas de un sistema de conocimiento. "
        "Corrige la ortografía, sustituye la jerga ambigua por el término del dominio "
        "y añade los sinónimos oficiales entre paréntesis. NO respondas la consulta, "
        "NO añadas información: devuelve solo la consulta reescrita."
    )

    def __init__(self, chat: ClienteChat | None = None) -> None:
        self.chat = chat or ClienteChat()

    def reescribir(self, consulta: Consulta) -> Consulta:
        texto = self.chat.completar(self.SISTEMA, consulta.texto)
        return Consulta(texto=texto.strip(), audiencia=consulta.audiencia,
                        dominio=consulta.dominio)


class JuezCosechaLLM(JuezCosecha):
    """El juez con veredictos cerrados: responde, parcial, no responde.

    Cerrados a propósito — el antídoto del veredicto complaciente (libro 2, cap. 16).
    Certifica encaje consulta-cosecha; jamás verdad jurídica.
    """

    SISTEMA = (
        "Eres el juez de cosecha de un sistema de conocimiento. Dado el material "
        "recuperado, emite UNO de estos tres veredictos y nada más:\n"
        "RESPONDE — la cosecha cubre la pregunta entera.\n"
        "PARCIAL — la cubre a medias.\n"
        "NO_RESPONDE — es de otro asunto o no alcanza.\n"
        "Devuelve solo la palabra del veredicto."
    )

    def __init__(self, chat: ClienteChat | None = None) -> None:
        self.chat = chat or ClienteChat()

    def veredictar(self, consulta: Consulta, cosecha: list[Hit]) -> Veredicto:
        if not cosecha:
            return Veredicto.NO_RESPONDE
        material = "\n\n".join(f"[{i + 1}] {h.pildora.titulo}\n{h.pildora.texto}"
                               for i, h in enumerate(cosecha))
        palabra = self.chat.completar(
            self.SISTEMA, f"Consulta: {consulta.texto}\n\nCosecha:\n{material}"
        ).strip().upper()
        try:
            return Veredicto(palabra.split()[0])
        except ValueError:
            return Veredicto.PARCIAL   # un juez ininteligible no es libre: es parcial de fábrica


class GeneradorEnsamblado:
    """La plantilla del libro 3 hecha código: ensamblar, no componer.

    Las seis piezas de la plantilla son datos (PlantillaGeneracion) y el
    material entra citado — [Fuente N] — para que toda afirmación sea
    comprobable y toda cita verificable por máquina (libro 3, cap. 14).
    """

    def __init__(self, chat: ClienteChat | None = None,
                 plantilla: PlantillaGeneracion | None = None) -> None:
        self.chat = chat or ClienteChat()
        self.plantilla = plantilla or PLANTILLA_POR_OMISION

    def _contexto(self, cosecha: list[Hit]) -> str:
        return "\n\n".join(
            f"[Fuente {i + 1} · {h.pildora.titulo}]\n{h.pildora.texto}"
            for i, h in enumerate(cosecha)
        )

    def generar(self, consulta: Consulta, cosecha: list[Hit]) -> Respuesta:
        p = self.plantilla
        sistema = f"{p.papel}\n\nMATERIAL:\n{p.material}\n\nPROHIBICIONES:\n{p.prohibiciones}"
        usuario = (
            f"CONSULTA: {consulta.texto}\n\nCONTEXTO:\n{self._contexto(cosecha)}\n\n"
            f"CITAS: {p.citas}\nFORMATO: {p.formato}\nABSTENCIÓN: {p.abstencion}"
        )
        texto = self.chat.completar(sistema, usuario)
        return Respuesta(
            texto=texto,
            citas=tuple(f"Fuente {i + 1}" for i in range(len(cosecha))),
            patron="directo",
        )


PLANTILLA_POR_OMISION = PlantillaGeneracion(
    audiencia="por_omision",
    papel=(
        "Redactas la respuesta para [audiencia] a partir exclusivamente del contexto "
        "entregado. No tienes conocimiento propio aplicable: todo lo que digas debe "
        "venir del contexto."
    ),
    material=(
        "Cada bloque de contexto lleva su identificador [Fuente N]; úsalo para citar. "
        "Los bloques caducados no responden. Si dos bloques contradicen, "
        "expón la discrepancia, no elijas."
    ),
    prohibiciones=(
        "No añadas conocimiento externo. No completes lo que el contexto deja a medias. "
        "No redondees cifras. No unifiques versiones distintas. Sin cortesía inflada."
    ),
    citas="Cada cifra, plazo y condición lleva su referencia [Fuente N].",
    formato="Dato primero, desarrollo después, referencias al final. Respuesta corta.",
    abstencion=(
        "Si el contexto no respalda la respuesta, no respondas: di que no consta en el "
        "corpus y señala lo más cercano que contiene. Toda abstención queda anotada."
    ),
)
