"""Servicio: reescribir, recuperar, juzgar y generar (caps. 11-14).

El caso de uso entero de la capa de respuesta, orquestando puertos.
Aquí no hay un if de proveedor: los adaptadores cambian, el servicio no.
"""

from __future__ import annotations

from cocinando.dominio.modelos import Consulta, Respuesta, Veredicto
from cocinando.dominio.puertos import (
    Generador,
    JuezCosecha,
    ClienteEmbeddings,
    RepositorioPildoras,
    ReescritorConsulta,
)

K_POR_OMISION = 10


class ServicioRespuesta:
    """El momento de la verdad: una consulta entra, una respuesta — o una abstención — sale.

    El orden es el del método y no se negocia: reescribir ANTES de buscar,
    juzgar ANTES de generar, abstenerse cuando el juez dice que la cosecha
    no responde. Cada paso recibe del anterior su contrato y nada más.
    """

    def __init__(
        self,
        repo: RepositorioPildoras,
        embeddings: ClienteEmbeddings,
        reescritor: ReescritorConsulta,
        juez: JuezCosecha,
        generador: Generador,
        k: int = K_POR_OMISION,
    ) -> None:
        self.repo = repo
        self.embeddings = embeddings
        self.reescritor = reescritor
        self.juez = juez
        self.generador = generador
        self.k = k

    def responder(self, consulta: Consulta) -> tuple[Respuesta, list]:
        # 1 · La reescritura: determinista primero, semántico después.
        #     Ocurre siempre, antes de la primera búsqueda, sin mirar resultados.
        reescrita = self.reescritor.reescribir(consulta)

        # 2 · El vector de la consulta reescrita: la búsqueda merece
        #     la mejor formulación, no la que escribió el usuario con prisa.
        vector = self.embeddings.incrustar([reescrita.texto])[0]

        # 3 · La cosecha híbrida: denso + léxico con su fusión declarada.
        cosecha = self.repo.buscar_hibrido(
            vector, lexico=reescrita.texto, k=self.k, dominio=reescrita.dominio
        )

        # 4 · El juez de cosecha: veredictos cerrados sobre lo recuperado.
        veredicto = self.juez.veredictar(reescrita, cosecha)

        # 5 · La abstención honesta cuando toca: un éxito que se celebra,
        #     no un error que se esconde (libro 3, cap. 3).
        if not cosecha or veredicto is Veredicto.NO_RESPONDE:
            return (
                Respuesta(
                    texto=(
                        "No consta en el corpus; lo más cercano que contiene es "
                        + (cosecha[0].pildora.titulo if cosecha else "nada relacionado")
                        + "."
                    ),
                    abstencion=True,
                    motivo_abstencion=f"juez: {veredicto.value}" if cosecha else "cosecha vacía",
                ),
                cosecha,
            )

        # 6 · La generación ensamblada: la plantilla compone con material citado.
        return self.generador.generar(reescrita, cosecha), cosecha
