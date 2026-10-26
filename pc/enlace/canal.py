"""Canal para la capa de enlace.

    canal.enviar(bytes)
    canal.recibir(max_bytes, timeout)   # con timeout 0 no bloquea
    canal.ajustar_ritmo(baud, hamming)
    canal.cerrar()

La capa de enlace siempre ve bytes limpios. Dos modos, se elige con MODO:

    "red"     el cable lo hace la red. Sirve para probar el enlace SIN Arduinos:
              dos terminales en una PC, o una terminal en cada PC. Reproduce lo
              que harán los Arduinos (Hamming, retardo del baud, ruido opcional).
    "serial"  puerto USB hacia el Arduino (115200). El Hamming y el enlace entre
              Arduinos los hace el firmware.

Cómo conectar en modo "red":
    una sola PC      IP_REMOTA = ""  en las dos terminales. La primera que abre
                     escucha y la segunda se conecta (el orden no importa).
    dos PCs          PC receptora: IP_REMOTA = ""  (escucha, abrir primero).
                     PC emisora:   IP_REMOTA = "<IP de la receptora>".
"""
import os
import random
import socket
import time

MODO = "red"                 # "red" o "serial"

# ---------------------------------------------------------------- modo red
IP_REMOTA = ""              
PUERTO_TCP = 50007
HAMMING_CABLE = True         # igual que en el Arduino: es del cable, no de la GUI
VELOCIDAD = 1.0              # 1 = tarda lo mismo que el cable real; 10 = diez veces más rápido
PROB_PERDIDA = 0.0           # probabilidad de perder un envío completo (0 a 1)
PROB_ERROR_BYTE = 0.0        # probabilidad de dañar cada byte que sale al cable (0 a 1)
BITS_ERROR = 2               # bits que se invierten en un byte dañado (1 = Hamming lo corrige)

# ---------------------------------------------------------------- modo serial
PUERTO = None                # None = detectar solo; si hay varios, "COM3", etc.
BAUD_USB = 115200            # PC <-> Arduino (debe coincidir con Serial.begin del .ino)
TROZO = 32                   # bytes por escritura; el buffer de entrada del Arduino es de 64

# Si llega un byte de un par y el otro no aparece en este tiempo, se descarta
ESPERA_PAR = 0.05


# ---------------------------------------------------------------- Hamming (8,4)
# Bits 0..6 = posiciones 1..7 de Hamming(7,4): p1 p2 d1 p3 d2 d3 d4
# Bit 7 = paridad global (así también se detectan errores dobles).

def _codificar_nibble(n):
    d1, d2, d3, d4 = n & 1, (n >> 1) & 1, (n >> 2) & 1, (n >> 3) & 1
    p1 = d1 ^ d2 ^ d4
    p2 = d1 ^ d3 ^ d4
    p3 = d2 ^ d3 ^ d4
    byte = p1 | (p2 << 1) | (d1 << 2) | (p3 << 3) | (d2 << 4) | (d3 << 5) | (d4 << 6)
    paridad = bin(byte).count("1") & 1
    return byte | (paridad << 7)


def _decodificar_byte(b):
    """Devuelve el nibble. Corrige 1 bit; con 2 bits malos el resultado es
    basura y lo atrapa el CRC de la trama."""
    bit = [(b >> i) & 1 for i in range(8)]
    s1 = bit[0] ^ bit[2] ^ bit[4] ^ bit[6]
    s2 = bit[1] ^ bit[2] ^ bit[5] ^ bit[6]
    s3 = bit[3] ^ bit[4] ^ bit[5] ^ bit[6]
    sindrome = s1 | (s2 << 1) | (s3 << 2)
    paridad_global = sum(bit) & 1
    if paridad_global and sindrome:
        bit[sindrome - 1] ^= 1
    return bit[2] | (bit[4] << 1) | (bit[5] << 2) | (bit[6] << 3)


_TABLA_COD = [_codificar_nibble(n) for n in range(16)]
_TABLA_DEC = [_decodificar_byte(b) for b in range(256)]


def hamming_codificar(datos):
    salida = bytearray()
    for byte in datos:
        salida.append(_TABLA_COD[byte >> 4])
        salida.append(_TABLA_COD[byte & 0x0F])
    return bytes(salida)


# ---------------------------------------------------------------- modo red

