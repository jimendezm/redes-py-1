import tkinter as tk
from tkinter import ttk

class RedesReceptorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("File Transfer Protocol — Receptor (Grupo 02)")
        self.root.geometry("720x400")
        self.root.resizable(False, False)

        # Paleta de Colores
        self.COLOR_BG = "#12181f"
        self.COLOR_CARD = "#1a232e"
        self.COLOR_CARD_BORDER = "#253342"
        self.COLOR_ACCENT = "#00bcd4"
        self.COLOR_TEXT = "#e1e6ed"
        self.COLOR_TEXT_MUTED = "#8295a8"
        self.COLOR_LOG_BG = "#0d1117"
        self.COLOR_LOG_FG = "#38ef7d"

        self.root.configure(bg=self.COLOR_BG)
        self._configurar_estilos()
        self._crear_interfaz()

    def _configurar_estilos(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Turquoise.Horizontal.TProgressbar",
                        troughcolor=self.COLOR_LOG_BG,
                        background=self.COLOR_ACCENT,
                        bordercolor=self.COLOR_CARD_BORDER,
                        thickness=12)

    def _crear_interfaz(self):
        # Header 
        header_frame = tk.Frame(self.root, bg=self.COLOR_BG)
        header_frame.pack(fill="x", padx=25, pady=(20, 10))

        tk.Label(header_frame, text="📡 SISTEMA DE RECEPCIÓN DE ARCHIVOS P2P",
                 font=("Segoe UI", 12, "bold"), bg=self.COLOR_BG, fg=self.COLOR_ACCENT).pack(anchor="w")
        tk.Label(header_frame, text="Módulo Receptor — Monitoreo de Enlace y Reensamblaje",
                 font=("Segoe UI", 9), bg=self.COLOR_BG, fg=self.COLOR_TEXT_MUTED).pack(anchor="w")

        # TARJETA ÚNICA: Monitor y Consola de Estado
        card_monitor = tk.Frame(self.root, bg=self.COLOR_CARD, highlightbackground=self.COLOR_CARD_BORDER, highlightthickness=1)
        card_monitor.pack(fill="both", expand=True, padx=25, pady=(8, 25))

        tk.Label(card_monitor, text="MONITOR DE ESTADO DEL ENLACE (ESCUCHANDO...)",
                 font=("Segoe UI", 9, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_ACCENT).pack(anchor="w", padx=15, pady=(12, 6))

        # Barra de progreso
        self.progress_bar = ttk.Progressbar(card_monitor, orient="horizontal", mode="determinate", style="Turquoise.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", padx=15, pady=(0, 8))

        # Consola estilo Terminal / Logs
        self.txt_log = tk.Text(card_monitor, bg=self.COLOR_LOG_BG, fg=self.COLOR_LOG_FG,
                               selectbackground=self.COLOR_ACCENT, selectforeground="#000000",
                               font=("Consolas", 9), bd=1, relief="solid", state="disabled")
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=(0, 12))

    def log(self, mensaje: str):
        """Método público para que la capa de enlace imprima aquí"""
        self.txt_log.config(state="normal")
        self.txt_log.insert(tk.END, f"{mensaje}\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state="disabled")

    def actualizar_progreso(self, porcentaje: float):
        """Actualiza la barra de progreso (0 a 100)"""
        self.progress_bar['value'] = porcentaje
        self.root.update_idletasks()

if __name__ == "__main__":
    root = tk.Tk()
    app = RedesReceptorGUI(root)
    app.log("Esperando conexión entrante...")
    root.mainloop()
