import random

import pytest

from pc.enlace.formato import trama
from pc.enlace.protocolo.emisor import Emisor
from pc.enlace.protocolo.receptor import Receptor

TIPO = {"ACK": trama.ACK, "NAK": trama.NAK}


def correr(W, J, semilla, perdida=0.15, corrupcion=0.15, n_bloques=60):
    azar = random.Random(semilla)
    bloques = [bytes([i % 256]) * 20 for i in range(n_bloques)]
    ida, vuelta, entregados = [], [], []
    reloj = {"t": 0.0}

    def al_cable(lista, crudo):
        # cable falso: pierde una parte y daña un byte de otra parte
        r = azar.random()
        if r < perdida:
            return
        if r < perdida + corrupcion:
            crudo = bytearray(crudo)
            crudo[azar.randrange(len(crudo))] ^= 0xFF
            crudo = bytes(crudo)
        lista.append(crudo)

    emisor = Emisor(bloques, W, J, timeout=1.0,
                    enviar_trama=lambda seq, d: al_cable(ida, trama.construir(trama.DATA, seq, d)),
                    reloj=lambda: reloj["t"])
    receptor = Receptor(W, J,
                        enviar_respuesta=lambda tipo, seq: al_cable(vuelta, trama.construir(TIPO[tipo], seq)),
                        entregar_datos=entregados.append)

    emisor.enviar_nuevas()
    for _ in range(100000):
        if emisor.terminado:
            break
        while ida:
            t = trama.parsear(ida.pop(0))
            if t.crc_ok:
                receptor.recibir_trama(t.secuencia, t.datos, True)
            else:
                receptor.recibir_trama(0, b"", False)
        while vuelta:
            t = trama.parsear(vuelta.pop(0))
            if t.crc_ok and t.tipo == trama.ACK:
                emisor.al_recibir_ack(t.secuencia)
            elif t.crc_ok and t.tipo == trama.NAK:
                emisor.al_recibir_nak(t.secuencia)
        reloj["t"] += 0.1
        emisor.revisar_timer()
    return bloques, entregados, emisor


@pytest.mark.parametrize("W", [4, 6, 8])
@pytest.mark.parametrize("J", [0, 2, 4])
@pytest.mark.parametrize("semilla", range(10))
def test_el_archivo_llega_completo_y_en_orden(W, J, semilla):
    bloques, entregados, emisor = correr(W, min(J, W), semilla)
    assert emisor.terminado
    assert entregados == bloques
