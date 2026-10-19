from pc.enlace.receptor import Receptor


def armar(W, J):
    respuestas, entregados = [], []
    r = Receptor(W=W, J=J,
                 enviar_respuesta=lambda tipo, seq: respuestas.append((tipo, seq)),
                 entregar_datos=entregados.append)
    return r, respuestas, entregados


def test_ejemplo_J3():
    r, respuestas, entregados = armar(W=4, J=3)
    r.recibir_trama(0, b"a", True)
    r.recibir_trama(1, b"", False)   # CRC mal
    r.recibir_trama(2, b"c", True)   # adelantada, va al buffer
    r.recibir_trama(3, b"d", True)   # adelantada, va al buffer
    r.recibir_trama(1, b"b", True)   # llega la que faltaba
    assert entregados == [b"a", b"b", b"c", b"d"]
    assert respuestas == [("ACK", 0), ("NAK", 1), ("ACK", 0), ("ACK", 0), ("ACK", 3)]


def test_J0_bota_las_adelantadas():
    r, respuestas, entregados = armar(W=4, J=0)
    r.recibir_trama(0, b"a", True)
    r.recibir_trama(2, b"c", True)
    r.recibir_trama(3, b"d", True)
    assert entregados == [b"a"]
    assert r.buffer == {}


def test_J_lleno_bota_las_que_no_caben():
    r, _, entregados = armar(W=8, J=2)
    for seq in (1, 2, 3):            # la 0 nunca llegó
        r.recibir_trama(seq, bytes([seq]), True)
    assert sorted(r.buffer) == [1, 2]


def test_arranque_pide_la_0_una_sola_vez():
    r, respuestas, _ = armar(W=4, J=3)
    r.recibir_trama(1, b"b", True)
    r.recibir_trama(2, b"c", True)
    assert respuestas == [("NAK", 0)]


def test_repetida_repite_el_ultimo_ack():
    r, respuestas, entregados = armar(W=4, J=3)
    r.recibir_trama(0, b"a", True)
    r.recibir_trama(0, b"a", True)
    assert entregados == [b"a"]
    assert respuestas == [("ACK", 0), ("ACK", 0)]


def test_vuelta_de_15_a_0():
    r, respuestas, entregados = armar(W=4, J=3)
    for seq in range(16):
        r.recibir_trama(seq, bytes([seq]), True)
    r.recibir_trama(0, b"x", True)
    assert len(entregados) == 17
    assert respuestas[-1] == ("ACK", 0)
