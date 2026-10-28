"""Tramas CONTROL: el emisor abre la sesión con INICIO y el receptor responde ACEPTADO.

Van dentro de una trama de tipo CONTROL (trama.CONTROL), en el campo de datos:
    INICIO:   [1] W(1) J(1) payload(2) baud(4) hamming(1) tamaño(4)
              len_ext(1) extensión  len_nombre(1) nombre
    ACEPTADO: [2]
Todos los números van en big endian. J viaja en el INICIO para que los dos
lados usen el mismo valor sin tener que calcularlo por separado.
La extensión va en ASCII y el nombre del archivo en UTF-8.
"""
from collections import namedtuple

from pc.enlace.formato import trama

INICIO, ACEPTADO = 1, 2
LARGO_FIJO_INICIO = 15
MAX_NOMBRE = 255

Inicio = namedtuple("Inicio", "W J payload baud hamming tamano extension nombre")


def _nombre_a_bytes(nombre):
    # se corta en 255 bytes sin dejar un carácter UTF-8 a medias
    crudo = nombre.encode("utf-8")[:MAX_NOMBRE]
    return crudo.decode("utf-8", errors="ignore").encode("utf-8")


def construir_inicio(W, J, payload, baud, hamming, tamano, extension, nombre=""):
    ext = extension.encode("ascii")
    nom = _nombre_a_bytes(nombre)
    datos = (bytes([INICIO, W, J])
             + payload.to_bytes(2, "big")
             + baud.to_bytes(4, "big")
             + bytes([1 if hamming else 0])
             + tamano.to_bytes(4, "big")
             + bytes([len(ext)]) + ext
             + bytes([len(nom)]) + nom)
    return trama.construir(trama.CONTROL, 0, datos)


def construir_aceptado():
    return trama.construir(trama.CONTROL, 0, bytes([ACEPTADO]))


def es_aceptado(datos):
    return datos == bytes([ACEPTADO])


def leer_inicio(datos):
    """Devuelve un Inicio, o None si los datos no son un INICIO bien formado."""
    if len(datos) < LARGO_FIJO_INICIO or datos[0] != INICIO:
        return None
    largo_ext = datos[14]
    pos_nombre = LARGO_FIJO_INICIO + largo_ext        # nomb
    if len(datos) < pos_nombre + 1:
        return None
    largo_nombre = datos[pos_nombre]
    if len(datos) != pos_nombre + 1 + largo_nombre:
        return None
    return Inicio(
        W=datos[1],
        J=datos[2],
        payload=int.from_bytes(datos[3:5], "big"),
        baud=int.from_bytes(datos[5:9], "big"),
        hamming=bool(datos[9]),
        tamano=int.from_bytes(datos[10:14], "big"),
        extension=datos[15:pos_nombre].decode("ascii", errors="replace"),
        nombre=datos[pos_nombre + 1:].decode("utf-8", errors="replace"),
    )