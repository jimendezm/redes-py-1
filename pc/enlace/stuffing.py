SOF = 0x7E
EOF = 0x7F
ESC = 0x7D
MASCARA = 0x20

RESERVADOS = (SOF, EOF, ESC)


def aplicar(datos):
    salida = bytearray()
    for byte in datos:
        if byte in RESERVADOS:
            salida.append(ESC)
            salida.append(byte ^ MASCARA)
        else:
            salida.append(byte)
    return bytes(salida)


def quitar(datos):
    salida = bytearray()
    escapado = False
    for byte in datos:
        if escapado:
            salida.append(byte ^ MASCARA)
            escapado = False
        elif byte == ESC:
            escapado = True
        else:
            salida.append(byte)
    if escapado:
        raise ValueError("la trama termina justo después de un escape")
    return bytes(salida)