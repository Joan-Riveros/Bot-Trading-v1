import pandas as pd
import numpy as np
import os
from datetime import timedelta
import pandas_ta as ta
import pytz


def label_and_enrich_dataset():
    print("⚖ INICIANDO ETIQUETADO E INGENIERÍA DE FEATURES...")

    # RUTA DE ENTRADA 1: Los candidatos detectados
    candidates_path = "quant_lab/datasets/candidates_unlabeled.csv"

    # RUTA DE ENTRADA 2: Los datos crudos del minero (CORREGIDA)
    raw_data_path = "data_core/datasets/SYNC_DATA_M1.csv"

    if not os.path.exists(candidates_path):
        print(f"❌ Falta el archivo de candidatos: {candidates_path}")
        print(
            "💡 Pista: Ejecuta primero el script que detecta patrones (test_integration.py)."
        )
        return

    if not os.path.exists(raw_data_path):
        print(f"❌ Falta el archivo de datos crudos: {raw_data_path}")
        print("💡 Pista: Ejecuta data_core/miner.py")
        return

    # 1. Cargar Datos
    df_candidates = pd.read_csv(candidates_path)
    # Convertir a UTC explícito para evitar confusiones
    df_candidates["timestamp"] = pd.to_datetime(df_candidates["timestamp"], utc=True)

    print(f"📂 Cargando datos de mercado desde: {raw_data_path}")
    df_raw = pd.read_csv(raw_data_path, index_col="time", parse_dates=True)
    df_raw.index = pd.to_datetime(df_raw.index, utc=True)

    # --- CORRECCIÓN CRÍTICA: RENOMBRADO DE COLUMNAS ---
    # El minero entrega 'nq_close', pero ta-lib y nuestra lógica esperan 'close'.
    if "nq_close" in df_raw.columns:
        print("🔄 Adaptando formato de columnas (nq_close -> close)...")
        df_raw.rename(
            columns={
                "nq_open": "open",
                "nq_high": "high",
                "nq_low": "low",
                "nq_close": "close",
                "nq_vol": "volume",
            },
            inplace=True,
        )

    # 2. Cálculo de Indicadores (si faltan)
    if "ATR" not in df_raw.columns:
        print("⚙ Calculando indicadores técnicos para el contexto...")
        df_raw["EMA_50"] = ta.ema(df_raw["close"], length=50)
        df_raw["EMA_200"] = ta.ema(df_raw["close"], length=200)
        df_raw["ATR"] = ta.atr(
            df_raw["high"], df_raw["low"], df_raw["close"], length=14
        )

        # Corrección de "Look-ahead Bias" (Rellenar hacia adelante)
        df_raw.fillna(method="ffill", inplace=True)
        df_raw.dropna(inplace=True)  # Borrar las primeras filas donde no hay EMA200

    print(f"🧐 Procesando {len(df_candidates)} candidatos con datos sincronizados...")

    processed_data = []
    MAX_HOLDING_TIME = timedelta(minutes=45)  # Tiempo máximo de operación
    ny_tz = pytz.timezone("America/New_York")

    for i, row in df_candidates.iterrows():
        entry_time = row["timestamp"]

        # Verificar si tenemos datos para ese momento exacto
        if entry_time not in df_raw.index:
            continue

        try:
            current_market_data = df_raw.loc[entry_time]

            # Definir ventana futura para ver si ganamos o perdimos
            exit_deadline = entry_time + MAX_HOLDING_TIME
            future_window = df_raw.loc[entry_time:exit_deadline]

            if future_window.empty or len(future_window) < 2:
                continue

            # --- A. LABELING (¿Ganó o Perdió?) ---
            entry_price = row["entry_price"]
            tp_price = row["take_profit"]
            sl_price = row["stop_loss"]
            signal_type = row["signal_type"]

            outcome = 0  # 0 = Perdedor, 1 = Ganador

            # Recorremos el futuro vela a vela (Skip vela 0)
            for t, candle in future_window.iloc[1:].iterrows():
                if signal_type == "BULLISH":
                    if candle["low"] <= sl_price:  # Tocó SL
                        outcome = 0
                        break
                    if candle["high"] >= tp_price:  # Tocó TP
                        outcome = 1
                        break
                elif signal_type == "BEARISH":
                    if candle["high"] >= sl_price:  # Tocó SL
                        outcome = 0
                        break
                    if candle["low"] <= tp_price:  # Tocó TP
                        outcome = 1
                        break

            # --- B. FEATURE ENGINEERING (Datos para la IA) ---

            # 1. Hora Local NY (Vital para aprender sesiones)
            entry_time_ny = entry_time.astimezone(ny_tz)
            feat_hour = entry_time_ny.hour
            feat_is_ny = 1 if (9 <= feat_hour < 16) else 0  # Session Open

            # 2. Contexto de Tendencia y Volatilidad
            atr_val = (
                current_market_data["ATR"] if current_market_data["ATR"] > 0 else 1.0
            )

            # Distancia a la EMA50 normalizada por volatilidad
            dist_ema50 = (entry_price - current_market_data["EMA_50"]) / atr_val

            feat_trend = 1 if entry_price > current_market_data["EMA_200"] else 0

            # Shock: Tamaño de la vela de señal vs ATR promedio
            candle_range = current_market_data["high"] - current_market_data["low"]
            feat_shock = candle_range / atr_val

            # Guardamos la fila enriquecida
            new_row = row.to_dict()
            new_row.update(
                {
                    "target": outcome,
                    "hour": feat_hour,
                    "is_ny_session": feat_is_ny,
                    "distance_to_ema50": dist_ema50,
                    "trend_ema200": feat_trend,
                    "volatility_shock": feat_shock,
                }
            )

            processed_data.append(new_row)

        except Exception as e:
            # Ignoramos errores puntuales para no detener todo el proceso
            continue

    if not processed_data:
        print(
            "❌ Error: No se generaron datos procesados. Verifica que las fechas del CSV de candidatos coincidan con el CSV de mercado."
        )
        return

    # Guardar Dataset Final
    df_final = pd.DataFrame(processed_data)
    output_path = "quant_lab/datasets/dataset_labeled.csv"

    # Crear carpeta si no existe
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    df_final.to_csv(output_path, index=False)

    print(f"✅ DATASET LISTO: {len(df_final)} muestras guardadas en {output_path}")

    # Estadística rápida
    win_rate = (df_final["target"].sum() / len(df_final)) * 100
    print(f"📊 Win Rate Base (Sin IA): {win_rate:.2f}%")
    print("👉 Siguiente paso: Ejecuta 'quant_lab/train_xgb.py'")


if __name__ == "__main__":
    label_and_enrich_dataset()
