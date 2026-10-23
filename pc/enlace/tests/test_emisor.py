from pc.enlace.protocolo.emisor import Emisor


class RelojFalso:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def armar(n_bloques, W, J, timeout=1.0):
    reloj = RelojFalso()
    enviadas = []
    e = Emisor([bytes([i]) for i in range(n_bloques)], W=W, J=J, timeout=timeout,
               enviar_trama=lambda seq, datos: enviadas.append(seq), reloj=reloj)
    return e, enviadas, reloj


def test_no_pasa_de_W_tramas_en_vuelo():
    e, enviadas, _ = armar(10, W=4, J=0)
    e.enviar_nuevas()
    assert enviadas == [0, 1, 2, 3]


def test_ack_desliza_la_ventana():
    e, enviadas, _ = armar(10, W=4, J=0)
    e.enviar_nuevas()
    e.al_recibir_ack(1)              # confirma 0 y 1
    assert enviadas == [0, 1, 2, 3, 4, 5]


def test_ack_repetido_no_mueve_nada():
    e, enviadas, _ = armar(10, W=4, J=0)
    e.enviar_nuevas()
    e.al_recibir_ack(1)
    antes = (e.base, list(enviadas))
    e.al_recibir_ack(1)
    assert (e.base, enviadas) == antes


def test_timeout_J0_repite_toda_la_ventana():
    e, enviadas, reloj = armar(10, W=4, J=0)
    e.enviar_nuevas()
    reloj.t = 1.5
    e.revisar_timer()
    assert enviadas[4:] == [0, 1, 2, 3]


def test_timeout_J3_repite_solo_la_base():
    e, enviadas, reloj = armar(10, W=4, J=3)
    e.enviar_nuevas()
    reloj.t = 1.5
    e.revisar_timer()
    assert enviadas[4:] == [0]


def test_nak_retransmite_sin_esperar_el_timer():
    e, enviadas, _ = armar(10, W=4, J=3)
    e.enviar_nuevas()
    e.al_recibir_ack(0)              # base pasa a 1
    e.al_recibir_nak(1)
    assert enviadas[-1] == 1


def test_secuencia_da_la_vuelta_en_16():
    e, enviadas, _ = armar(20, W=4, J=0)
    e.enviar_nuevas()
    for n in range(0, 17):
        e.al_recibir_ack(n % 16)
    assert 0 in enviadas[16:] and 15 in enviadas
