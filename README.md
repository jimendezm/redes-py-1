# Proyecto 1 - IC-7602 Redes (Grupo 2)

Repositorio: https://github.com/jimendezm/redes-py-1

Sistema de transferencia de archivos (PDF, TXT, PNG) entre dos terminales sobre un
enlace de cobre UTP punto a punto Full Duplex, con Arduino Uno y Arduino Nano.
Implementa ventana deslizante (Go-Back-N con búfer de reordenamiento J), CRC-16-CCITT
en la capa de enlace y Hamming (8,4) en la capa física.

- Primera etapa (diseño): informe entregado.
- Segunda etapa (implementación): entrega el **lunes 2 de noviembre de 2026**, antes de la clase.

---

## 1. Idea general

Cada terminal = **una PC + un Arduino**. La PC hace casi todo el trabajo; el Arduino
solo sirve de puente entre el USB y el cable.

```
 TERMINAL 1                                              TERMINAL 2
┌────────────────────┐                              ┌────────────────────┐
│ PC (Python)        │                              │ PC (Python)        │
│  GUI               │                              │  GUI               │
│  Aplicación        │                              │  Aplicación        │
│  Enlace de datos   │                              │  Enlace de datos   │
└──────┬─────────────┘                              └─────────────┬──────┘
       │ USB (puerto COM)                          USB (puerto COM) │
┌──────┴─────────────┐        cable UTP 8-10 m       ┌─────────────┴──────┐
│ Arduino Uno (C++)  │ D9 (TX) ───────────► D8 (RX)  │ Arduino Nano (C++) │
│  puente + Hamming  │ D8 (RX) ◄─────────── D9 (TX)  │  puente + Hamming  │
└────────────────────┘ GND ───────────────── GND     └────────────────────┘
```

El mismo programa de PC actúa como **emisor y receptor** (el enlace es Full Duplex).
Se ejecuta una instancia por terminal.

### Reparto de responsabilidades

| Dónde | Qué hace |
|---|---|
| **PC** | GUI, lectura y fragmentación del archivo, armado de tramas, CRC, byte stuffing, ventana deslizante, temporizador, retransmisión, búfer J, ACK/NAK, reensamblado, estadísticas |
| **Arduino** | Puente USB ↔ UART (pines D8/D9) y codec Hamming (8,4). No guarda tramas completas (solo 2 KB de RAM) |

### Flujo de un archivo

```
Emisor:   archivo → bytes → bloques (500/900 B) → trama (CRC + stuffing) → ventana
          → USB → Arduino → [Hamming] → TX → cable
Receptor: RX → [decodifica Hamming] → Arduino → USB → quitar stuffing → verificar CRC
          → clasificar secuencia (esperada / adelantada / repetida) → entrega ordenada
          → reensamblador → archivo
          └─► ACK / NAK por el camino inverso
```

---

## 2. Estructura del repositorio

```
redes-py-1/
├── README.md
├── requirements.txt          # pyserial, pytest
├── docs/
│   └── trama.md              # CONTRATO: formato de trama, Canal, eventos
├── pc/
│   ├── main.py               # punto de entrada (--puerto COM3 | --simulado)
│   ├── eventos.py            # eventos hacia la GUI: estado, progreso, tasa_error
│   ├── canal/                # lo que hay "debajo" del enlace
│   │   ├── base.py           #   interfaz Canal (enviar / recibir / cerrar)
│   │   ├── serial_canal.py   #   canal real: puerto serial hacia el Arduino
│   │   └── simulado.py       #   canal en memoria con pérdida y corrupción
│   ├── enlace/               # capa de enlace de datos
│   │   ├── crc.py            #   CRC-16-CCITT
│   │   ├── stuffing.py       #   byte stuffing
│   │   ├── trama.py          #   construir / parsear tramas DATA, ACK, NAK
│   │   └── (pendiente)       #   emisor.py (ventana, timer, J), receptor.py
│   ├── aplicacion/           # capas superiores (pendiente)
│   │                         #   lector, fragmentador, reensamblador, escritor
│   ├── gui/                  # interfaz y monitor (pendiente)
│   └── tests/                # pytest
├── firmware/                 # código Arduino (C/C++), pendiente
│   ├── eco/                  #   sketch de prueba de conexión
│   └── puente/               #   puente USB↔UART + Hamming
└── scripts/
    └── eco.py                # prueba rápida PC ↔ Arduino
```


