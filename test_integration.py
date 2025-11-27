import pandas as pd
import os
from data_core.indicators import Indicators
from data_core.po3_logic import PO3Detector

# Configuración visual para la terminal
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)


def run_test():
    print("🔬 INICIANDO TEST DE INTEGRACIÓN (SPRINT 1)...")

    # 1. CARGAR DATOS (Trabajo de Dev B)
    csv_path = "data_core/datasets/SYNC_DATA_M1.csv"
    if not os.path.exists(csv_path):
        print(f"❌ Error: No encuentro {csv_path}. Ejecuta el miner primero.")
        return

    print(f"📂 Cargando datos minados: {csv_path}")
    df = pd.read_csv(csv_path, index_col="time", parse_dates=True)

    # ---------------------------------------------------------
    # ADAPTADOR DE INTEGRACIÓN (El Puente Dev B <-> Dev A)
    # ---------------------------------------------------------
    # El código de Dev A espera 'high', 'low', etc. Nosotros tenemos 'nq_high'.
    # Creamos un DF de trabajo solo para el NQ.
    df_logic = df.copy()
    df_logic.rename(
        columns={
            "nq_open": "open",
            "nq_high": "high",
            "nq_low": "low",
            "nq_close": "close",
            "nq_vol": "volume",
        },
        inplace=True,
    )
    # ---------------------------------------------------------

    # 2. CALCULAR INDICADORES (Trabajo de Dev A)
    print("🧮 Calculando Fractales, ATR y Midnight Open...")
    indicator_engine = Indicators()
    df_processed = indicator_engine.add_all_features(df_logic)

    # Verificación rápida de columnas
    required_cols = [
        "is_swing_high",
        "target_liquidity_high",
        "midnight_open",
        "ATRr_14",
    ]
    missing = [c for c in required_cols if c not in df_processed.columns]
    if missing:
        print(f"❌ Error Crítico: Faltan columnas generadas: {missing}")
        return
    else:
        print("✅ Indicadores generados correctamente.")

    # 3. ESCANEAR SEÑALES PO3 (Trabajo de Dev A)
    print("🕵️‍♂️ Escaneando patrones PO3 (Sweep + BOS + FVG)...")
    detector = PO3Detector(df_processed)

    signals_found = []

    # Escaneamos las últimas 5000 velas para no tardar una eternidad en el test
    # (En producción esto se hace vela a vela en tiempo real)
    start_index = len(df_processed) - 5000
    if start_index < 0:
        start_index = 0

    for i in range(start_index, len(df_processed)):
        signal = detector.scan_for_signals(i)
        if signal:
            # Añadimos la fecha para referencia humana
            signal["date"] = df_processed.index[i]
            signals_found.append(signal)

    # 4. REPORTE DE RESULTADOS
    print("\n---------------------------------------------------")
    print(
        f"📊 RESUMEN DE SEÑALES EN LAS ÚLTIMAS {len(df_processed) - start_index} VELAS"
    )
    print("---------------------------------------------------")

    if not signals_found:
        print("⚠️ No se encontraron señales perfectas.")
        print("Posibles causas: Mercado muy lateral o reglas muy estrictas.")
        print("Sugerencia: Revisa si el 'Scan Window' en po3_logic.py es muy corto.")
    else:
        print(f"🚀 ¡ÉXITO! Se encontraron {len(signals_found)} señales PO3 válidas.")
        print("\nEjemplos encontrados:")
        for s in signals_found[-5:]:  # Mostrar las últimas 5
            print(
                f"📅 {s['date']} | Tipo: {s['signal_type']} | Entry: {s['entry_price']:.2f} | TP: {s['take_profit']:.2f}"
            )

        # Guardar dataset de candidatos para el Sprint 2 (ML)
        print(
            f"\n💾 Guardando {len(signals_found)} candidatos para el Sprint 2 de IA..."
        )
        # (Aquí iría la lógica de guardado, por ahora solo validamos)


if __name__ == "__main__":
    run_test()
