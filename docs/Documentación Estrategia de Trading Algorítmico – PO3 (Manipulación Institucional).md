# **Documentación Estrategia de Trading Algorítmico – PO3 (Manipulación Institucional)**

### **1\. Resumen de la Estrategia**

* **Nombre de la estrategia:** PO3 – Price, Orderflow & Opportunity (Basado en Manipulación Institucional).  
* **Mercados a operar:** Índices bursátiles (NASDAQ, S\&P500).  
* **Temporalidades principales:**  
  * **4H y 1H** → Bias macro general.  
  * **30M y 15M** → Bias de la sesión.  
  * **5M y 1M** → Confirmación de entradas.  
* **Tipo de estrategia:** Intradía, basada en estructura institucional (ICT concepts).  
* **Objetivo:** Aprovechar patrones de manipulación y distribución de liquidez en la sesión de Nueva York.

### **2\. Lógica de la Estrategia**

La estrategia se basa en el modelo **PO3 (Consolidación – Manipulación – Distribución)** y en la estructura del mercado generada en las distintas sesiones (Asia, Londres y Nueva York).

* **Sesiones relevantes:**  
  * Análisis previo de Asia y Londres.  
  * Entrada en sesión de Nueva York (apertura 9:30 EST, preferencia en la hora macro 9:50 EST).  
* **Condiciones de Entrada:**  
  1. Identificar bias (alcista/bajista) en marcos altos (4H, 1H).  
  2. Validar estructura y manipulación en 30M y 15M.  
  3. Confirmar entrada en 5M con patrones como:  
     * **FVG (Fair Value Gap)**  
     * **BOS (Break of Structure)**  
     * **IFVG (Inverse Fair Value Gap)**  
  4. Confirmar en 1M con al menos 3 validaciones entre:  
     * FVG  
     * IFVG  
     * BOS  
     * SMT Divergence  
* **Condiciones de Salida:**  
  * **Take Profit:** Zonas de liquidez próximas (highs/lows significativos, orderblocks, FVG en marcos mayores como 15M o 1H).  
  * **Stop Loss:** Detrás del último high/low estructural tras el BOS.  
* **Filtros adicionales:**  
  * No operar en días de noticias de alto impacto:  
    * CPI  
    * NFP  
    * Discursos de Jerome Powell u otros eventos FED.

### **3\. Gestión del Riesgo**

* **Stop Loss:** Basado en estructura (debajo/encima del último swing relevante).  
* **Take Profit:** En zonas de liquidez más cercanas o estructuras relevantes (OB, FVG en H1 o M15).  
* **Ratio riesgo/beneficio buscado:** Mínimo 1:2 (en setups de alta probabilidad puede ser superior).  
* **Capital por operación:** Ajustable según riesgo total (ejemplo: 1–2% por trade).

### **4\. Parámetros de la Estrategia**

* **Bias:** definido en 4H y 1H.  
* **Estructura de sesión:** validada en 30M/15M.  
* **Confirmaciones de entrada:**  
  * En 5M: 1–2 (FVG, BOS, IFVG).  
  * En 1M: mínimo 3 (FVG, IFVG, BOS, SMT Divergence).

### **5\. Marco de Ejecución**

* **Horario principal:** 9:30–11:00 EST (sesión NY, con foco en 9:50 EST “hora macro”).  
* **Frecuencia de evaluación:** Cada cierre de vela en 5M y 1M durante ventana de ejecución.  
* **Plataforma recomendada:** MetaTrader, TradingView para análisis, y broker con acceso directo a índices (Interactive Brokers, AMP, etc.).

### **6\. Ejemplo de Operación**

* **Fecha:** 15/08/2025  
* **Activo:** NASDAQ (NQ)  
* **Bias:** Bajista en 1H tras manipulación de Londres.  
* **Señal:** BOS bajista en 5M \+ confirmación FVG y SMT Divergence en 1M.  
* **Entrada:** 15,320  
* **Stop Loss:** 15,360 (último high tras BOS).  
* **Take Profit:** 15,220 (zona de liquidez en M15).  
* **Resultado:** \+2.5R

### **7\. Backtesting (pendiente de pruebas)**

* **Periodo recomendado:** últimos 6–12 meses de NY Session.  
* **Métricas a evaluar:**  
  * Nº de operaciones.  
  * % acierto.  
  * Ratio riesgo/beneficio medio.  
  * Profit factor.  
  * Drawdown máximo.

### **8\. Observaciones y Limitaciones**

* Estrategia dependiente de la sesión de Nueva York.  
* Requiere disciplina en días de noticias (no operar).  
* Alta efectividad cuando hay manipulación clara en Asia/Londres.  
* Posibles mejoras: backtesting automático con filtros de volatilidad y calendarización de noticias.