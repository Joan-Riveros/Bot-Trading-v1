import pandas as pd
import os
from datetime import timedelta


def label_dataset():
    print("⚖️ INICIANDO PROCESO DE ETIQUETADO (LABELING)...")

    # 1. Cargar Candidatos y Datos Crudos (Para ver el futuro)
    candidates_path = "quant_lab/datasets/candidates_unlabeled.csv"
    raw_data_path = "data_core/datasets/SYNC_DATA_M1.csv"

    if not os.path.exists(candidates_path) or not os.path.exists(raw_data_path):
        print("❌ Faltan archivos. Asegúrate de haber corrido build_dataset.py")
        return

    print("📂 Cargando archivos...")
    df_candidates = pd.read_csv(candidates_path)
    # Parseamos fechas explícitamente
    df_candidates["timestamp"] = pd.to_datetime(
        df_candidates["timestamp"], utc=True
    ).dt.tz_localize(None)

    df_raw = pd.read_csv(raw_data_path, index_col="time", parse_dates=True)
    df_raw.index = pd.to_datetime(df_raw.index, utc=True).tz_localize(None)
    # Renombrar para facilitar acceso (solo necesitamos precios del NQ)
    df_raw.rename(columns={"nq_high": "high", "nq_low": "low"}, inplace=True)

    print(f"🧐 Evaluando {len(df_candidates)} trades con regla: TP en < 45 mins...")

    labels = []

    # Configuración de límite de tiempo (Time Decay)
    MAX_HOLDING_TIME = timedelta(minutes=45)

    for i, row in df_candidates.iterrows():
        entry_time = row["timestamp"]
        exit_deadline = entry_time + MAX_HOLDING_TIME

        entry_price = row["entry_price"]
        tp_price = row["take_profit"]
        sl_price = row["stop_loss"]
        signal_type = row["signal_type"]

        # Recortamos el futuro: Desde la entrada hasta 45 mins después
        # Usamos try/except por si la fecha se sale del historial
        try:
            future_window = df_raw.loc[entry_time:exit_deadline]
        except KeyError:
            labels.append(0)  # Si no hay datos futuros, asumimos 0 por seguridad
            continue

        if future_window.empty:
            labels.append(0)
            continue

        outcome = 0  # Asumimos derrota hasta demostrar lo contrario

        # Lógica de Evaluación Vela a Vela
        for t, candle in future_window.iterrows():
            # Saltamos la vela de entrada exacta para evitar auto-cumplimiento inmediato
            if t == entry_time:
                continue

            if signal_type == "BULLISH":
                # 1. ¿Tocó SL? (Prioridad al riesgo: Si en la misma vela toca SL y TP, es SL)
                if candle["low"] <= sl_price:
                    outcome = 0  # LOSS
                    break
                # 2. ¿Tocó TP?
                if candle["high"] >= tp_price:
                    outcome = 1  # WIN
                    break

            elif signal_type == "BEARISH":
                # 1. ¿Tocó SL?
                if candle["high"] >= sl_price:
                    outcome = 0  # LOSS
                    break
                # 2. ¿Tocó TP?
                if candle["low"] <= tp_price:
                    outcome = 1  # WIN
                    break

        # Si termina el loop y no tocó nada (Time Out), outcome se queda en 0.
        labels.append(outcome)

        if i % 500 == 0:
            print(f"   ... evaluado {i}/{len(df_candidates)}")

    # 3. Guardar Dataset Final
    df_candidates["target"] = labels

    output_path = "quant_lab/datasets/dataset_labeled.csv"
    df_candidates.to_csv(output_path, index=False)

    # 4. Estadísticas del "Motor Determinista" (Sin IA)
    total = len(df_candidates)
    wins = sum(labels)
    win_rate = (wins / total) * 100

    print("\n------------------------------------------------")
    print(f"✅ ETIQUETADO FINALIZADO: {output_path}")
    print(f"📊 Estadísticas Base (Sin Inteligencia Artificial):")
    print(f"   Total Trades: {total}")
    print(f"   Wins (TP < 45m): {wins}")
    print(f"   Losses/TimeOut: {total - wins}")
    print(f"   WIN RATE BASE: {win_rate:.2f}%")
    print("------------------------------------------------")

    if win_rate < 30:
        print("⚠️ ALERTA: El Win Rate base es bajo. La IA tendrá que filtrar mucho.")
    elif win_rate > 45:
        print("🚀 EXCELENTE: La estrategia base ya es muy sólida.")


if __name__ == "__main__":
    label_dataset()
