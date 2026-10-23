import logging

log = logging.getLogger("enlace.receptor")


class Receptor:
    def __init__(self, W, J, enviar_respuesta, entregar_datos, registrar_error=None):
        self.W = W
        self.J = J
        self.enviar_respuesta = enviar_respuesta
        self.entregar_datos = entregar_datos
        self.registrar_error = registrar_error or (lambda: None)

        self.esperada = 0          # secuencia de la trama que toca, vuelve a 0 después del 15
        self.buffer = {}           # adelantadas guardadas: secuencia -> datos, nunca más de J
        self.entrego_algo = False  # mientras sea False no hay ACK válido que repetir
        self.ultimo_nak = None     # Esperada para la que ya pedimos con NAK
        self.recibidas = 0
        self.errores_crc = 0

    def recibir_trama(self, secuencia, datos, crc_ok):
        self.recibidas += 1

        if not crc_ok:
            # con el CRC malo tampoco nos fiamos de la secuencia, pedimos la que toca
            self.errores_crc += 1
            log.warning("CRC mal (error %d de %d recibidas), se descarta",
                        self.errores_crc, self.recibidas)
            self.registrar_error()
            self._pedir_esperada()
            return

        distancia = (secuencia - self.esperada) % 16
        if distancia == 0:
            self._entregar(datos)
        elif distancia < self.W:
            # adelantada: con J=0 el buffer nunca tiene espacio, y si J se llena
            # se pierde y el emisor la reenvía cuando le toque
            if len(self.buffer) < self.J:
                self.buffer[secuencia] = datos
                log.info("Trama %d adelantada (se espera la %d): se guarda en el buffer J (%d de %d)",
                         secuencia, self.esperada, len(self.buffer), self.J)
            else:
                log.info("Trama %d adelantada (se espera la %d): buffer J lleno (J=%d), se descarta",
                         secuencia, self.esperada, self.J)
            self._repetir_ack()
        else:
            # ya la habíamos entregado: retransmisión de más o ACK que se perdió
            log.debug("Trama %d repetida (ya entregada)", secuencia)
            self._repetir_ack()

    def _entregar(self, datos):
        log.debug("Trama %d en orden, se entrega", self.esperada)
        self.entregar_datos(datos)
        self.esperada = (self.esperada + 1) % 16

        # puede que las siguientes ya estuvieran guardadas esperando a esta
        while self.esperada in self.buffer:
            log.info("Trama %d sale del buffer J y se entrega", self.esperada)
            self.entregar_datos(self.buffer.pop(self.esperada))
            self.esperada = (self.esperada + 1) % 16

        self.entrego_algo = True
        self.ultimo_nak = None
        self.enviar_respuesta("ACK", (self.esperada - 1) % 16)

    def _repetir_ack(self):
        if self.entrego_algo:
            self.enviar_respuesta("ACK", (self.esperada - 1) % 16)
        else:
            # al arrancar, ACK(15) diría que ya llegó algo que no existe
            self._pedir_esperada()

    def _pedir_esperada(self):
        # un solo NAK por trama: si se pierde, el timer del emisor la recupera
        if self.ultimo_nak != self.esperada:
            log.info("Pide la trama %d con un NAK", self.esperada)
            self.enviar_respuesta("NAK", self.esperada)
            self.ultimo_nak = self.esperada
        else:
            log.debug("Ya se pidió la trama %d con un NAK, no se repite", self.esperada)
