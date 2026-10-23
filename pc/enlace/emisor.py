import logging
import time

log = logging.getLogger("enlace.emisor")


class Emisor:
    def __init__(self, bloques, W, J, timeout, enviar_trama, reloj=time.monotonic,
                 max_reintentos=None):
        self.bloques = bloques
        self.W = W
        self.J = J
        self.timeout = timeout
        self.enviar_trama = enviar_trama
        self.reloj = reloj
        self.max_reintentos = max_reintentos   # timeouts seguidos de la misma trama; None = sin límite

        # base y siguiente son índices en la lista de bloques (no vuelven a 0);
        # la secuencia que viaja en la trama es ese índice % 16
        self.base = 0
        self.siguiente = 0
        self.vence = None
        self.enviadas = 0
        self.retransmisiones = 0
        self.timeouts_seguidos = 0
        self.abortado = False                  # True = error irrecuperable, se dejó de insistir

    @property
    def en_vuelo(self):
        return self.siguiente - self.base

    @property
    def terminado(self):
        return self.base >= len(self.bloques)

    def enviar_nuevas(self):
        if self.abortado:
            return
        while self.siguiente < len(self.bloques) and self.en_vuelo < self.W:
            self._mandar(self.siguiente)
            self.enviadas += 1
            if self.vence is None:
                self._arrancar_timer()
            self.siguiente += 1

    def al_recibir_ack(self, n):
        # ACK(n) confirma todo hasta n, contamos cuántos bloques son desde la base
        if self.abortado:
            return
        avance = (n - self.base) % 16 + 1
        if avance > self.en_vuelo:
            log.debug("ACK(%d) repetido o viejo, se ignora", n)
            return  # repetido, o confirma algo que ya estaba confirmado

        self.base += avance
        self.timeouts_seguidos = 0             # hubo progreso, la cuenta empieza de nuevo
        log.debug("ACK(%d): la base pasa al bloque %d, en vuelo %d", n, self.base, self.en_vuelo)
        self.vence = None
        if self.en_vuelo > 0:
            self._arrancar_timer()
        self.enviar_nuevas()

    def al_recibir_nak(self, n):
        # el NAK trae la secuencia que el receptor espera, la ubicamos dentro de la ventana
        if self.abortado:
            return
        desplazamiento = (n - self.base) % 16
        if desplazamiento < self.en_vuelo:
            log.info("NAK(%d): se retransmite sin esperar al temporizador", n)
            self._retransmitir(self.base + desplazamiento)

    def revisar_timer(self):
        # se llama en cada vuelta del ciclo principal, así no hacen falta hilos
        if self.abortado or self.vence is None or self.en_vuelo == 0:
            return
        if self.reloj() < self.vence:
            return

        self.timeouts_seguidos += 1
        log.warning("Timeout %d de la trama %d (bloque %d)",
                    self.timeouts_seguidos, self.base % 16, self.base)
        if self.max_reintentos is not None and self.timeouts_seguidos > self.max_reintentos:
            # la misma trama venció demasiadas veces: error irrecuperable
            log.error("La trama %d venció %d veces seguidas: error irrecuperable",
                      self.base % 16, self.timeouts_seguidos)
            self.abortado = True
            return
        self._retransmitir(self.base)

    def _retransmitir(self, desde):
        # J=0 es Go-Back-N puro: se repite todo desde la trama fallida.
        # Con J>0 el receptor guardó las siguientes, solo hace falta esa.
        hasta = desde + 1 if self.J > 0 else self.siguiente
        log.info("Retransmite %d trama(s) desde el bloque %d (secuencia %d), J=%d",
                 hasta - desde, desde, desde % 16, self.J)
        for i in range(desde, hasta):
            self._mandar(i)
            self.retransmisiones += 1
        self._arrancar_timer()

    def _mandar(self, i):
        log.debug("Envía DATA secuencia %d (bloque %d de %d, %d B)",
                  i % 16, i + 1, len(self.bloques), len(self.bloques[i]))
        self.enviar_trama(i % 16, self.bloques[i])

    def _arrancar_timer(self):
        self.vence = self.reloj() + self.timeout
