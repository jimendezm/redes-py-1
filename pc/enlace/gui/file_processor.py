import os
from typing import List, Dict, Any, Tuple

class FileProcessor:
    """
    Módulo de Capas Superiores: Lector, procesador de extensiones
    y fragmentador de archivos.
    """
    FORMATOS_PERMITIDOS = {'.pdf', '.txt', '.png'}

    def __init__(self, filepath: str, payload_size: int):
        self.filepath = filepath
        self.payload_size = payload_size  # 500 o 900 bytes
        self.filename = os.path.basename(filepath)
        self.file_extension = os.path.splitext(filepath)[1].lower()
        self.file_size_bytes = 0
        self.raw_bytes = b''
        self.fragments: List[bytes] = []

    def validar_y_cargar(self) -> Tuple[bool, str]:
        """
        Valida que el archivo exista, tenga una extensión permitida y lee su contenido binario.
        """
        if not os.path.exists(self.filepath):
            return False, f"El archivo '{self.filepath}' no existe."

        if self.file_extension not in self.FORMATOS_PERMITIDOS:
            return False, f"Extensión no permitida ({self.file_extension}). Solo se admiten PDF, TXT y PNG."

        try:
            with open(self.filepath, 'rb') as f:
                self.raw_bytes = f.read()
            self.file_size_bytes = len(self.raw_bytes)
            
            if self.file_size_bytes == 0:
                return False, "El archivo seleccionado está vacío."

            return True, "Archivo cargado correctamente."
        except Exception as e:
            return False, f"Error al leer el archivo: {str(e)}"

    def fragmentar(self) -> List[bytes]:
        """
        Divide la secuencia de bytes del archivo en fragmentos (bloques)
        del tamaño especificado por payload_size (500 o 900 bytes).
        """
        self.fragments = [
            self.raw_bytes[i:i + self.payload_size]
            for i in range(0, self.file_size_bytes, self.payload_size)
        ]
        return self.fragments

    def obtener_resumen_sesion(self) -> Dict[str, Any]:
        """
        Retorna la metadata de la sesión lista para pasarse a la Capa de Enlace.
        """
        return {
            "nombre_archivo": self.filename,
            "extension": self.file_extension,
            "tamano_total_bytes": self.file_size_bytes,
            "tamano_payload": self.payload_size,
            "total_fragmentos": len(self.fragments),
            "fragmentos": self.fragments
        }