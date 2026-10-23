POLINOMIO = 0x1021
VALOR_INICIAL = 0xFFFF


def crc16_ccitt(datos):
    # bit a bit y sin tabla, el mismo cálculo que haría el Arduino con poca RAM
    crc = VALOR_INICIAL
    for byte in datos:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ POLINOMIO) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc