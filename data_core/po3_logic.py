import pandas as pd
import numpy as np


class PO3Detector:
    """
    v2.0 - Motor de Lógica Secuencial (State-Aware)
    Implementa la validación estricta:
    1. Liquidity Raid (Sweep) contra niveles 'target_liquidity' proyectados.
    2. Displacement (Cierre fuerte lejos de la zona).
    3. FVG Creation (Confirmación de inyección de volumen).
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def scan_for_signals(self, i: int):
        """
        Escanea la vela en el índice 'i' buscando la FINALIZACIÓN del patrón PO3.
        Retorna dict con trade setup o None.
        """
        # Margen de seguridad para cálculos previos
        if i < 20:
            return None

        row = self.df.iloc[i]

        # --- PASO 1: ¿Tenemos un FVG (Gatillo) en la vela actual? ---
        # El FVG es la última pieza del dominó. Si no está, no procesamos nada.
        fvg_type, fvg_price = self._detect_dynamic_fvg(i)

        if not fvg_type:
            return None

        # --- PASO 2: Validación de Contexto (El Sweep) ---
        # Si tenemos un FVG Bajista, significa que queremos vender.
        # Para vender, PRIMERO debimos haber capturado liquidez de compra (Highs).

        # Miramos una ventana corta hacia atrás (ej. 5 velas).
        # La manipulación debe ser reciente para ser válida.
        scan_window = 5
        sweep_detected = False
        stop_loss_level = 0.0

        if fvg_type == "BEARISH":
            # Lógica: En las últimas X velas, ¿hubo alguna cuyo High superó
            # la liquidez objetivo (Target High) que existía en ese momento?

            # Recortamos la ventana de análisis
            window_df = self.df.iloc[i - scan_window : i]

            # Buscamos el Sweep
            # Condición: High de la vela > Target Liquidity High de esa misma vela
            sweeps = window_df[window_df["high"] > window_df["target_liquidity_high"]]

            if not sweeps.empty:
                # Validamos calidad del Sweep:
                # El precio máximo alcanzado en la ventana es nuestro punto de invalidación
                highest_point = window_df["high"].max()

                # Check de Desplazamiento:
                # El precio actual (que cerró el FVG) debe estar DEBAJO del nivel barrido.
                # Si estamos por encima, no es un rechazo, es una ruptura.
                current_close = row["close"]

                # Obtenemos el nivel que se rompió (del primer sweep detectado)
                level_broken = sweeps.iloc[0]["target_liquidity_high"]

                if current_close < level_broken:
                    sweep_detected = True
                    stop_loss_level = highest_point

        elif fvg_type == "BULLISH":
            # Lógica inversa: Buscamos toma de liquidez de venta (Lows)
            window_df = self.df.iloc[i - scan_window : i]

            sweeps = window_df[window_df["low"] < window_df["target_liquidity_low"]]

            if not sweeps.empty:
                lowest_point = window_df["low"].min()
                current_close = row["close"]
                level_broken = sweeps.iloc[0]["target_liquidity_low"]

                if current_close > level_broken:
                    sweep_detected = True
                    stop_loss_level = lowest_point

        if not sweep_detected:
            return None

        # --- PASO 3: Construcción de la Señal ---
        return {
            "timestamp": str(row.name),
            "signal_type": fvg_type,  # BULLISH / BEARISH
            "entry_price": fvg_price,  # Límite de entrada
            "stop_loss": stop_loss_level,  # Protección estructural
            "take_profit": self._calculate_tp(fvg_price, stop_loss_level, fvg_type),
            "atr_context": row["ATRr_14"],  # Para fines de registro/debug
        }

    def _detect_dynamic_fvg(self, idx: int):
        """
        Detecta FVG usando ATR como filtro de ruido.
        """
        c0 = self.df.iloc[idx]  # Vela actual
        c1 = self.df.iloc[idx - 1]  # Vela de desplazamiento
        c2 = self.df.iloc[idx - 2]  # Vela origen

        atr = c0["ATRr_14"]
        min_gap_size = 0.5 * atr  # El gap debe ser al menos medio ATR (Significancia)

        # FVG BAJISTA (Gap entre c2.Low y c0.High)
        if c2["low"] > c0["high"]:
            gap = c2["low"] - c0["high"]
            if gap >= min_gap_size:
                return "BEARISH", c2["low"]  # Entrada en el inicio del gap

        # FVG ALCISTA (Gap entre c2.High y c0.Low)
        if c2["high"] < c0["low"]:
            gap = c0["low"] - c2["high"]
            if gap >= min_gap_size:
                return "BULLISH", c2["high"]

        return None, 0.0

    def _calculate_tp(self, entry, sl, direction):
        """Calcula TP fijo 2R para el dataset inicial"""
        risk = abs(entry - sl)
        if direction == "BULLISH":
            return entry + (risk * 2)
        else:
            return entry - (risk * 2)
