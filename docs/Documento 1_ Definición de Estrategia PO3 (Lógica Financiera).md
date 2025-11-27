# **Documento 1: Definición de Estrategia PO3 (Lógica Financiera)**

Versión: 1.0  
Contexto: Reglas estrictas de negocio para el "Motor Determinista".

## **1\. Concepto Central**

La estrategia se basa en el ciclo **PO3 (Accumulation, Manipulation, Distribution)** aplicado a la sesión de Nueva York en índices bursátiles. Busca capturar la reversión tras una manipulación institucional de liquidez.

## **2\. Activos y Horarios**

* **Instrumentos:** NASDAQ (NQ), S\&P500 (ES).  
* **Ventana Operativa:** 09:30 EST – 11:00 EST (New York Session).  
* **Filtro de Calendario:** **PROHIBIDO** operar 30 minutos antes/después de noticias de alto impacto (CPI, NFP, FOMC, Fed Chair Speech).

## **3\. Jerarquía de Temporalidades (Multi-Timeframe)**

1. **Macro (4H/1H):** Define el Bias (Sesgo).  
   * *Bajista:* Precio debajo de estructura bajista validada.  
   * *Alcista:* Precio encima de estructura alcista validada.  
2. **Estructura (15M/30M):** Define los Puntos de Liquidez (Swings).  
   * Identificar Altos (Highs) y Bajos (Lows) de la sesión de Londres y Asia.  
3. **Ejecución (5M/1M):** Gatillo de entrada.

## **4\. Secuencia Lógica de Entrada (El Setup)**

El bot debe buscar esta secuencia cronológica exacta. Si un paso falla, el setup se cancela.

### **Paso A: La Manipulación (Sweep)**

* El precio debe romper un Swing High/Low relevante (de Londres o Asia) dentro de la ventana operativa.  
* **Condición Crítica:** Debe ser una "Toma de Liquidez" (Sweep), no una continuación.  
  * *Validación:* El precio rompe el nivel, pero la vela cierra (o regresa rápidamente) dentro del rango anterior.

### **Paso B: El Rompimiento (BOS \- Break of Structure)**

* Inmediatamente tras la manipulación, el precio debe romper la estructura en dirección opuesta (Market Structure Shift).  
* *Ejemplo Bajista:* Tras tomar un High, el precio rompe con fuerza el último Low de corto plazo (M5/M1).

### **Paso C: La Ineficiencia (FVG/IFVG)**

* El movimiento que causó el BOS debe dejar un **Fair Value Gap (FVG)** o un **Inverse FVG**.  
* **FVG Bajista:** Hueco entre el Low de la Vela 1 y el High de la Vela 3\.

## **5\. Gestión de la Operación (Trade Management)**

* **Entrada:** Orden Limit en el inicio del FVG o al cierre de la vela de confirmación.  
* **Stop Loss (SL):**  
  * Por encima/debajo del Swing de la Manipulación.  
* **Take Profit (TP):**  
  * Objetivo Fijo: 2R (2 veces el riesgo).  
  * Objetivo Estructural: Siguiente zona de liquidez opuesta en M15.