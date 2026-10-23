from pc.enlace import control, trama
from pc.enlace.lector_tramas import LectorTramas
from pc.enlace.parametros import tasa_error_estimada
from pc.enlace.receptor import Receptor

TIPO_RESPUESTA = {"ACK": trama.ACK, "NAK": trama.NAK}


class SesionReceptor:
    """Une el Receptor con el canal. Quien la use llama a tick() cada pocos milisegundos.

    Espera el INICIO del emisor, crea el Receptor con esos parámetros y va
    entregando los datos en orden a al_datos. Conviene seguir llamando a tick()
    un rato después de completar, por si el último ACK se pierde y el emisor
    reenvía la última trama.
    """

    def __init__(self, canal, al_estado=print, al_progreso=lambda porcentaje: None,
                 al_datos=lambda datos: None, al_iniciar=lambda info: None):
        self.canal = canal
        self.al_estado = al_estado
        self.al_progreso = al_progreso
        self.al_datos = al_datos
        self.al_iniciar = al_iniciar
        self.lector = LectorTramas()

        self.receptor = None
        self.info = None
        self.entregados = 0          # bytes de archivo entregados hasta ahora
        self.completa = False
        self._progreso = -1
        self._anunciada_en_curso = False

    def tick(self):
        descartadas_antes = self.lector.descartadas
        tramas = self.lector.alimentar(self.canal.recibir(1024, 0))
        for _ in range(self.lector.descartadas - descartadas_antes):
            self._trama_danada()         # llegó sin final: cuenta como error de CRC
        for crudo in tramas:
            self._procesar(crudo)

    def _procesar(self, crudo):
        t = trama.parsear(crudo)
        if not t.crc_ok:
            self._trama_danada()
        elif t.tipo == trama.CONTROL:
            self._al_recibir_control(t.datos)
        elif t.tipo == trama.DATA and self.receptor is not None:
            if not self._anunciada_en_curso:
                self._anunciada_en_curso = True
                self.al_estado("Transmisión en curso...")
            self.receptor.recibir_trama(t.secuencia, t.datos, True)

    def _trama_danada(self):
        if self.receptor is not None and not self.completa:
            self.receptor.recibir_trama(0, b"", False)

    def _al_recibir_control(self, datos):
        info = control.leer_inicio(datos)
        if info is None:
            return
        if self.receptor is None or self.completa:
            self._abrir_sesion(info)
        # si el INICIO se repite (se perdió el ACEPTADO) solo se vuelve a confirmar
        self.canal.enviar(control.construir_aceptado())

    def _abrir_sesion(self, info):
        self.info = info
        self.receptor = Receptor(info.W, info.J, self._responder, self._entregar)
        self.entregados = 0
        self.completa = False
        self._progreso = -1
        self._anunciada_en_curso = False
        self.al_iniciar(info)
        self.al_estado("Inicio de transmisión...")

    def _responder(self, tipo, secuencia):
        self.canal.enviar(trama.construir(TIPO_RESPUESTA[tipo], secuencia))

    def _entregar(self, datos):
        self.entregados += len(datos)
        self.al_datos(datos)
        porcentaje = min(100, 100 * self.entregados // self.info.tamano)
        if porcentaje != self._progreso:
            self._progreso = porcentaje
            self.al_progreso(porcentaje)
        if self.entregados >= self.info.tamano and not self.completa:
            self._terminar()

    def _terminar(self):
        self.completa = True
        self.al_estado("Transmisión finalizada")
        if self.receptor.errores_crc == 0:
            self.al_estado("Estado de enlace óptimo")
        tasa = tasa_error_estimada(self.receptor.errores_crc, self.receptor.recibidas)
        self.al_estado(f"Tasa de error estimada: {tasa:05.2f} %")
