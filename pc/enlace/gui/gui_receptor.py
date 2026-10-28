import tkinter as tk
from tkinter import ttk


class RedesReceptorGUI:
    """Solo dibuja. No conoce el canal ni el protocolo: quien la use le pasa
    los datos con mostrar_sesion(), actualizar_recibido(), log() y
    actualizar_progreso()."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("File Transfer Protocol — Receptor (Grupo 02)")
        self.root.geometry("720x590")
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

        # TARJETA: información de la sesión (lo que manda el emisor en el INICIO)
        card_info = tk.Frame(self.root, bg=self.COLOR_CARD,
                             highlightbackground=self.COLOR_CARD_BORDER, highlightthickness=1)
        card_info.pack(fill="x", padx=25, pady=8)

        tk.Label(card_info, text="INFORMACIÓN DE LA SESIÓN (enviada por el emisor)",
                 font=("Segoe UI", 9, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_ACCENT
                 ).pack(anchor="w", padx=15, pady=(12, 8))

        grid = tk.Frame(card_info, bg=self.COLOR_CARD)
        grid.pack(fill="x", padx=15, pady=(0, 12))

        self.campos = {}

        # el nombre del archivo ocupa toda la fila de arriba
        tk.Label(grid, text="Nombre del archivo:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT_MUTED,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=3)
        lbl_nombre = tk.Label(grid, text="—", bg=self.COLOR_CARD, fg=self.COLOR_TEXT,
                              font=("Segoe UI", 9, "bold"))
        lbl_nombre.grid(row=0, column=1, columnspan=3, sticky="w", padx=(8, 0), pady=3)
        self.campos["nombre"] = lbl_nombre

        etiquetas = [
            ("tamano", "Tamaño del archivo:"), ("extension", "Formato:"),
            ("tramas", "Total de tramas:"), ("recibido", "Recibido:"),
            ("baud", "Velocidad (baud):"), ("hamming", "Hamming (8,4):"),
            ("payload", "Carga útil (payload):"), ("ventana", "Ventana (W) / Buffer (J):"),
        ]
        for i, (clave, texto) in enumerate(etiquetas):
            fila, col = i // 2 + 1, (i % 2) * 2
            tk.Label(grid, text=texto, bg=self.COLOR_CARD, fg=self.COLOR_TEXT_MUTED,
                     font=("Segoe UI", 9)).grid(row=fila, column=col, sticky="w", pady=3)
            lbl = tk.Label(grid, text="—", bg=self.COLOR_CARD, fg=self.COLOR_TEXT,
                           font=("Segoe UI", 9, "bold"))
            lbl.grid(row=fila, column=col + 1, sticky="w", padx=(8, 30), pady=3)
            self.campos[clave] = lbl

        # TARJETA: monitor y consola
        card_monitor = tk.Frame(self.root, bg=self.COLOR_CARD,
                                highlightbackground=self.COLOR_CARD_BORDER, highlightthickness=1)
        card_monitor.pack(fill="both", expand=True, padx=25, pady=(8, 25))

        tk.Label(card_monitor, text="MONITOR DE ESTADO DEL ENLACE (ESCUCHANDO...)",
                 font=("Segoe UI", 9, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_ACCENT
                 ).pack(anchor="w", padx=15, pady=(12, 6))

        self.progress_bar = ttk.Progressbar(card_monitor, orient="horizontal", mode="determinate",
                                            style="Turquoise.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", padx=15, pady=(0, 8))

        self.txt_log = tk.Text(card_monitor, bg=self.COLOR_LOG_BG, fg=self.COLOR_LOG_FG,
                               selectbackground=self.COLOR_ACCENT, selectforeground="#000000",
                               font=("Consolas", 9), bd=1, relief="solid", state="disabled")
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=(0, 12))

    # ------------------------------------------------------------ API pública

    @staticmethod
    def _formatear_bytes(n: int) -> str:
        if n >= 1024 * 1024:
            return f"{n / (1024 * 1024):.2f} MB ({n} B)"
        if n >= 1024:
            return f"{n / 1024:.1f} KB ({n} B)"
        return f"{n} B"

    def mostrar_sesion(self, tamano, extension, baud, hamming, W, J, payload, nombre=""):
        """Rellena la tarjeta con lo que llegó en el INICIO."""
        tramas = -(-tamano // payload) if payload else 0     # división hacia arriba
        if len(nombre) > 55:                                 # que no se salga de la ventana
            nombre = nombre[:52] + "..."
        self.campos["nombre"].config(text=nombre or "(sin nombre)")
        self.campos["tamano"].config(text=self._formatear_bytes(tamano))
        self.campos["extension"].config(text=extension.upper() or "—")
        self.campos["tramas"].config(text=str(tramas))
        self.campos["recibido"].config(text=f"0 B de {self._formatear_bytes(tamano)}")
        self.campos["baud"].config(text=f"{baud} bps")
        self.campos["hamming"].config(text="ACTIVADO" if hamming else "DESACTIVADO")
        self.campos["payload"].config(text=f"{payload} B")
        self.campos["ventana"].config(text=f"W={W}  /  J={J}")

    def actualizar_recibido(self, recibidos, tamano):
        self.campos["recibido"].config(
            text=f"{self._formatear_bytes(recibidos)} de {self._formatear_bytes(tamano)}")

    def log(self, mensaje: str):
        self.txt_log.config(state="normal")
        self.txt_log.insert(tk.END, f"{mensaje}\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state="disabled")

    def actualizar_progreso(self, porcentaje: float):
        self.progress_bar['value'] = porcentaje
        self.root.update_idletasks()