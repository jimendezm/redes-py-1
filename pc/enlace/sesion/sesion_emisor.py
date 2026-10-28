import time

from pc.enlace.sesion import control
from pc.enlace.protocolo.emisor import Emisor
from pc.enlace.formato import trama
from pc.enlace.formato.lector_tramas import LectorTramas
from pc.enlace.protocolo.parametros import calcular_J, calcular_timeout

NEGOCIANDO, TRANSMITIENDO = "negociando", "transmitiendo"


class SesionEmisor:
    """Une el Emisor con el canal. Quien la use llama a tick() cada pocos milisegundos.

    Primero abre la sesión (INICIO / ACEPTADO) y después transmite los bloques.
    """

    def __init__(self, bloques, W, payload, baud, hamming, canal, tamano, extension,
                 al_estado=print, al_progreso=lambda porcentaje: None,
                 reloj=time.monotonic, max_reintentos=10, nombre=""):
        self.canal = canal
        self.al_estado = al_estado
        self.al_progreso = al_progreso
        self.reloj = reloj
        self.max_reintentos = max_reintentos
        self.lector = LectorTramas()

        self.J = calcular_J(W, payload)
        self.timeout = calcular_timeout(W, payload, baud, hamming)
        self.emisor = Emisor(bloques, W, self.J, self.timeout, self._enviar_datos,
                             reloj, max_reintentos)

        self._inicio = control.construir_inicio(W, self.J, payload, baud, hamming,
                                                tamano, extension, nombre)
        self._intentos_inicio = 0
        self._vence_inicio = None
        self._progreso = -1

        self.fase = NEGOCIANDO
        self.terminada = False
        self.abortada = False

    def iniciar(self):
        self.al_estado(f"[ENLACE] J = {self.J} | timeout = {self.timeout:.2f} s")
        self.al_estado("Esperando al receptor...")
        self._mandar_inicio()

    def tick(self):
        if self.terminada:
            return

        for crudo in self.lector.alimentar(self.canal.recibir(1024, 0)):
            t = trama.parsear(crudo)
            if not t.crc_ok:
                continue                     # respuesta dañada: los timers lo resuelven
            if self.fase == NEGOCIANDO:
                if t.tipo == trama.CONTROL and control.es_aceptado(t.datos):
                    self._comenzar()
            elif t.tipo == trama.ACK:
                self.emisor.al_recibir_ack(t.secuencia)
            elif t.tipo == trama.NAK:
                self.emisor.al_recibir_nak(t.secuencia)

        if self.fase == NEGOCIANDO:
            self._revisar_inicio()
            return

        self.emisor.revisar_timer()
        self._avisar_progreso()
        if self.emisor.abortado:
            self.al_estado("Estado de enlace ruidoso: errores irrecuperables")
            self._abortar()
        elif self.emisor.terminado:
            self._terminar()

    def _comenzar(self):
        self.fase = TRANSMITIENDO
        self.al_estado("Inicio de transmisión...")
        self.emisor.enviar_nuevas()
        self.al_estado("Transmisión en curso...")

    def _mandar_inicio(self):
        self.canal.enviar(self._inicio)
        self._intentos_inicio += 1
        self._vence_inicio = self.reloj() + self.timeout

    def _revisar_inicio(self):
        if self.reloj() < self._vence_inicio:
            return
        if self._intentos_inicio > self.max_reintentos:
            self.al_estado("El receptor no responde")
            self._abortar()
        else:
            self._mandar_inicio()

    def _abortar(self):
        self.terminada = True
        self.abortada = True
        self.al_estado("Transmisión abortada")

    def _terminar(self):
        self.terminada = True
        self.al_estado("Transmisión finalizada")
        if self.emisor.retransmisiones == 0:
            self.al_estado("Estado de enlace óptimo")
        total = self.emisor.enviadas + self.emisor.retransmisiones
        self.al_estado(f"Retransmisiones: {self.emisor.retransmisiones} de {total} tramas enviadas")

    def _enviar_datos(self, secuencia, datos):
        self.canal.enviar(trama.construir(trama.DATA, secuencia, datos))

    def _avisar_progreso(self):
        porcentaje = 100 * self.emisor.base // len(self.emisor.bloques)
        if porcentaje != self._progreso:
            self._progreso = porcentaje
            self.al_progreso(porcentaje)