import pandas as pd
import numpy as np

class PO3Detector:
    """
    v3.0 - Motor PO3 Institucional + SMT Divergence
    """

    def __init__(self, df: pd.DataFrame, df_correlated: pd.DataFrame = None):
        self.df = df
        self.df_corr = df_correlated # Data del ES (S&P 500)

    def scan_for_signals(self, i: int):
        if i < 20: return None

        row = self.df.iloc[i]

        # 1. FVG Trigger
        fvg_type, fvg_price = self._detect_dynamic_fvg(i)
        if not fvg_type: return None

        # 2. Sweep & SMT Validation
        scan_window = 5
        sweep_detected = False
        smt_confirmed = False # Nueva variable de control
        stop_loss_level = 0.0

        if fvg_type == "BEARISH":
            # --- BUSCAR SWEEP EN NQ ---
            window_df = self.df.iloc[i - scan_window : i]
            # ¿Superamos un High previo?
            sweeps = window_df[window_df["high"] > window_df["target_liquidity_high"]]

            if not sweeps.empty:
                highest_point = window_df["high"].max()
                level_broken = sweeps.iloc[0]["target_liquidity_high"]
                
                # Validación de Desplazamiento (Cierre abajo del nivel roto)
                if row["close"] < level_broken:
                    sweep_detected = True
                    stop_loss_level = highest_point
                    
                    # --- VALIDACIÓN SMT (EL SANTO GRIAL) ---
                    # Si NQ hizo un High mas alto, ¿Qué hizo el ES?
                    if self._check_smt_divergence(i, scan_window, "BEARISH"):
                        smt_confirmed = True
                    else:
                        # Si no hay data de ES, asumimos True para no bloquear (o False si quieres ser estricto)
                        smt_confirmed = True if self.df_corr is None else False

        elif fvg_type == "BULLISH":
            # --- BUSCAR SWEEP EN NQ ---
            window_df = self.df.iloc[i - scan_window : i]
            sweeps = window_df[window_df["low"] < window_df["target_liquidity_low"]]

            if not sweeps.empty:
                lowest_point = window_df["low"].min()
                level_broken = sweeps.iloc[0]["target_liquidity_low"]

                if row["close"] > level_broken:
                    sweep_detected = True
                    stop_loss_level = lowest_point
                    
                    # --- VALIDACIÓN SMT ---
                    if self._check_smt_divergence(i, scan_window, "BULLISH"):
                        smt_confirmed = True
                    else:
                        smt_confirmed = True if self.df_corr is None else False

        # FILTRO FINAL: Solo pasamos si hay Sweep Y (SMT o no hay data correlacionada)
        if not sweep_detected: return None
        
        # Opcional: Puedes decidir si retornar None si smt_confirmed es False
        # Para v1, lo marcaremos en el objeto de retorno para que la IA lo sepa
        
        return {
            "timestamp": str(row.name),
            "signal_type": fvg_type,
            "entry_price": fvg_price,
            "stop_loss": stop_loss_level,
            "take_profit": self._calculate_tp(fvg_price, stop_loss_level, fvg_type),
            "atr_context": row["ATRr_14"],
            "smt_divergence": smt_confirmed # Nueva etiqueta valiosa
        }

    def _check_smt_divergence(self, idx, window, direction):
        """
        Compara la estructura del NQ con el ES.
        Retorna True si hay Divergencia (SMT).
        """
        if self.df_corr is None: return False
        
        # Sincronización temporal: Obtener índices de tiempo
        try:
            current_time = self.df.index[idx]
            start_time = self.df.index[idx - window]
            
            # Recortar ventana en el Activo Correlacionado (ES)
            # Usamos búsqueda asof o slice directo si los indices coinciden
            es_window = self.df_corr.loc[start_time : current_time]
            
            if es_window.empty: return False
            
            # --- LÓGICA DE DIVERGENCIA ---
            if direction == "BEARISH":
                # NQ hizo Higher High (Ya validado fuera).
                # SMT Bearish = ES hizo Lower High (Debilidad).
                
                # Obtenemos el máximo de ES en esta ventana
                es_high_window = es_window['high'].max()
                
                # Obtenemos el target liquidity del ES (necesitamos que indicators.py haya procesado ES tambien)
                # Si no tenemos target liquidity en ES, comparamos con el máximo de una ventana PREVIA
                # Simplificación robusta: Comparar con el máximo de la ventana anterior a esta ventana
                # Para MVP: Verificamos si el ES High de la ventana superó su propio fractal reciente
                # Asumimos que df_corr tiene las columnas 'target_liquidity_high' calculadas
                
                if 'target_liquidity_high' in es_window.columns:
                    # Si ES NO rompió su liquidez, es divergencia.
                    # NQ rompió (Fuerza/Manipulación), ES no rompió (Debilidad real).
                    broken_liquidity = es_window[es_window['high'] > es_window['target_liquidity_high']]
                    
                    if broken_liquidity.empty:
                        return True # ¡SMT DETECTADO! ES no pudo hacer un alto más alto.
                    else:
                        return False # Correlación normal (ambos subieron).
                        
            elif direction == "BULLISH":
                # NQ hizo Lower Low.
                # SMT Bullish = ES hizo Higher Low (Fortaleza).
                if 'target_liquidity_low' in es_window.columns:
                    broken_liquidity = es_window[es_window['low'] < es_window['target_liquidity_low']]
                    
                    if broken_liquidity.empty:
                        return True # ¡SMT DETECTADO! ES no quiso bajar.
                    else:
                        return False
                        
        except Exception as e:
            # print(f"Error SMT check: {e}")
            return False

        return False

    def _detect_dynamic_fvg(self, idx: int):
        c0 = self.df.iloc[idx]; c1 = self.df.iloc[idx - 1]; c2 = self.df.iloc[idx - 2]
        atr = c0["ATRr_14"]
        min_gap = 0.5 * atr
        
        if c2["low"] > c0["high"]: # Bearish
            if (c2["low"] - c0["high"]) >= min_gap: return "BEARISH", c2["low"]
            
        if c2["high"] < c0["low"]: # Bullish
            if (c0["low"] - c2["high"]) >= min_gap: return "BULLISH", c2["high"]
            
        return None, 0.0

    def _calculate_tp(self, entry, sl, direction):
        risk = abs(entry - sl)
        return entry + (risk * 2) if direction == "BULLISH" else entry - (risk * 2)