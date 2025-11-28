import pandas as pd
import numpy as np
import os
from datetime import timedelta
import pandas_ta as ta
import pytz # Necesario para arreglar el error de hora

def label_and_enrich_dataset():
    print("⚖️ INICIANDO ETIQUETADO E INGENIERÍA DE FEATURES...")

    candidates_path = "quant_lab/datasets/candidates_unlabeled.csv"
    raw_data_path = "data_core/storage/NQ_M1.csv" # Asegúrate que coincida con lo que bajó miner.py

    if not os.path.exists(candidates_path) or not os.path.exists(raw_data_path):
        print(f"❌ Faltan archivos. Buscando en: {candidates_path} y {raw_data_path}")
        return

    # 1. Cargar Datos
    df_candidates = pd.read_csv(candidates_path)
    
    # Estandarizar Fechas a UTC primero
    df_candidates["timestamp"] = pd.to_datetime(df_candidates["timestamp"], utc=True)

    df_raw = pd.read_csv(raw_data_path, index_col="time", parse_dates=True)
    df_raw.index = pd.to_datetime(df_raw.index, utc=True)
    
    # Calcular indicadores si faltan (Sobre todo ATR para normalizar)
    if 'ATR' not in df_raw.columns:
        print("⚙️ Calculando indicadores técnicos base...")
        df_raw['EMA_50'] = ta.ema(df_raw['close'], length=50)
        df_raw['EMA_200'] = ta.ema(df_raw['close'], length=200)
        df_raw['ATR'] = ta.atr(df_raw['high'], df_raw['low'], df_raw['close'], length=14)
        # Rellenar NaN iniciales para evitar errores
        # 1. Rellenar huecos intermedios con el último valor conocido (Honesto)
        df_raw.fillna(method='ffill', inplace=True)
        # 2. Eliminar las primeras velas donde los indicadores aún no existen (EMA200 es NaN al inicio)
        # Si no las borramos, el modelo entrenará con basura o ceros en esas filas.
        df_raw.dropna(inplace=True)

    print(f"🧐 Procesando {len(df_candidates)} candidatos...")

    # Usaremos una lista nueva para reconstruir el DF limpio y evitar errores de longitud
    processed_data = []
    
    MAX_HOLDING_TIME = timedelta(minutes=45)
    ny_tz = pytz.timezone('America/New_York')

    for i, row in df_candidates.iterrows():
        entry_time = row["timestamp"]
        
        # Validar que tengamos datos para ese momento
        if entry_time not in df_raw.index:
            continue # Saltamos silenciosamente si no hay data histórica

        try:
            # Contexto
            current_market_data = df_raw.loc[entry_time]
            
            # Ventana Futura (Look-ahead)
            exit_deadline = entry_time + MAX_HOLDING_TIME
            future_window = df_raw.loc[entry_time : exit_deadline] # Slicing de tiempo
            
            if future_window.empty or len(future_window) < 2:
                continue

            # --- A. LABELING (Win/Loss) ---
            entry_price = row["entry_price"]
            tp_price = row["take_profit"]
            sl_price = row["stop_loss"]
            signal_type = row["signal_type"]
            
            outcome = 0
            
            # Iteramos velas futuras (saltando la primera que es la entrada)
            for t, candle in future_window.iloc[1:].iterrows():
                if signal_type == "BULLISH":
                    if candle["low"] <= sl_price:
                        outcome = 0; break
                    if candle["high"] >= tp_price:
                        outcome = 1; break
                elif signal_type == "BEARISH":
                    if candle["high"] >= sl_price:
                        outcome = 0; break
                    if candle["low"] <= tp_price:
                        outcome = 1; break
            
            # --- B. FEATURE ENGINEERING (Corregido) ---
            
            # 1. Corrección de Hora (UTC -> NY)
            # Convertimos el timestamp UTC a hora NY para saber si es sesión real
            entry_time_ny = entry_time.astimezone(ny_tz)
            feat_hour = entry_time_ny.hour
            
            # 2. Is NY Session (9:00 - 16:00 Hora NY)
            feat_is_ny = 1 if (9 <= feat_hour < 16) else 0
            
            # 3. Distancia EMA y Trend
            atr_val = current_market_data['ATR'] if current_market_data['ATR'] > 0 else 1.0
            dist_ema50 = (entry_price - current_market_data['EMA_50']) / atr_val
            feat_trend = 1 if entry_price > current_market_data['EMA_200'] else 0
            
            # 4. Volatility Shock
            candle_range = current_market_data['high'] - current_market_data['low']
            feat_shock = candle_range / atr_val

            # Guardamos TODO en un diccionario nuevo
            new_row = row.to_dict()
            new_row.update({
                'target': outcome,
                'hour': feat_hour,
                'is_ny_session': feat_is_ny,
                'distance_to_ema50': dist_ema50,
                'trend_ema200': feat_trend,
                'volatility_shock': feat_shock
            })
            
            processed_data.append(new_row)

        except Exception as e:
            print(f"⚠️ Error procesando fila {i}: {e}")
            continue

    # Reconstruir DataFrame final
    if not processed_data:
        print("❌ No se pudieron procesar datos. Revisa las fechas.")
        return

    df_final = pd.DataFrame(processed_data)
    
    output_path = "quant_lab/datasets/dataset_labeled.csv"
    # Asegurar directorio
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    df_final.to_csv(output_path, index=False)

    print(f"✅ DATASET LISTO: {len(df_final)} muestras guardadas en {output_path}")
    win_rate = (df_final['target'].sum() / len(df_final)) * 100
    print(f"📊 Win Rate Base (Sin IA): {win_rate:.2f}%")

if __name__ == "__main__":
    label_and_enrich_dataset()