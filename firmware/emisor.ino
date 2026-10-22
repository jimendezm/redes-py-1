#include <AltSoftSerial.h>

// Enlace hacia el otro Arduino. Usa pines fijos:
// RX = D8, TX = D9 (Timer1). No se puede cambiar.
AltSoftSerial enlace;

// ---- Parámetros (iguales en emisor y receptor) ----
const long BAUD_ENLACE   = 9600;   // 9600 o 19200
const bool USAR_HAMMING  = true;   // enviar el byte tal cual o con Hamming

uint32_t bytesEnviados = 0;        // contador de bytes de datos enviados
unsigned long ultimoInforme = 0;

// Paridad par de un byte: devuelve 1 si hay cantidad impar de unos.
uint8_t paridad8(uint8_t x) {
  x ^= x >> 4;
  x ^= x >> 2;
  x ^= x >> 1;
  return x & 1;
}

// Codifica nibble (4 bits) en byte de línea Hamming(8,4) extendido.
// Formato del byte: bit0=p1, bit1=p2, bit2=d1, bit3=p4, bit4=d2, bit5=d3, bit6=d4, bit7=P
uint8_t hammingCodificar(uint8_t nibble) {
  uint8_t d1 = (nibble >> 0) & 1;
  uint8_t d2 = (nibble >> 1) & 1;
  uint8_t d3 = (nibble >> 2) & 1;
  uint8_t d4 = (nibble >> 3) & 1;

  uint8_t p1 = d1 ^ d2 ^ d4;       // cubre posiciones 1,3,5,7
  uint8_t p2 = d1 ^ d3 ^ d4;       // cubre posiciones 2,3,6,7
  uint8_t p4 = d2 ^ d3 ^ d4;       // cubre posiciones 4,5,6,7

  // Se arman los bits 0..6 del código Hamming(7,4)
  uint8_t b = p1 | (p2 << 1) | (d1 << 2) | (p4 << 3) | (d2 << 4) | (d3 << 5) | (d4 << 6);

  // Bit 7: paridad global (la hace SECDED: corrige 1 error, detecta 2)
  b |= (paridad8(b) << 7);
  return b;
}

// Envía byte de datos por el enlace.
// Con Hamming: 1 byte -> 2 bytes de línea (primero el nibble bajo, luego el alto).
void enviarByte(uint8_t dato) {
  if (USAR_HAMMING) {
    enlace.write(hammingCodificar(dato & 0x0F));   // nibble bajo
    enlace.write(hammingCodificar(dato >> 4));     // nibble alto
  } else {
    enlace.write(dato);
  }
  bytesEnviados++;
}

void setup() {
  Serial.begin(115200);        // USB hacia la PC (UART de hardware, D0/D1)
  enlace.begin(BAUD_ENLACE);   // Enlace hacia el Nano (D8/D9, 8N1)
  Serial.println(F("[UNO] Emisor listo. Escriba datos en el Monitor Serie."));
}

void loop() {
  // Todo byte que llegue de la PC se envía por el enlace.
  while (Serial.available()) {
    enviarByte(Serial.read());
  }

  // Informe de estado cada 2 s
  if (millis() - ultimoInforme >= 2000) {
    ultimoInforme = millis();
    Serial.print(F("[UNO] bytes enviados: "));
    Serial.println(bytesEnviados);
  }
}