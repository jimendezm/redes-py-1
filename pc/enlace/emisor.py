import time


class Emisor:
    def __init__(self, bloques, W, J, timeout, enviar_trama, reloj=time.monotonic):
        self.bloques = bloques
        self.W = W
        self.J = J
        self.timeout = timeout
        self.enviar_trama = enviar_trama
        self.reloj = reloj

        # base y siguiente son índices en la lista de bloques (no vuelven a 0);
        # la secuencia que viaja en la trama es ese índice % 16
        self.base = 0
        self.siguiente = 0
        self.vence = None
        self.enviadas = 0
        self.retransmisiones = 0

    @property
    def en_vuelo(self):
        return self.siguiente - self.base

    @property
    def terminado(self):
        return self.base >= len(self.bloques)

    def enviar_nuevas(self):
        while self.siguiente < len(self.bloques) and self.en_vuelo < self.W:
            self._mandar(self.siguiente)
            self.enviadas += 1
            if self.vence is None:
                self._arrancar_timer()
            self.siguiente += 1

    def al_recibir_ack(self, n):
        # ACK(n) confirma todo hasta n, contamos cuántos bloques son desde la base
        avance = (n - self.base) % 16 + 1
        if avance > self.en_vuelo:
            return  # repetido, o confirma algo que ya estaba confirmado

        self.base += avance
        self.vence = None
        if self.en_vuelo > 0:
            self._arrancar_timer()
        self.enviar_nuevas()

    def al_recibir_nak(self, n):
        # el NAK trae la secuencia que el receptor espera, la ubicamos dentro de la ventana
        desplazamiento = (n - self.base) % 16
        if desplazamiento < self.en_vuelo:
            self._retransmitir(self.base + desplazamiento)

    def revisar_timer(self):
        # se llama en cada vuelta del ciclo principal, así no hacen falta hilos
        if self.vence is not None and self.en_vuelo > 0 and self.reloj() >= self.vence:
            self._retransmitir(self.base)

    def _retransmitir(self, desde):
        # J=0 es Go-Back-N puro: se repite todo desde la trama fallida.
        # Con J>0 el receptor guardó las siguientes, solo hace falta esa.
        hasta = desde + 1 if self.J > 0 else self.siguiente
        for i in range(desde, hasta):
            self._mandar(i)
            self.retransmisiones += 1
        self._arrancar_timer()

    def _mandar(self, i):
        self.enviar_trama(i % 16, self.bloques[i])

    def _arrancar_timer(self):
        self.vence = self.reloj() + self.timeout