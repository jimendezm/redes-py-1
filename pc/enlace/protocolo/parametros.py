SOBRECARGA_TRAMA = 7            # SOF, Control, Longitud (2), CRC (2) y EOF
BITS_POR_BYTE_UART = 10         # 8 de datos + bit de inicio + bit de parada
PRESUPUESTO_BUFFER_J = 1_000_000  # bytes de la PC reservados para el buffer J


def calcular_J(W, payload, presupuesto=PRESUPUESTO_BUFFER_J):
    # más de W-1 adelantadas no caben nunca en la ventana, J no puede ser mayor
    caben = presupuesto // (payload + SOBRECARGA_TRAMA)
    return min(W - 1, caben)


def tiempo_en_cable(n_bytes, baud, hamming):
    # con Hamming (8,4) cada byte sale como dos, así que el cable tarda el doble
    reales = n_bytes * 2 if hamming else n_bytes
    return reales * BITS_POR_BYTE_UART / baud


def calcular_timeout(W, payload, baud, hamming, margen=0.5):
    # punto de partida: tiempo de sacar toda la ventana, más el ACK de vuelta y un margen.
    # Hay que ajustarlo midiendo con el enlace real.
    ida = tiempo_en_cable(payload + SOBRECARGA_TRAMA, baud, hamming)
    ack = tiempo_en_cable(SOBRECARGA_TRAMA, baud, hamming)
    return W * ida + ack + margen


def tasa_error_estimada(errores_crc, recibidas):
    # fórmula provisoria: tramas con error entre tramas recibidas.
    # Es el único lugar que hay que tocar cuando el grupo defina la definitiva.
    if recibidas == 0:
        return 0.0
    return 100 * errores_crc / recibidas
