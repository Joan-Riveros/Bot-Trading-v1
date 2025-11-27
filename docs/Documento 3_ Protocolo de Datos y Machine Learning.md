# **Documento 3: Protocolo de Datos y Machine Learning**

Versión: 1.0  
Objetivo: Instrucciones para la creación del Dataset y Entrenamiento.

## **1\. Definición del Target (Etiquetado)**

Para entrenar a la IA, debemos definir qué constituye un "Éxito" histórico.  
El script de etiquetado debe recorrer el historial y, para cada patrón PO3 detectado, mirar al futuro:

* **Clase 1 (Éxito):** El precio toca el **Take Profit (+2R)** SIN haber tocado antes el Stop Loss.  
* **Clase 0 (Fallo):** El precio toca el **Stop Loss** ANTES de tocar el Take Profit, O el día termina sin tocar TP.

## **2\. Ingeniería de Características (Feature Engineering)**

La IA no debe ver precios crudos (ej. "15500.50"), sino métricas relativas y normalizadas.

### **Features Obligatorios (Input del Modelo):**

1. **Hora del día:** (Float o One-Hot Encoding) Para detectar estacionalidad dentro de la sesión.  
2. **Tamaño del Sweep:** (Puntos) Cuánto penetró el precio la liquidez antes de revertir.  
3. **Tamaño del FVG:** (Puntos) Magnitud del desbalance.  
4. **Tiempo de Confirmación:** (Velas) Cuántas velas pasaron desde el Sweep hasta el BOS (Inmediatez \= Mejor).  
5. **Volatilidad Reciente:** (ATR 14 en M5) Contexto de volatilidad.  
6. **Distancia al Bias:** (Puntos) Distancia relativa a la media móvil de 200 periodos en M5 (Contexto de tendencia).  
7. **Volumen:** (Si está disponible y es fiable) Volumen en la vela del BOS.

## **3\. Preprocesamiento de Datos**

* **Limpieza:** Eliminar filas con valores NaN.  
* **Split:** División cronológica (NO aleatoria) para evitar *Look-ahead bias*.  
  * Train: Primer 80% del tiempo.  
  * Test: Último 20% del tiempo.  
* **Balanceo:** Si hay muchos más fallos que éxitos (común en trading), ajustar scale\_pos\_weight en XGBoost.

## **4\. Métricas de Evaluación del Modelo**

No optimizar por *Accuracy* (Exactitud global). Optimizar por:

* **Precision (Precisión de la clase 1):** De todas las veces que el bot dijo "Compra", ¿cuántas fueron realmente ganadoras?  
* Queremos una Precisión alta (\>60%), aunque el Recall sea bajo (pocas operaciones). **Calidad sobre Cantidad.**