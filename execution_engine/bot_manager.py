import asyncio
import pandas as pd
import xgboost as xgb
import json
import os
import sys
import pytz
from datetime import datetime

# Imports de módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from data_core.indicators import Indicators
from data_core.po3_logic import PO3Detector
from data_core.miner import get_data
from execution_engine.mt5_driver import MT5Driver


class BotManager:
    def __init__(self):
        self.is_running = False
        self.driver = MT5Driver()
        self.logs = []
        self.latest_status = "IDLE"
        self.ny_tz = pytz.timezone("America/New_York")

        # Cargar IA
        self.model = xgb.XGBClassifier()
        model_path = "quant_lab/models/po3_sniper_v1.json"
        self.threshold = 0.70  # Default seguro

        if os.path.exists(model_path):
            self.model.load_model(model_path)
            # Cargar Threshold óptimo
            config_path = "quant_lab/models/model_config.json"
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    conf = json.load(f)
                    self.threshold = conf.get("threshold", 0.70)
            self.log(f"🧠 IA Cargada. Umbral Operativo: {self.threshold:.2%}")
        else:
            self.log("⚠️ ALERTA: No hay modelo IA. El bot NO operará.")

    def log(self, msg):
        """Guarda logs en memoria para enviarlos por WebSocket"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        fmsg = f"[{timestamp}] {msg}"
        print(fmsg)
        self.logs.append(fmsg)
        if len(self.logs) > 50:
            self.logs.pop(0)

    async def start_loop(self):
        self.is_running = True
        self.log("🚀 SISTEMA INICIADO. Escaneando mercado...")

        while self.is_running:
            try:
                # 1. Obtener Datos (Polling cada 5s)
                # Nota: get_data descarga 500 velas recientes
                df = get_data(self.driver.symbol_nq, "M1", n=500)

                if df is not None and not df.empty:
                    # Adaptar columnas del miner para la lógica
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
                    engine = Indicators()
                    df = engine.add_all_features(df)

                    # 3. Detectar Patrón (Vela cerrada anterior)
                    last_idx = len(df) - 2
                    detector = PO3Detector(df)
                    signal = detector.scan_for_signals(last_idx)

                    current_price = df["close"].iloc[-1]
                    self.latest_status = f"Escaneando... Precio: {current_price:.2f}"

                    if signal:
                        self.log(
                            f"🔎 Patrón {signal['signal_type']} detectado @ {signal['entry_price']}"
                        )

                        # 4. Validar con IA (Feature Engineering en tiempo real)
                        row = df.iloc[last_idx]

                        # Hora NY
                        current_time_utc = row.name.replace(tzinfo=pytz.utc)
                        current_time_ny = current_time_utc.astimezone(self.ny_tz)
                        feat_hour = current_time_ny.hour + (
                            current_time_ny.minute / 60.0
                        )

                        # Normalización
                        atr_val = row["ATRr_14"] if row["ATRr_14"] > 0 else 1.0

                        features = pd.DataFrame(
                            [
                                {
                                    "hour": current_time_ny.hour,  # Ojo: Labeler usaba solo la hora entera
                                    "is_ny_session": 1
                                    if (9.5 <= feat_hour < 16)
                                    else 0,
                                    "distance_to_ema50": (
                                        signal["entry_price"] - row["ema_50"]
                                    )
                                    / atr_val,
                                    "trend_ema200": 1
                                    if signal["entry_price"] > row["ema_200"]
                                    else 0,
                                    "volatility_shock": (row["high"] - row["low"])
                                    / atr_val,
                                }
                            ]
                        )

                        prob = self.model.predict_proba(features)[0][1]

                        if prob >= self.threshold:
                            self.log(f"✅ IA APROBADO ({prob:.1%}). ENVIANDO ORDEN...")
                            self.driver.place_limit_order(
                                signal["signal_type"],
                                signal["entry_price"],
                                signal["stop_loss"],
                                signal["take_profit"],
                            )
                        else:
                            self.log(
                                f"🛑 IA RECHAZADO ({prob:.1%}). (Req: {self.threshold:.1%})"
                            )

            except Exception as e:
                self.log(f"❌ Error Loop: {e}")

            await asyncio.sleep(5)  # Espera no bloqueante

    def stop(self):
        self.is_running = False
        self.log("🛑 Sistema Detenido.")

    def panic(self):
        self.stop()
        self.driver.close_all_positions()
        self.log("🚨 PÁNICO: Cerrando todo.")
