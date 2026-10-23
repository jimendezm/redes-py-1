"""Canal para la capa de enlace.

Lo usan SesionEmisor y SesionReceptor:
    canal.enviar(bytes)
    canal.recibir(max_bytes, timeout)   # con timeout 0 no bloquea

Dos modos, se elige con MODO:
    "emulado"  cable falso por localhost (las dos ventanas en la misma PC, sin Arduino)
    "serial"   puerto serial real

Con Hamming activado cada byte sale como dos bytes por el cable (uno por
nibble) y al recibir se decodifica y corrige 1 bit por byte. La capa de
enlace siempre ve bytes limpios.
"""
import os
import random
import socket
import time

MODO = "emulado"            # "emulado" o "serial"

# ---- modo serial
PUERTO = "COM3"             # puerto de ESTA PC

# ---- modo emulado
HOST, PUERTO_TCP = "127.0.0.1", 50007
VELOCIDAD = 1.0             # 1 = tarda lo mismo que el cable real; 10 = diez veces más rápido
PROB_PERDIDA = 0.0          # probabilidad de que se pierda una trama completa (0 a 1)
PROB_ERROR_BYTE = 0.0       # probabilidad de dañar cada byte que sale al cable (0 a 1)
BITS_ERROR = 2              # bits que se invierten en un byte dañado (con 1 el Hamming lo corrige)

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
    bit = [(b >> i) & 1 for i in range(8)]       # bit[0] = posición 1
    s1 = bit[0] ^ bit[2] ^ bit[4] ^ bit[6]
    s2 = bit[1] ^ bit[2] ^ bit[5] ^ bit[6]
    s3 = bit[3] ^ bit[4] ^ bit[5] ^ bit[6]
    sindrome = s1 | (s2 << 1) | (s3 << 2)
    paridad_global = sum(bit) & 1
    if paridad_global and sindrome:
        bit[sindrome - 1] ^= 1                   # un bit malo, se corrige
    return bit[2] | (bit[4] << 1) | (bit[5] << 2) | (bit[6] << 3)


_TABLA_COD = [_codificar_nibble(n) for n in range(16)]
_TABLA_DEC = [_decodificar_byte(b) for b in range(256)]


def hamming_codificar(datos):
    salida = bytearray()
    for byte in datos:
        salida.append(_TABLA_COD[byte >> 4])
        salida.append(_TABLA_COD[byte & 0x0F])
    return bytes(salida)


# ---------------------------------------------------------------- base

class _CanalBase:
    def __init__(self, hamming):
        self.hamming = hamming
        self._huerfano = None        # primer byte de un par que aún no completa
        self._t_huerfano = 0.0

    def enviar(self, datos):
        crudo = hamming_codificar(datos) if self.hamming else bytes(datos)
        self._escribir(crudo)

    def recibir(self, max_bytes, timeout=0):
        crudo = self._leer(max_bytes * (2 if self.hamming else 1), timeout)
        return self._decodificar(crudo) if self.hamming else crudo

    def _decodificar(self, crudo):
        ahora = time.monotonic()
        if self._huerfano is not None and not crudo and ahora - self._t_huerfano > ESPERA_PAR:
            self._huerfano = None        # el otro byte del par nunca llegó
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


# ---------------------------------------------------------------- serial real

class CanalSerial(_CanalBase):
    def __init__(self, puerto, baud, hamming):
        super().__init__(hamming)
        import serial   # pip install pyserial
        self.ser = serial.Serial(puerto, baud, timeout=0, write_timeout=5)
        # al abrir el puerto muchos Arduino se reinician: esperar y limpiar
        time.sleep(2)
        self.ser.reset_input_buffer()

    def _escribir(self, crudo):
        self.ser.write(crudo)

    def _leer(self, n, timeout):
        limite = time.monotonic() + timeout
        while True:
            disponibles = self.ser.in_waiting
            if disponibles or time.monotonic() >= limite:
                break
            time.sleep(0.001)
        return self.ser.read(min(disponibles, n))

    def cerrar(self):
        self.ser.close()


# ---------------------------------------------------------------- cable emulado

class CanalEmulado(_CanalBase):
    """Cable falso por TCP en localhost. No importa cuál programa se abre primero:
    el primero queda escuchando y el segundo se conecta."""

    def __init__(self, baud, hamming):
        super().__init__(hamming)
        self.baud = baud
        self.conn = None
        self.server = None
        self.pendiente = []          # (instante de llegada, bytes) todavía "en el cable"
        self.libre_en = 0.0          # cuándo se desocupa el cable para la próxima trama
        self._conectar()

    def _conectar(self):
        srv = socket.socket()
        if os.name != "nt":
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind((HOST, PUERTO_TCP))
            srv.listen(1)
            srv.setblocking(False)
            self.server = srv
        except OSError:
            srv.close()
            self.conn = socket.create_connection((HOST, PUERTO_TCP), timeout=5)
            self.conn.setblocking(False)

    def _aceptar(self):
        if self.conn is None and self.server is not None:
            try:
                self.conn, _ = self.server.accept()
                self.conn.setblocking(False)
            except BlockingIOError:
                pass

    def _escribir(self, crudo):
        if random.random() < PROB_PERDIDA:
            return                                   # trama perdida
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
            if self.conn is not None:                # sin nadie al otro lado se pierde
                try:
                    self.conn.sendall(crudo)
                except (BlockingIOError, OSError):
                    pass

    def _leer(self, n, timeout):
        limite = time.monotonic() + timeout
        while True:
            self._vaciar()
            if self.conn is not None:
                try:
                    datos = self.conn.recv(n)
                    if datos:
                        return datos
                    self.conn = None                 # el otro lado cerró
                except (BlockingIOError, ConnectionResetError, OSError):
                    pass
            if time.monotonic() >= limite:
                return b""
            time.sleep(0.001)


def crear_canal(baud, hamming, puerto=None):
    if MODO == "emulado":
        return CanalEmulado(baud, hamming)
    return CanalSerial(puerto or PUERTO, baud, hamming)