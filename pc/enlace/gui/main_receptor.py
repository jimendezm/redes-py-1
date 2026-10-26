import os
import sys
import time
import tkinter as tk
from tkinter import messagebox

from pc.enlace.gui import registro
from pc.enlace.gui.gui_receptor import RedesReceptorGUI
from pc.enlace.sesion.sesion_receptor import SesionReceptor
from pc.enlace.canal import crear_canal


class ReceptorApp:
    """Une la ventana con la capa de enlace. Abre el canal al arrancar y espera
    el INICIO del emisor: W, J, payload, baud, Hamming, tamaño y extensión
    llegan ahí, no se configuran en el receptor."""

    def __init__(self, root):
        self.root = root
        self.gui = RedesReceptorGUI(root)
        self.datos = bytearray()
        self.guardado = False
        self.canal = None
        self.sesion = None
        self.root.protocol("WM_DELETE_WINDOW", self._cerrar)

        try:
            self.canal = crear_canal()
        except Exception as e:
            self.gui.log(f"[ERROR] No se pudo abrir el canal: {e}")
            messagebox.showerror("Error de canal", str(e))
            return

        self.sesion = SesionReceptor(
            self.canal,
            al_estado=self.gui.log,
            al_progreso=self.gui.actualizar_progreso,
            al_datos=self._al_datos,
            al_iniciar=self._al_iniciar,
        )
        self.gui.log("Esperando conexión entrante...")
        self._tick()

    def _al_iniciar(self, info):
        self.datos.clear()
        self.guardado = False
        self.gui.actualizar_progreso(0)
        # el ritmo de envío de ACK/NAK se ajusta con el baud y Hamming del INICIO
        self.canal.ajustar_ritmo(info.baud, info.hamming)
        self.gui.mostrar_sesion(
            tamano=info.tamano, extension=info.extension, baud=info.baud,
            hamming=info.hamming, W=info.W, J=info.J, payload=info.payload,
        )
        self.gui.log(f"[SESIÓN] Parámetros recibidos del emisor: {info.tamano} bytes, "
                     f"{info.extension}")

    def _al_datos(self, datos):
        self.datos.extend(datos)
        self.gui.actualizar_recibido(len(self.datos), self.sesion.info.tamano)

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

    def _cerrar(self):
        if self.canal is not None:
            self.canal.cerrar()
        self.root.destroy()


if __name__ == "__main__":
    registro.configurar("receptor", detallado="--debug" in sys.argv)
    root = tk.Tk()
    ReceptorApp(root)
    root.mainloop()