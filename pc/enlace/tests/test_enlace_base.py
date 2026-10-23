import pytest

from pc.enlace.formato import trama
from pc.enlace.formato.crc import crc16_ccitt
from pc.enlace.formato import stuffing


def test_crc_vector_conocido():
    # valor de referencia publicado para CRC-16-CCITT con inicial 0xFFFF
    assert crc16_ccitt(b"123456789") == 0x29B1


def test_stuffing_ida_y_vuelta_con_bytes_reservados():
    original = bytes([0x01, 0x7E, 0x7F, 0x7D, 0x7D, 0xFF])
    enviado = stuffing.aplicar(original)
    assert stuffing.SOF not in enviado and stuffing.EOF not in enviado
    assert stuffing.quitar(enviado) == original


def test_ejemplo_del_documento():
    # DATA, secuencia 3, datos 41 42 43 -> 7E 0C 00 03 41 42 43 [CRC] 7F
    crudo = trama.construir(trama.DATA, 3, b"ABC")
    assert crudo[:7] == bytes([0x7E, 0x0C, 0x00, 0x03, 0x41, 0x42, 0x43])
    assert crudo[-1] == 0x7F


def test_construir_y_parsear():
    datos = bytes(range(256)) * 3
    t = trama.parsear(trama.construir(trama.DATA, 15, datos))
    assert t == (trama.DATA, 15, datos, True)


def test_ack_y_nak_sin_datos():
    for tipo in (trama.ACK, trama.NAK):
        t = trama.parsear(trama.construir(tipo, 7))
        assert t == (tipo, 7, b"", True)


def test_un_byte_dañado_falla_el_crc():
    crudo = bytearray(trama.construir(trama.DATA, 2, b"hola mundo"))
    crudo[5] ^= 0x01
    assert trama.parsear(bytes(crudo)).crc_ok is False


def test_trama_sin_delimitadores():
    assert trama.parsear(b"\x01\x02\x03").crc_ok is False


def test_validaciones_al_construir():
    with pytest.raises(ValueError):
        trama.construir(trama.DATA, 16, b"")
    with pytest.raises(ValueError):
        trama.construir(trama.DATA, 0, bytes(901))
    with pytest.raises(ValueError):
        trama.construir(9, 0, b"")
