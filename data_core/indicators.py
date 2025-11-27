import pandas as pd
import pandas_ta as ta
import pytz
import numpy as np


class Indicators:
    """
    v3.0 - Arquitectura 'Lag-Aware' & 'Forward-Fill'
    - Soluciona el Look-Ahead Bias mediante desplazamiento explícito (shift=2).
    - Optimiza el acceso a datos mediante ffill (O(1) access en Logic Engine).
    """

    def __init__(self):
        self.ny_timezone = pytz.timezone("America/New_York")

    def add_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df) < 50:
            return df

        # 1. Indicadores de Volatilidad
        # ATR es vital para definir el tamaño mínimo del FVG y Stop Loss dinámico
        df.ta.atr(length=14, append=True)  # Genera columna 'ATRr_14'

        # 2. Estructura y Liquidez (Swings)
        df = self.calculate_fractals(df)

        # 3. Contexto Temporal
        df = self.calculate_midnight_open(df)

        # 4. Tendencia Macro
        df = self.calculate_emas(df)

        return df

    def calculate_fractals(self, df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        Detecta Fractales y proyecta niveles de liquidez CONFIRMADOS.
        """
        # Calcular el offset para center=True.
        # Window 5 implica: 2 atrás, 1 centro, 2 adelante.
        # Por tanto, la confirmación ocurre 2 velas después.
        lag = window // 2

        # --- 1. Detección Geométrica (La verdad histórica) ---
        roll_max = df["high"].rolling(window=window, center=True).max()
        roll_min = df["low"].rolling(window=window, center=True).min()

        df["is_swing_high"] = df["high"] == roll_max
        df["is_swing_low"] = df["low"] == roll_min

        # Limpieza inicial
        df["is_swing_high"] = df["is_swing_high"].fillna(False)
        df["is_swing_low"] = df["is_swing_low"].fillna(False)

        # --- 2. Niveles de Liquidez (Raw) ---
        # Usamos numpy.where para vectorización rápida (más rápido que apply)
        df["high_level_raw"] = np.where(df["is_swing_high"], df["high"], np.nan)
        df["low_level_raw"] = np.where(df["is_swing_low"], df["low"], np.nan)

        # --- 3. Proyección de Liquidez "Tradeable" (CRÍTICO) ---
        # Shift(lag): Movemos el dato al momento donde REALMENTE se confirma.
        # ffill(): Arrastramos ese valor hasta que aparezca uno nuevo.
        # Resultado: En la vela X, 'target_liquidity_high' es el último High confirmado conocido.

        df["target_liquidity_high"] = df["high_level_raw"].shift(lag).ffill()
        df["target_liquidity_low"] = df["low_level_raw"].shift(lag).ffill()

        # Limpieza de columnas auxiliares para no ensuciar memoria
        df.drop(columns=["high_level_raw", "low_level_raw"], inplace=True)

        return df

    def calculate_midnight_open(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.index.tz is None:
            df = df.tz_localize("UTC")
        # Convertir a NY para obtener la apertura real de sesión
        df_ny = df.tz_convert(self.ny_timezone)

        # Extraer fecha y calcular Open diario
        # Optimizamos agrupando solo lo necesario
        midnight_opens = df_ny.groupby(df_ny.index.date)["open"].first()

        # Mapear de vuelta al dataframe original usando la fecha del índice
        df["midnight_open"] = df_ny.index.date
        df["midnight_open"] = df["midnight_open"].map(midnight_opens)

        return df

    def calculate_emas(self, df: pd.DataFrame) -> pd.DataFrame:
        df["ema_50"] = ta.ema(df["close"], length=50)
        df["ema_200"] = ta.ema(df["close"], length=200)
        return df
