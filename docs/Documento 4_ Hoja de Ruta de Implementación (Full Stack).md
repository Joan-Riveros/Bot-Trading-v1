# **Documento 4: Hoja de Ruta de Implementación (Full Stack)**

Versión: 2.0  
Instrucciones: Seguir el orden para garantizar la integración correcta entre Móvil y PC.

## **FASE 1: El Core (Backend Lógico)**

**Objetivo:** Que la estrategia funcione en consola antes de conectarla al móvil.

1. **Data Mining:** Scripts para descargar data de MT5 (get\_data.py).  
2. **Detector PO3:** Script que imprime en consola "Patrón Detectado" (pattern\_detector.py).  
3. **Entrenamiento ML:** Generar el modelo model.json (train\_model.py).  
   * *Nota:* Hasta aquí, es igual al plan original.

## **FASE 2: La API (Backend Server)**

**Objetivo:** Convertir los scripts en un servidor controlable.

4. **Servidor FastAPI (server.py):**  
   * Crear endpoints /start y /stop.  
   * Integrar el bucle de trading dentro de una función asíncrona (asyncio).  
   * Implementar el WebSocket para emitir logs.  
   * *Prueba:* Usar Postman o navegador para encender/apagar el bot y ver que responda.

## **FASE 3: La App Móvil (Frontend)**

**Objetivo:** Crear la interfaz de control.

5. **Estructura Flutter:**  
   * Crear proyecto flutter create trading\_bot\_control.  
   * Configurar modelo de datos (Trade, Log).  
6. **Conexión HTTP/WS:**  
   * Implementar repositorio que conecte a 10.0.2.2:8000 (o IP local).  
   * Crear pantalla de Dashboard con indicador de estado (conectado al WS).  
7. **Botones de Control:**  
   * Vincular botones de la UI a los endpoints /start y /panic.

## **FASE 4: Integración y Pruebas**

**Objetivo:** Prueba de campo en entorno local.

8. **Simulación Completa:**  
   * Abrir MT5 en PC.  
   * Correr servidor FastAPI en PC.  
   * Abrir App en Emulador/Móvil.  
   * Pulsar "Iniciar" en el móvil \-\> Verificar que Python empieza a imprimir logs \-\> Verificar que MT5 recibe órdenes.  
   * Pulsar "Panic" en el móvil \-\> Verificar que MT5 cierra todo.