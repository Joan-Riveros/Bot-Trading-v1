import pandas as pd
import pytz
from datetime import datetime

def build_features(row, signal_entry_price, market_context):
    """
    SINGLE SOURCE OF TRUTH (Fuente Única de Verdad)
    Calcula los features matemáticos para la IA.
    
    Args:
        row: Fila del DataFrame (Series) con datos OHLCV y Time.
        signal_entry_price: Precio de entrada de la señal detectada.
        market_context: Diccionario con indicadores {'atr', 'ema_50', 'ema_200'}
    
    Returns:
        pd.DataFrame: DataFrame de 1 fila con las columnas en orden estricto.
    """
    
    # 1. Gestión de Hora (Timezone Aware)
    # Asumimos que row.name o row['time'] es el timestamp.
    ts = row.name if isinstance(row.name, pd.Timestamp) else row['time']
    
    # Convertir a UTC si es naive
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=pytz.utc)
    else:
        ts = ts.astimezone(pytz.utc)
        
    ny_tz = pytz.timezone('America/New_York')
    ny_time = ts.astimezone(ny_tz)
    
    feat_hour = ny_time.hour
    
    # 2. Cálculos Relativos
    atr = market_context.get('atr', 1.0)
    if atr <= 0: atr = 1.0
    
    entry = signal_entry_price
    ema50 = market_context.get('ema_50', entry)
    ema200 = market_context.get('ema_200', entry)
    
    # Distancia normalizada por volatilidad
    dist_ema50 = (entry - ema50) / atr
    
    # Tendencia binaria
    trend_ema200 = 1 if entry > ema200 else 0
    
    # Shock de volatilidad (Rango de la vela / ATR)
    high = row.get('high', 0)
    low = row.get('low', 0)
    vol_shock = (high - low) / atr

    # 3. Construcción del Vector
    data = {
        "hour": feat_hour,
        "is_ny_session": 1 if (9 <= feat_hour < 16) else 0,
        "distance_to_ema50": dist_ema50,
        "trend_ema200": trend_ema200,
        "volatility_shock": vol_shock
    }
    
    # ORDEN ESTRICTO (Vital para XGBoost)
    cols = ["hour", "is_ny_session", "distance_to_ema50", "trend_ema200", "volatility_shock"]
    
    return pd.DataFrame([data])[cols]