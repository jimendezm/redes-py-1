#include <AltSoftSerial.h>

// Pines fijos de AltSoftSerial en Uno/Nano: RX = D8, TX = D9.
AltSoftSerial enlace;

const long BAUD_ENLACE = 9600; 
const long BAUD_USB = 115200; 
const bool USAR_HAMMING = true;

// Poner en true SOLO para probar con el Monitor Serie. Con la PC conectada
// debe estar en false: el texto de depuracion se mezclaria con las tramas.
const bool DEPURACION = false;

// Si llego el nibble bajo y el alto no aparece en este tiempo, se perdio un byte
// en el cable: se descarta el nibble huerfano para recuperar la alineacion.
const unsigned long TIMEOUT_NIBBLE_MS = 10;

// ---- Contadores ----
uint32_t bytesRecibidos = 0; 
uint32_t errCorregidos = 0;
uint32_t errNoCorregibles = 0; 
uint32_t nibblesDescartados = 0;
unsigned long ultimoInforme = 0;

bool esperandoAlto = false;    
uint8_t nibbleBajo = 0;
unsigned long tUltimoByteEnlace = 0;

// ---- Hamming (8,4) ----
// Paridad par de un byte: devuelve 1 si hay cantidad impar de unos.
uint8_t paridad8(uint8_t x) {
  x ^= x >> 4;
  x ^= x >> 2;
  x ^= x >> 1;
  return x & 1;
}

// Formato del byte: bit0=p1, bit1=p2, bit2=d1, bit3=p4, bit4=d2, bit5=d3, bit6=d4, bit7=P
uint8_t hammingCodificar(uint8_t nibble) {
  uint8_t d1 = (nibble >> 0) & 1;
  uint8_t d2 = (nibble >> 1) & 1;
  uint8_t d3 = (nibble >> 2) & 1;
  uint8_t d4 = (nibble >> 3) & 1;

  uint8_t p1 = d1 ^ d2 ^ d4;
  uint8_t p2 = d1 ^ d3 ^ d4;
  uint8_t p4 = d2 ^ d3 ^ d4;

  uint8_t b = p1 | (p2 << 1) | (d1 << 2) | (p4 << 3) | (d2 << 4) | (d3 << 5) | (d4 << 6);
  b |= (paridad8(b) << 7);
  return b;
}

// Decodifica un byte de linea. Devuelve el nibble en *nibble y el estado:
//   0 = sin error, 1 = un error corregido, 2 = dos errores (no corregible).
uint8_t hammingDecodificar(uint8_t b, uint8_t *nibble) {
  uint8_t s1 = ((b >> 0) ^ (b >> 2) ^ (b >> 4) ^ (b >> 6)) & 1; 
  uint8_t s2 = ((b >> 1) ^ (b >> 2) ^ (b >> 5) ^ (b >> 6)) & 1;
  uint8_t s4 = ((b >> 3) ^ (b >> 4) ^ (b >> 5) ^ (b >> 6)) & 1;
  uint8_t sindrome = s1 | (s2 << 1) | (s4 << 2); 
  uint8_t paridadGlobal = paridad8(b);

  uint8_t estado;
  if (sindrome == 0 && paridadGlobal == 0) {
    estado = 0;   
  } else if (paridadGlobal == 1) {
    if (sindrome != 0) b ^= (1 << (sindrome - 1));
    estado = 1;
  } else {
    estado = 2;  
  }

  *nibble = ((b >> 2) & 1) | (((b >> 4) & 1) << 1) | (((b >> 5) & 1) << 2) | (((b >> 6) & 1) << 3);
  return estado;
}
// ---- Fin Hamming ----

// Con Hamming: 1 byte -> 2 bytes de linea
void enviarByte(uint8_t dato) {
  if (USAR_HAMMING) {
    enlace.write(hammingCodificar(dato & 0x0F));
    enlace.write(hammingCodificar(dato >> 4));
  } else {
    enlace.write(dato);
  }
}

// Procesa un byte que llego por el enlace y, cuando hay un byte completo, lo manda a la PC.
void procesarByteEnlace(uint8_t b) {
  tUltimoByteEnlace = millis();

  if (!USAR_HAMMING) {
    Serial.write(b);
    bytesRecibidos++;
    return;
  }

  uint8_t nibble;
  uint8_t estado = hammingDecodificar(b, &nibble);
  if (estado == 1) errCorregidos++;
  else if (estado == 2) errNoCorregibles++;

  if (!esperandoAlto) {
    nibbleBajo = nibble;
    esperandoAlto = true;
  } else {
    Serial.write((uint8_t)((nibble << 4) | nibbleBajo));
    bytesRecibidos++;
    esperandoAlto = false;
  }
}

void setup() {
  Serial.begin(BAUD_USB);       // USB hacia la PC (UART de hardware, D0/D1)
  enlace.begin(BAUD_ENLACE);    // Enlace hacia el Uno (D8/D9, 8N1)
  if (DEPURACION) Serial.println(F("[NANO] Receptor listo."));
}

void loop() {
  // Enlace -> PC (decodificando)
  while (enlace.available()) {
    procesarByteEnlace((uint8_t)enlace.read());
  }

  // PC -> Enlace (ACK/NAK de vuelta, codificando)
  while (Serial.available()) {
    enviarByte((uint8_t)Serial.read());
  }

  // Nibble huerfano: se perdio un byte, se descarta para realinear.
  if (esperandoAlto && (millis() - tUltimoByteEnlace > TIMEOUT_NIBBLE_MS)) {
    esperandoAlto = false;
    nibblesDescartados++;
  }

  if (DEPURACION && millis() - ultimoInforme >= 2000) {
    ultimoInforme = millis();
    Serial.print(F("[NANO] recibidos: "));       Serial.print(bytesRecibidos);
    Serial.print(F(" | corregidos: "));          Serial.print(errCorregidos);
    Serial.print(F(" | no corregibles: "));      Serial.print(errNoCorregibles);
    Serial.print(F(" | descartados: "));         Serial.println(nibblesDescartados);
  }
}
