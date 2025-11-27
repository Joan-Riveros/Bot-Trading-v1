Este es el **Plan Maestro Definitivo (Execution Roadmap v1.0)**. Está diseñado para velocidad y precisión, eliminando cualquier tarea que no aporte valor directo al P\&L o al requerimiento del cliente.

Dividiremos el desarrollo en **4 Sprints de Alta Intensidad**.

---

### **Estructura del Proyecto (Mapa Mental)**

Antes de escribir una línea, así se organizará la carpeta para mantener el orden institucional:

Plaintext

/institutional\_bot\_v1  
│  
├── /data\_core           \# SPRINT 1: Datos y Lógica  
│   ├── miner.py         \# Descarga NQ \+ ES (Sincronizados)  
│   ├── indicators.py    \# Fractales Híbridos (3 & 5), VWAP, Midnight Open  
│   └── po3\_logic.py     \# Detector: Sweep \+ SMT \+ BOS \+ FVG  
│  
├── /quant\_lab           \# SPRINT 2: Inteligencia Artificial  
│   ├── labeler.py       \# Define éxito: TP en \< 45 min  
│   ├── features.py      \# Crea inputs: Distancia VWAP, Hora, Volatilidad  
│   └── train\_xgb.py     \# Entrena el modelo XGBoost  
│  
├── /execution\_engine    \# SPRINT 3: Servidor y MT5  
│   ├── server.py        \# FastAPI \+ WebSockets  
│   ├── mt5\_driver.py    \# Gestión de Órdenes (Limit, Expiración)  
│   └── risk.py          \# Cálculo de lotaje y Bias H1  
│  
└── /mobile\_app          \# SPRINT 4: Flutter (Cliente)  
    ├── lib/             \# UI Code  
    └── pubspec.yaml     \# Dependencias (web\_socket\_channel)

---

### **🚀 SPRINT 1: El Núcleo Matemático (Lógica y Datos)**

Objetivo: Validar que la estrategia existe en el gráfico y extraer la data para entrenar.

Tiempo estimado: 1-2 Días.

1. **Script 01\_miner.py:**  
   * Conexión a MT5.  
   * Descargar datos M1, M5, M15, H1 de **NQ** (Nasdaq) y **ES** (S\&P500).  
   * **Crítico:** Sincronizar los timestamps. Para detectar SMT, necesitamos saber qué hizo el ES exactamente en el minuto que el NQ hizo el Sweep.  
2. **Librería indicators.py:**  
   * Codificar **Fractales Híbridos**:  
     * Función get\_fractals(window=3) para M1/M5 (Gatillo).  
     * Función get\_fractals(window=5) para H1 (Estructura).  
   * Codificar **Midnight Open**: Detectar el precio de apertura a las 00:00 hora servidor (ajustar a NY).  
3. **Detector 02\_po3\_detector.py:**  
   * Recorre el histórico.  
   * Detecta la secuencia: **Sweep (M15) \+ SMT Divergence (vs ES) \+ BOS (M1) \+ FVG**.  
   * **Output:** Genera un archivo candidates\_dataset.csv.

---

### **🧠 SPRINT 2: El Cerebro (Machine Learning)**

Objetivo: Filtrar los falsos positivos (rangos lentos) usando XGBoost.

Tiempo estimado: 1-2 Días.

1. **Etiquetado (labeler.py):**  
   * Toma los candidatos del Sprint 1\.  
   * Mira al futuro: ¿El precio tocó \+2R en las siguientes **9 velas (45 min)**?  
     * SÍ \= Clase 1\.  
     * NO (o tocó SL) \= Clase 0\.  
2. **Ingeniería de Features (features.py):**  
   * Añadir columnas clave:  
     * time\_encoding: (Seno/Coseno de la hora).  
     * dist\_vwap: (Precio \- VWAP) / ATR.  
     * smt\_strength: Valor binario o magnitud de la divergencia.  
3. **Entrenamiento (train.py):**  
   * Entrenar XGBoost.  
   * Guardar el modelo como model.json.  
   * **Validación:** Asegurar que Precision \> 60% (preferimos perder oportunidades que perder dinero).

---

### **⚙️ SPRINT 3: El Motor de Ejecución (Backend API)**

Objetivo: Un sistema autónomo que opere en vivo y permita control externo.

Tiempo estimado: 2-3 Días.

1. **FastAPI Server (server.py):**  
   * Endpoints REST: /start, /stop, /status.  
   * **WebSocket:** /ws/feed para enviar logs en tiempo real a la app.  
2. **Driver MT5 (mt5\_driver.py):**  
   * **Bias Check:** Antes de buscar trade, validar:  
     * ¿Precio \> Estructura H1 (50 velas)?  
     * ¿Precio \> Midnight Open?  
   * **Gestión de Órdenes:**  
     * Calcular Lotaje (Riesgo 1%).  
     * Enviar **Buy Limit** al inicio del FVG (o 50% si FVG \> 10 puntos).  
     * **Loop de Cancelación:** Si la orden no se activa en 15 min \-\> OrderDelete.  
3. **Integración:**  
   * El sistema carga el model.json al iniciar.  
   * Analiza cada vela nueva de M1. Si hay señal \-\> Ejecuta.

---

### **📱 SPRINT 4: La Interfaz (Flutter App)**

Objetivo: Cumplir el requisito del cliente con una app reactiva y profesional.

Tiempo estimado: 2-3 Días.

1. **Setup:** Flutter create \+ Dependencias (dio, web\_socket\_channel, provider).  
2. **Conexión:**  
   * Clase WebSocketService: Se conecta a ws://ip-servidor:8000/ws/feed.  
   * Escucha el stream y actualiza una variable de estado messagesList.  
3. **UI (Pantalla Única \- Dashboard):**  
   * **Cabecera:** Estado del Bias (Alcista/Bajista) con colores.  
   * **Cuerpo:** Lista de Logs (tipo terminal hacker).  
   * **Pie:** Botones grandes "START SYSTEM" (Verde) y "PANIC EXIT" (Rojo).  
4. **Compilación:** Generar APK para Android.

---

### **Resumen de Prioridades**

1. **No pierdas tiempo diseñando la App hoy.** La App es inútil sin el Sprint 1 y 3 funcionando.  
2. **Cuidado con la SMT:** Es la parte más compleja de programar porque requiere sincronizar dos arrays de datos (NQ y ES) al milisegundo exacto. Dedícale atención en el Sprint 1\.  
3. **Backtesting Visual:** En el Sprint 1, cuando generes candidates.csv, **abre el gráfico manual** y verifica 10 operaciones al azar. Si el código detecta basura, no pases al Sprint 2\.