class CanalRed:
    """Cable falso por TCP. Hace lo que harán los Arduinos: Hamming, retardo del
    baud y (opcional) ruido. El enlace de datos ni se entera."""

    def __init__(self, baud=9600):
        self.baud = baud
        self.hamming = HAMMING_CABLE
        self.conn = None
        self.server = None
        self.destino = None              # a dónde reconectar si somos el que se conecta
        self._prox_reintento = 0.0
        self.pendiente = []              # (instante de llegada, bytes) todavía "en el cable"
        self.libre_en = 0.0
        self._huerfano = None
        self._t_huerfano = 0.0
        self._conectar()

    def ajustar_ritmo(self, baud, hamming=None):
        # el Hamming es del cable (constante), solo el baud se ajusta
        self.baud = baud

    def _conectar(self):
        if IP_REMOTA:
            self.destino = (IP_REMOTA, PUERTO_TCP)
            self.conn = socket.create_connection(self.destino, timeout=5)
            self.conn.setblocking(False)
            return
        srv = socket.socket()
        if os.name != "nt":
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind(("0.0.0.0", PUERTO_TCP))
            srv.listen(1)
            srv.setblocking(False)
            self.server = srv
        except OSError:
            # ya hay alguien escuchando en esta PC: nos conectamos a él
            srv.close()
            self.destino = ("127.0.0.1", PUERTO_TCP)
            self.conn = socket.create_connection(self.destino, timeout=5)
            self.conn.setblocking(False)

    def _aceptar(self):
        if self.conn is not None:
            return
        if self.server is not None:
            try:
                self.conn, _ = self.server.accept()
                self.conn.setblocking(False)
            except BlockingIOError:
                pass
        elif self.destino is not None and time.monotonic() >= self._prox_reintento:
            # el otro lado cerró (terminó un envío): reintentar sin bloquear mucho
            self._prox_reintento = time.monotonic() + 1.0
            try:
                self.conn = socket.create_connection(self.destino, timeout=0.2)
                self.conn.setblocking(False)
            except OSError:
                pass

    def enviar(self, datos):
        crudo = hamming_codificar(datos) if self.hamming else bytes(datos)
        if random.random() < PROB_PERDIDA:
            return
        if PROB_ERROR_BYTE > 0:
            crudo = bytearray(crudo)
            for i in range(len(crudo)):
                if random.random() < PROB_ERROR_BYTE:
                    for bit in random.sample(range(8), BITS_ERROR):
                        crudo[i] ^= 1 << bit
            crudo = bytes(crudo)

        # el cable tarda lo que tardaría a este baud (10 bits por byte)
        ahora = time.monotonic()
        llega = max(ahora, self.libre_en) + len(crudo) * 10 / self.baud / VELOCIDAD
        self.libre_en = llega
        self.pendiente.append((llega, crudo))

    def _vaciar(self):
        self._aceptar()
        ahora = time.monotonic()
        while self.pendiente and self.pendiente[0][0] <= ahora:
            _, crudo = self.pendiente.pop(0)
            if self.conn is not None:        # sin nadie al otro lado se pierde
                try:
                    self.conn.sendall(crudo)
                except (BlockingIOError, OSError):
                    pass

    def _leer(self, n):
        if self.conn is None:
            return b""
        try:
            datos = self.conn.recv(n)
            if datos:
                return datos
            self.conn.close()                # el otro lado cerró
            self.conn = None
        except (BlockingIOError, InterruptedError):
            pass
        except OSError:
            self.conn = None
        return b""

    def recibir(self, max_bytes, timeout=0):
        limite = time.monotonic() + timeout
        while True:
            self._vaciar()
            crudo = self._leer(max_bytes * (2 if self.hamming else 1))
            if crudo or time.monotonic() >= limite:
                break
            time.sleep(0.001)
        return self._decodificar(crudo) if self.hamming else crudo

    def _decodificar(self, crudo):
        ahora = time.monotonic()
        if self._huerfano is not None and not crudo and ahora - self._t_huerfano > ESPERA_PAR:
            self._huerfano = None            # el otro byte del par nunca llegó
        if not crudo:
            return b""
        if self._huerfano is not None:
            crudo = bytes([self._huerfano]) + crudo
            self._huerfano = None
        if len(crudo) % 2:
            self._huerfano = crudo[-1]
            self._t_huerfano = ahora
            crudo = crudo[:-1]
        salida = bytearray()
        for i in range(0, len(crudo), 2):
            salida.append((_TABLA_DEC[crudo[i]] << 4) | _TABLA_DEC[crudo[i + 1]])
        return bytes(salida)

    def cerrar(self):
        for s in (self.conn, self.server):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass
        self.conn = self.server = None


# ---------------------------------------------------------------- modo serial

def _buscar_puerto():
    from serial.tools import list_ports
    puertos = [p.device for p in list_ports.comports()]
    if len(puertos) == 1:
        return puertos[0]
    if not puertos:
        raise RuntimeError("No se detectó ningún puerto serial. ¿Está conectado el Arduino?")
    raise RuntimeError(f"Hay varios puertos ({', '.join(puertos)}). Fija PUERTO en canal.py.")


class CanalSerial:
    """La PC habla con SU Arduino por USB con bytes limpios; el Hamming y el
    enlace entre Arduinos los hace el firmware."""

    def __init__(self, puerto=None, baud_enlace=9600, hamming=True):
        import serial                    # pip install pyserial
        puerto = puerto or PUERTO or _buscar_puerto()
        self.ser = serial.Serial(puerto, BAUD_USB, timeout=0, write_timeout=5)
        time.sleep(2)                    # muchos Arduino se reinician al abrir el puerto
        self.ser.reset_input_buffer()
        self.salida = bytearray()
        self.libre_en = 0.0
        self.ajustar_ritmo(baud_enlace, hamming)

    def ajustar_ritmo(self, baud, hamming=True):
        """Ritmo al que el Arduino saca bytes de datos al enlace."""
        self.baud = baud
        self.hamming = hamming
        self.bytes_por_s = baud / 10 / (2 if hamming else 1)

    def enviar(self, datos):
        self.salida.extend(datos)
        self._bombear()

    def _bombear(self):
        # el Arduino no saca al enlace tan rápido como llega por USB:
        # se le da de a trozos y al ritmo del enlace para que no desborde
        if not self.salida or time.monotonic() < self.libre_en:
            return
        trozo = bytes(self.salida[:TROZO])
        del self.salida[:TROZO]
        self.ser.write(trozo)
        self.libre_en = time.monotonic() + len(trozo) / self.bytes_por_s

    def recibir(self, max_bytes, timeout=0):
        limite = time.monotonic() + timeout
        while True:
            self._bombear()
            disponibles = self.ser.in_waiting
            if disponibles:
                return self.ser.read(min(disponibles, max_bytes))
            if time.monotonic() >= limite:
                return b""
            time.sleep(0.001)

    def cerrar(self):
        self.ser.close()


def crear_canal(baud=9600, hamming=True, puerto=None):
    if MODO == "red":
        return CanalRed(baud)
    return CanalSerial(puerto, baud, hamming)