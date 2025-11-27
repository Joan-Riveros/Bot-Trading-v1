import MetaTrader5 as mt5
import pandas as pd
import os
from datetime import datetime
import pytz
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
NQ_SYMBOL = os.getenv("SYMBOL_NQ", "USTEC")
ES_SYMBOL = os.getenv("SYMBOL_ES", "US500")
N_CANDLES = int(os.getenv("MAX_CANDLES", 100000))

# Mapeo de Timeframes de MT5
TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
}


def initialize_mt5():
    """Inicia la conexión con MT5"""
    if not mt5.initialize():
        print(f"❌ Error al iniciar MT5: {mt5.last_error()}")
        return False

    # Verificar si los símbolos existen
    for symbol in [NQ_SYMBOL, ES_SYMBOL]:
        selected = mt5.symbol_select(symbol, True)
        if not selected:
            print(
                f"❌ Error: No se pudo encontrar/seleccionar el símbolo {symbol}. Verifica el .env"
            )
            return False

    print(f"✅ Conexión MT5 establecida. Operando con: {NQ_SYMBOL} vs {ES_SYMBOL}")
    return True


def get_data(symbol, timeframe_str, n=N_CANDLES):
    """Descarga data cruda de un símbolo"""
    tf_mt5 = TIMEFRAMES[timeframe_str]

    # Copiar rates desde la posición actual hacia atrás
    rates = mt5.copy_rates_from_pos(symbol, tf_mt5, 0, n)

    if rates is None or len(rates) == 0:
        print(f"⚠️ No se recibieron datos para {symbol} en {timeframe_str}")
        return None

    # Convertir a DataFrame
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")

    # Limpieza básica
    df.drop(
        columns=["tick_volume", "spread", "real_volume"], inplace=True, errors="ignore"
    )
    df.rename(columns={"tick_volume": "vol"}, inplace=True)  # Si existe

    # Setear índice temporal para facilitar el JOIN
    df.set_index("time", inplace=True)
    return df


def sync_and_save_data():
    """Orquestador principal: Descarga, Sincroniza y Guarda"""

    # Crear carpeta de salida si no existe
    output_dir = os.path.join(os.path.dirname(__file__), "datasets")
    os.makedirs(output_dir, exist_ok=True)

    print(f"🚀 Iniciando minería de datos ({N_CANDLES} velas)...")

    for tf_name in TIMEFRAMES.keys():
        print(f"\n⏳ Procesando Timeframe: {tf_name}")

        # 1. Descargar NQ
        df_nq = get_data(NQ_SYMBOL, tf_name)
        if df_nq is None:
            continue

        # 2. Descargar ES
        df_es = get_data(ES_SYMBOL, tf_name)
        if df_es is None:
            continue

        # 3. SINCRONIZACIÓN (Inner Join)
        # Renombramos columnas para identificar activo: 'close' -> 'nq_close'
        df_nq_clean = df_nq.add_prefix("nq_")
        df_es_clean = df_es.add_prefix("es_")

        # El Inner Join alinea los índices (tiempo). Si falta una vela en uno, se borra en ambos.
        df_merged = df_nq_clean.join(df_es_clean, how="inner")

        # 4. Conversión de Zona Horaria (A New York - EST/EDT)
        # Asumimos que MT5 viene en UTC (o ajusta según tu broker).
        # La mayoría de brokers de CFDs usan UTC+2/UTC+3.
        # Aquí convertimos a 'US/Eastern' para que la lógica de las 09:30 funcione.
        # NOTA: Ajustar 'tz_localize' según la hora de TU servidor MT5.
        # Para MVP asumimos que el índice ya es datetime naive y lo tratamos como raw.

        # 5. Guardar CSV
        filename = f"SYNC_DATA_{tf_name}.csv"
        filepath = os.path.join(output_dir, filename)
        df_merged.to_csv(filepath)

        print(f"✅ Guardado: {filename} | Filas: {len(df_merged)} (Sincronizadas)")
        print(
            f"   Muestra: NQ Close {df_merged.iloc[-1]['nq_close']} | ES Close {df_merged.iloc[-1]['es_close']}"
        )

    mt5.shutdown()
    print("\n🏁 Proceso de minería finalizado con éxito.")


if __name__ == "__main__":
    if initialize_mt5():
        sync_and_save_data()
