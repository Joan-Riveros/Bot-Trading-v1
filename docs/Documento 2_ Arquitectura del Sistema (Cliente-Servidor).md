# **Documento 2: Arquitectura del Sistema (Cliente-Servidor)**

Versión: 2.0 (Adaptada a Backend API \+ Frontend Móvil)  
Objetivo: Definir la infraestructura dividida entre el Motor de Trading (Python) y el Tablero de Control (Flutter).

## **1\. Diagrama de Alto Nivel**

\[ ORDENADOR / SERVIDOR \]                 \[ DISPOSITIVO MÓVIL \]  
(Backend Python \- FastAPI)               (Frontend Flutter)  
       |                                         |  
       |---\[Motor PO3 \+ MT5\] \<----(Control)----- | \[Botones Start/Stop\]  
       |                                         |  
       |---\[Modelo ML\]       \----(Estado)------\> | \[Dashboard: "Buscando..."\]  
       |                                         |  
       |---\[Base de Datos\]   \----(Historial)---\> | \[Lista de Trades/P\&L\]

## **2\. Componentes del Backend (Python)**

El backend es el "Cerebro". Debe correr independientemente de si la app móvil está abierta o cerrada.

### **A. API Server (FastAPI)**

Expone endpoints para que el móvil se comunique.

* **Tecnología:** FastAPI, Uvicorn.  
* **Protocolos:**  
  * **REST (HTTP):** Para acciones puntuales (Iniciar, Parar, Ver Historial).  
  * **WebSocket (WS):** Para streaming de estado en tiempo real (Log de consola, cambio de precio, alertas).

### **B. Endpoints Requeridos**

1. POST /bot/start: Inicia el bucle de trading en un hilo secundario (Background Task).  
2. POST /bot/stop: Detiene el bucle de trading de forma segura (cierra posiciones si se configura así).  
3. POST /bot/panic: "Panic Button". Cierra TODAS las posiciones abiertas inmediatamente y apaga el bot.  
4. GET /stats: Retorna P\&L diario, Winrate actual y estado del servicio.  
5. WS /ws/status: Socket que emite JSONs con eventos: {"type": "log", "message": "Patrón detectado en NQ..."}.

### **C. Motor de Trading (Core)**

* Mantiene la conexión con MetaTrader 5 (mt5.initialize()).  
* Ejecuta la lógica de la Estrategia PO3 (Fase 1 y Fase 2 descritas en Doc 1).  
* Almacena operaciones en un archivo local trades.json o base de datos SQLite para persistencia.

## **3\. Componentes del Frontend (Flutter)**

La app es el "Control Remoto". No procesa datos complejos, solo visualiza.

### **A. Pantallas (UI)**

1. **Dashboard (Home):**  
   * Indicador de Estado (Semáforo: Rojo/Verde).  
   * Texto de Estado actual (ej. "Esperando apertura NY", "Analizando velas...").  
   * Gráfico simple de P\&L del día.  
2. **Consola/Logs:**  
   * Lista scrolleable que muestra los mensajes que llegan por WebSocket (lo que el bot está "pensando").  
3. **Controles:**  
   * Botón grande "ENCENDER SISTEMA".  
   * Botón "APAGAR".  
   * Botón de emergencia "CERRAR TODO".

### **B. Conectividad Local**

* **Desarrollo en Emulador:** Apuntar API a http://10.0.2.2:8000.  
* **Desarrollo en Físico (USB):** Apuntar API a http://\<IP\_LOCAL\_PC\>:8000 (ej. 192.168.1.35).

## **4\. Stack Tecnológico Actualizado**

* **Backend:** Python 3.9+, FastAPI, MetaTrader5, Pandas, XGBoost.  
* **Frontend:** Flutter (Dart), Provider o Riverpod (Gestión de estado), Dio (HTTP), web\_socket\_channel (WS).  
* **Base de Datos:** SQLite (integrado en Python) para guardar historial de trades y mostrarlo en el móvil.