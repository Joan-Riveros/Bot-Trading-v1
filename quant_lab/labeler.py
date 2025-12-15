import pandas as pd
import numpy as np
import os
import sys
from datetime import timedelta
import pandas_ta as ta
import pytz

# --- IMPORTACIÓN DE LA LIBRERÍA DE FEATURES (Single Source of Truth) ---
# Esto es lo que reduce las líneas: Importamos la lógica en lugar de escribirla de nuevo
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from quant_lab.features import build_features
except ImportError:
    print("❌ Error Crítico: No se encontró 'quant_lab/features.py'.")
    print("   Asegúrate de haber creado ese archivo con la función build_features.")
    sys.exit(1)

def label_and_enrich_dataset():
    print("⚖️ INICIANDO ETIQUETADO E INGENIERÍA DE FEATURES (V3.0 Modular)...")

    candidates_path = "quant_lab/datasets/candidates_unlabeled.csv"
    raw_data_path = "data_core/datasets/SYNC_DATA_M1.csv" 

    if not os.path.exists(candidates_path):
        print(f"❌ Falta candidatos: {candidates_path}")
        return

    if not os.path.exists(raw_data_path):
        print(f"❌ Falta datos crudos: {raw_data_path}")
        return

    # 1. Cargar Datos
    print("📂 Cargando datasets...")
    df_candidates = pd.read_csv(candidates_path)
    df_candidates["timestamp"] = pd.to_datetime(df_candidates["timestamp"], utc=True)

    df_raw = pd.read_csv(raw_data_path, index_col="time", parse_dates=True)
    df_raw.index = pd.to_datetime(df_raw.index, utc=True)
    
    # Normalizar columnas
    if 'nq_close' in df_raw.columns:
        df_raw.rename(columns={
            'nq_open': 'open', 'nq_high': 'high', 'nq_low': 'low', 
            'nq_close': 'close', 'nq_vol': 'volume'
        }, inplace=True)
    
    # 2. Pre-Cálculo de Indicadores (Optimización Vectorizada)
    if 'ATR' not in df_raw.columns:
        print("⚙️ Generando indicadores técnicos base...")
        df_raw.sort_index(inplace=True)
        df_raw['EMA_50'] = ta.ema(df_raw['close'], length=50)
        df_raw['EMA_200'] = ta.ema(df_raw['close'], length=200)
        df_raw['ATR'] = ta.atr(df_raw['high'], df_raw['low'], df_raw['close'], length=14)
        df_raw.ffill(inplace=True)
        df_raw.dropna(inplace=True)

    print(f"🧐 Procesando {len(df_candidates)} candidatos...")

    processed_data = []
    MAX_HOLDING_TIME = timedelta(minutes=45) 

    for i, row in df_candidates.iterrows():
        entry_time = row["timestamp"]
        
        if entry_time not in df_raw.index: continue 

        try:
            current_market_data = df_raw.loc[entry_time]
            
            # --- A. LABELING (Determinista) ---
            exit_deadline = entry_time + MAX_HOLDING_TIME
            future_window = df_raw.loc[entry_time : exit_deadline]
            
            if future_window.empty or len(future_window) < 2: continue

            tp_price = row["take_profit"]
            sl_price = row["stop_loss"]
            signal_type = row["signal_type"]
            
            outcome = 0
            # Vela a vela (skip entrada)
            for t, candle in future_window.iloc[1:].iterrows():
                if signal_type == "BULLISH":
                    if candle["low"] <= sl_price: outcome = 0; break
                    if candle["high"] >= tp_price: outcome = 1; break
                elif signal_type == "BEARISH":
                    if candle["high"] >= sl_price: outcome = 0; break
                    if candle["low"] <= tp_price: outcome = 1; break
            
            # --- B. FEATURE ENGINEERING (Delegado a features.py) ---
            # AQUÍ ESTÁ EL AHORRO DE LÍNEAS:
            market_ctx = {
                'atr': current_market_data['ATR'],
                'ema_50': current_market_data['EMA_50'],
                'ema_200': current_market_data['EMA_200']
            }
            
            # Llamada mágica que calcula todo estándar
            features_df = build_features(current_market_data, row["entry_price"], market_ctx)
            features_dict = features_df.iloc[0].to_dict()

            # --- C. FUSIÓN ---
            new_row = row.to_dict()
            new_row.update({'target': outcome})
            new_row.update(features_dict)
            
            processed_data.append(new_row)

        except Exception as e:
            continue

    if not processed_data:
        print("❌ Error: No se generaron datos.")
        return

    # Guardado
    df_final = pd.DataFrame(processed_data)
    output_path = "quant_lab/datasets/dataset_labeled.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_final.to_csv(output_path, index=False)

    print(f"✅ DATASET GENERADO: {len(df_final)} muestras.")
    print(f"📊 Win Rate Base: {(df_final['target'].sum() / len(df_final)) * 100:.2f}%")

if __name__ == "__main__":
    label_and_enrich_dataset()