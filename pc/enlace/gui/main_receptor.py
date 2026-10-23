import os
import sys
import time
import tkinter as tk

from pc.enlace import registro
from pc.enlace.gui.gui_receptor import RedesReceptorGUI
from pc.enlace.sesion_receptor import SesionReceptor
from pc.enlace.canal import crear_canal

# El puerto se abre antes de recibir el INICIO, así que baud y Hamming
# se fijan aquí y deben coincidir con los del emisor.
BAUD = 9600
HAMMING = True


class ReceptorApp:
    def __init__(self, root, canal):
        self.root = root
        self.gui = RedesReceptorGUI(root)
        self.datos = bytearray()
        self.guardado = False
        self.sesion = SesionReceptor(
            canal,
            al_estado=self.gui.log,
            al_progreso=self.gui.actualizar_progreso,
            al_datos=self.datos.extend,
            al_iniciar=self._al_iniciar,
        )
        self.gui.log("Esperando conexión entrante...")
        self._tick()

    def _al_iniciar(self, info):
        self.datos.clear()
        self.guardado = False
        self.gui.actualizar_progreso(0)
        self.gui.log(f"[SESIÓN] {info.tamano} bytes | {info.extension} | "
                     f"{info.baud} bps | W={info.W} J={info.J} | "
                     f"Hamming={'ON' if info.hamming else 'OFF'}")
        if info.baud != BAUD or info.hamming != HAMMING:
            self.gui.log(f"[AVISO] El receptor está en {BAUD} bps / "
                         f"Hamming={'ON' if HAMMING else 'OFF'}: no coincide con el emisor")

    def _tick(self):
        self.sesion.tick()
        if self.sesion.completa and not self.guardado:
            self._guardar()
        # sigue activo tras completar: si el último ACK se pierde, hay que responder
        self.root.after(5, self._tick)

    def _guardar(self):
        self.guardado = True
        os.makedirs("recibidos", exist_ok=True)
        ruta = os.path.join("recibidos",
                            f"recibido_{int(time.time())}{self.sesion.info.extension}")
        with open(ruta, "wb") as f:
            f.write(self.datos)
        self.gui.log(f"Archivo guardado en: {ruta}")


if __name__ == "__main__":
    registro.configurar("receptor", detallado="--debug" in sys.argv)
    root = tk.Tk()
    ReceptorApp(root, crear_canal(BAUD, HAMMING))
    root.mainloop()