---

## 3. Contratos entre módulos

Todo está detallado en `docs/trama.md`. Resumen:

1. **Trama:** `SOF 0x7E | Control 1B | Longitud 2B | Datos 0-900B | CRC-16 2B | EOF 0x7F`.
   El CRC cubre Control + Longitud + Datos; el stuffing se aplica después del CRC.
2. **Canal:** `enviar(bytes)`, `recibir(max_bytes, timeout) -> bytes`, `cerrar()`.
3. **Eventos a la GUI:** `estado(texto)`, `progreso(%)`, `tasa_error(valor)`.
   La GUI solo escucha estos eventos, así que se puede desarrollar con datos falsos.

Si alguien necesita cambiar un contrato, lo avisa al grupo y actualiza `docs/trama.md`
**en el mismo pull request**.

---

## 4. Preparación (Windows)

```
git clone https://github.com/jimendezm/redes-py-1.git
cd redes-py-1
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

Ejecutar:

```
python -m pc.main --simulado
python -m pc.main --puerto COM3 --baud 9600
python scripts/eco.py COM3 9600
```

Notas sobre los Arduino en Windows:
- Un puerto COM solo lo puede abrir un programa a la vez: cierren el Monitor Serie del IDE antes de correr Python.
- El número de COM puede cambiar al reconectar la placa (Administrador de dispositivos → Puertos).
- Si el Nano no aparece, instalar el driver CH340. Si falla la carga, probar *Procesador → ATmega328P (Old Bootloader)*.
- El cable USB debe ser de datos, no solo de carga.

---

## 5. Flujo de trabajo en Git

- `main` siempre debe funcionar y pasar `pytest`. No se hace push directo a `main`.
- Una rama por módulo: `feature/gui`, `feature/ventana`, `feature/aplicacion`, `feature/firmware`.
- Pull requests pequeños; otra persona los revisa antes de fusionar.
- Cada módulo nuevo trae sus tests en `pc/tests/`.
- Commits claros, por ejemplo: `ventana: retransmitir al vencer el timer`.

---

## 6. Reparto de trabajo

| Módulo | Responsable | Necesita hardware |
|---|---|---|
| GUI y monitor | _por asignar_ | No |
| Enlace: ventana, timer, retransmisión | _por asignar_ | No |
| Enlace: receptor, búfer J, ACK/NAK | _por asignar_ | No |
| Aplicación (lector, fragmentador, reensamblador, escritor) y canal simulado | _por asignar_ | No |
| Firmware: puente USB↔UART y Hamming | _por asignar_ (quienes tienen Arduino) | Sí |
| Integrador (mantiene `main` funcionando) | _por asignar_ | No |

---

## 7. Cronograma

| Fechas | Meta |
|---|---|
| 18-20 oct | Repo listo, contratos acordados, prueba de eco con Arduino, comprar cable |
| 20-24 oct | Enlace + aplicación + GUI funcionando con canal simulado |
| 24-27 oct | Firmware (puente + Hamming) e integración PC ↔ Arduino ↔ Arduino |
| 27-31 oct | Cable armado, mediciones de las 24 configuraciones |
| 31 oct-2 nov | Informe, apéndice de diseño y ensayo de la defensa |

Las 24 configuraciones: 2 velocidades (9600 / 19200) × 2 cargas (500 / 900 B) ×
3 ventanas (4 / 6 / 8) × Hamming (sí / no).

---

## 8. Decisiones pendientes

Estas cosas el informe las dejó para la segunda etapa y hay que fijarlas pronto:

- [ ] Trama CONTROL: negociación de parámetros (velocidad, carga, ventana, Hamming, tamaño y extensión del archivo) y cierre de sesión.
- [ ] Fórmula de la tasa de error (qué cuenta y entre qué se divide).
- [ ] Valor de J (se decide midiendo).
- [ ] Timeout (se mide con el enlace real).
- [ ] Librería para UART por software en D8/D9: `SoftwareSerial` o `AltSoftSerial` (consultar al profesor si se permite).
- [ ] Velocidad USB PC↔Arduino frente a la del enlace y cómo evitar desbordar los 2 KB del Arduino.

---

## 9. Honor académico

Según el enunciado, no se puede usar código copiado de internet ni de otros proyectos.
Si usamos alguna librería externa (pyserial, una librería de Arduino), la declaramos en
el informe.