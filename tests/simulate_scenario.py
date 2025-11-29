import sys
import os
import pandas as pd
import pytz
from datetime import datetime

# 1. Configurar rutas para importar los módulos del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_core.indicators import Indicators
from data_core.po3_logic import PO3Detector
from execution_engine.bot_manager import BotManager


def run_simulation():
    print("🕵️‍♂️ INICIANDO SIMULACIÓN FORENSE...")
    print("---------------------------------------")

    # 2. Cargar Datos Históricos (Los que bajaste con el miner)
    data_path = "data_core/datasets/SYNC_DATA_M1.csv"
    if not os.path.exists(data_path):
        print("❌ No se encontró SYNC_DATA_M1.csv. Ejecuta el miner primero.")
        return

    print(f"📂 Cargando historial: {data_path}")
    df = pd.read_csv(data_path, index_col="time", parse_dates=True)

    # Adaptador de columnas (Infraestructura -> Lógica)
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

    # 3. Inicializar Componentes Reales
    # Instanciamos el BotManager para usar SU cerebro (IA) y SU lógica de features
    # Esto asegura que la simulación sea idéntica a la realidad.
    print("🧠 Inicializando Motores e IA...")
    bot = BotManager()
    indicators = Indicators()

    # 4. Preparar Datos
    print("🧮 Calculando Indicadores Técnicos...")
    df = indicators.add_all_features(df)

    # 5. Escaneo Retrospectivo (Back-Scan)
    # Miramos las últimas 5000 velas (aprox 3.5 días)
    lookback = 5000
    start_index = len(df) - lookback
    if start_index < 0:
        start_index = 0

    print(f"🔎 Escaneando desde la vela {start_index} hasta {len(df)}...")

    detector = PO3Detector(df)
    found_count = 0

    for i in range(start_index, len(df) - 1):
        # Escanear vela histórica
        signal = detector.scan_for_signals(i)

        if signal:
            found_count += 1
            # --- Aquí ocurre la Magia de la Simulación ---

            # A. Pasamos la señal por la IA (usando la lógica del BotManager)
            # Reconstruimos features para ese momento exacto del pasado
            # Necesitamos cortar el DF hasta ese punto para simular "tiempo real"
            df_slice = df.iloc[: i + 2]  # +2 para incluir la vela cerrada y contexto
            features = bot._prepare_features_for_ai(signal, df_slice)

            try:
                prob = bot.model.predict_proba(features)[0][1]
            except:
                prob = 0.0

            # B. Evaluamos si hubiera disparado
            if prob >= bot.threshold:
                print("\n==================================================")
                print("✅ ¡MATCH CONFIRMADO! EL BOT HUBIERA DISPARADO")
                print("==================================================")
                print(f"📅 Fecha Señal: {signal['timestamp']}")
                print(f"💎 Tipo: {signal['signal_type']}")
                print(f"📉 Entrada: {signal['entry_price']:.2f}")
                print(f"🎯 Take Profit: {signal['take_profit']:.2f}")
                print(f"🛑 Stop Loss: {signal['stop_loss']:.2f}")
                print(f"🤖 Confianza IA: {prob:.2%} (Umbral: {bot.threshold:.2%})")

                # C. Simulamos el Riesgo (Llamamos al RiskManager real del Driver)
                lot_size = bot.driver.risk_manager.get_lot_size(
                    signal["entry_price"], signal["stop_loss"], bot.driver.symbol
                )
                print(f"💰 Gestión de Riesgo: Se enviarían {lot_size} lotes")
                print("--------------------------------------------------")

                # Opcional: Detenerse al encontrar el primero para no saturar
                # return

    print(
        f"\n🏁 Simulación terminada. Se detectaron {found_count} patrones totales en la muestra."
    )
    if found_count > 0:
        print("Nota: Solo se muestran arriba los que pasaron el filtro de IA.")
    else:
        print("⚠️ No se encontraron patrones geométricos en este periodo.")


if __name__ == "__main__":
    run_simulation()
