from collections import namedtuple

from pc.enlace import stuffing
from pc.enlace.crc import crc16_ccitt

DATA, ACK, NAK, CONTROL = 0, 1, 2, 3
MAX_DATOS = 900

# crc_ok queda en False si algo falla: delimitadores, stuffing, longitud o CRC
Trama = namedtuple("Trama", "tipo secuencia datos crc_ok")


def construir(tipo, secuencia, datos=b""):
    if tipo not in (DATA, ACK, NAK, CONTROL):
        raise ValueError(f"tipo inválido: {tipo}")
    if not 0 <= secuencia <= 15:
        raise ValueError(f"la secuencia va de 0 a 15, llegó {secuencia}")
    if len(datos) > MAX_DATOS:
        raise ValueError(f"máximo {MAX_DATOS} bytes de datos, llegaron {len(datos)}")

    # tipo en los 2 bits altos, secuencia en los 4 siguientes, 2 bits libres
    control = (tipo << 6) | (secuencia << 2)
    cuerpo = bytes([control]) + len(datos).to_bytes(2, "big") + datos
    crc = crc16_ccitt(cuerpo).to_bytes(2, "big")

    # el CRC se calcula sobre los bytes originales y el stuffing va después
    return bytes([stuffing.SOF]) + stuffing.aplicar(cuerpo + crc) + bytes([stuffing.EOF])


def parsear(crudo):
    malformada = Trama(None, None, b"", False)

    if len(crudo) < 2 or crudo[0] != stuffing.SOF or crudo[-1] != stuffing.EOF:
        return malformada
    try:
        interior = stuffing.quitar(crudo[1:-1])
    except ValueError:
        return malformada

    # mínimo: control (1) + longitud (2) + crc (2)
    if len(interior) < 5:
        return malformada

    cuerpo, crc_recibido = interior[:-2], interior[-2:]
    control = cuerpo[0]
    longitud = int.from_bytes(cuerpo[1:3], "big")
    datos = cuerpo[3:]

    crc_ok = len(datos) == longitud and crc16_ccitt(cuerpo).to_bytes(2, "big") == crc_recibido
    return Trama(control >> 6, (control >> 2) & 0x0F, datos, crc_ok)