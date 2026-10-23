from pc.enlace.stuffing import EOF, SOF


class LectorTramas:
    """Junta los bytes que llegan del canal y devuelve tramas completas (SOF a EOF).

    El stuffing garantiza que SOF y EOF no aparecen dentro de una trama,
    así que basta con buscarlos.
    """

    def __init__(self):
        self.pendiente = bytearray()
        self.descartadas = 0   # tramas que perdieron su EOF antes de que empezara otra

    def alimentar(self, datos):
        self.pendiente.extend(datos)
        tramas = []
        while True:
            inicio = self.pendiente.find(SOF)
            if inicio < 0:
                self.pendiente.clear()      # solo ruido, sin ningún SOF
                break
            del self.pendiente[:inicio]

            fin = self.pendiente.find(EOF)
            otro_sof = self.pendiente.find(SOF, 1)
            if otro_sof != -1 and (fin == -1 or otro_sof < fin):
                # llegó un SOF antes de cerrar: la trama anterior perdió su final
                del self.pendiente[:otro_sof]
                self.descartadas += 1
                continue
            if fin == -1:
                break                        # la trama todavía no termina de llegar

            tramas.append(bytes(self.pendiente[:fin + 1]))
            del self.pendiente[:fin + 1]
        return tramas
