import pandas as pd
import os
import sys

# Truco para importar módulos hermanos desde otra carpeta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_core.indicators import Indicators
from data_core.po3_logic import PO3Detector


def build_candidates_dataset():
    print("🏭 INICIANDO FÁBRICA DE DATASET (SPRINT 2)...")

    # 1. Cargar Datos Raw
    input_path = "data_core/datasets/SYNC_DATA_M1.csv"
    if not os.path.exists(input_path):
        print("❌ No hay datos. Corre el miner primero.")
        return

    print(f"📂 Leyendo historial completo: {input_path}")
    df = pd.read_csv(input_path, index_col="time", parse_dates=True)

    # Adaptador de nombres (igual que en el test)
    df.rename(
        columns={
            "nq_open": "open",
            "nq_high": "high",
            "nq_low": "low",
            "nq_close": "close",
            "nq_vol": "volume",
        },
        inplace=True,
    )

    # 2. Calcular Indicadores
    print("🧮 Calculando features técnicas...")
    engine = Indicators()
    df = engine.add_all_features(df)

    # 3. Escaneo Masivo
    print("🕵️‍♂️ Buscando patrones en todo el historial (esto tomará unos segundos)...")
    detector = PO3Detector(df)

    candidates = []

    # Recorremos TODO el dataframe (dejando margen inicial de 100 velas)
    total_candles = len(df)
    for i in range(100, total_candles):
        signal = detector.scan_for_signals(i)

        if signal:
            # Aplanamos el diccionario para que sea una fila de CSV
            row = {
                "timestamp": df.index[i],
                "signal_type": signal["signal_type"],
                "entry_price": signal["entry_price"],
                "stop_loss": signal["stop_loss"],
                "take_profit": signal["take_profit"],
                "atr": signal["atr_context"],
                # --- FEATURES PARA LA IA (CONTEXTO) ---
                "hour": df.index[i].hour + df.index[i].minute / 60.0,
                "is_ny_session": 1
                if (9.5 <= (df.index[i].hour + df.index[i].minute / 60.0) <= 16.0)
                else 0,
                "distance_to_ema50": df["close"].iloc[i] - df["ema_50"].iloc[i],
                "trend_ema200": 1
                if df["close"].iloc[i] > df["ema_200"].iloc[i]
                else -1,
                "volatility_shock": 1
                if (df["high"].iloc[i] - df["low"].iloc[i])
                > (signal["atr_context"] * 1.5)
                else 0,
            }
            candidates.append(row)

        # Barra de progreso simple
        if i % 10000 == 0:
            print(f"   ... procesado {i}/{total_candles} velas")

    # 4. Guardar
    if not candidates:
        print("⚠️ No se encontraron candidatos en todo el historial.")
        return

    df_candidates = pd.DataFrame(candidates)
    output_path = "quant_lab/datasets/candidates_unlabeled.csv"

    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    df_candidates.to_csv(output_path, index=False)

    print("\n------------------------------------------------")
    print(f"✅ DATASET GENERADO: {output_path}")
    print(f"📊 Total Candidatos: {len(df_candidates)}")
    print("------------------------------------------------")
    print(
        "Siguiente paso: Ejecutar labeler.py para decir cuáles ganaron y cuáles perdieron."
    )


if __name__ == "__main__":
    build_candidates_dataset()
