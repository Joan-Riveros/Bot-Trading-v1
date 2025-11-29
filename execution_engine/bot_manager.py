import asyncio
import pandas as pd
import xgboost as xgb
import json
import os
import sys
import pytz
from datetime import datetime

# Imports relativos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from data_core.indicators import Indicators
from data_core.po3_logic import PO3Detector
from execution_engine.mt5_driver import MT5Driver


class BotManager:
    def __init__(self):
        self.is_running = False
        # El driver maneja la conexión a MT5
        self.driver = MT5Driver()

        self.logs = []
        self.latest_status = "IDLE"
        self.ny_tz = pytz.timezone("America/New_York")

        # Cargar IA
        self.model = xgb.XGBClassifier()
        self.threshold = 0.70
        self.indicators = Indicators()

        self._load_brain()

    def _load_brain(self):
        model_path = "quant_lab/models/po3_sniper_v1.json"
        config_path = "quant_lab/models/model_config.json"

        if os.path.exists(model_path):
            try:
                self.model.load_model(model_path)
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        conf = json.load(f)
                        self.threshold = conf.get("threshold", 0.70)
                self.log(f"🧠 IA Cargada. Umbral: {self.threshold:.2%}")
            except Exception as e:
                self.log(f"❌ Error cargando IA: {e}")
        else:
            self.log("⚠ ALERTA: No hay modelo IA. Operando sin filtro inteligente.")

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        fmsg = f"[{timestamp}] {msg}"
        print(fmsg)
        self.logs.append(fmsg)
        if len(self.logs) > 100:
            self.logs.pop(0)
        self.latest_status = msg

    async def start_loop(self):
        self.is_running = True
        self.log(f"🚀 MOTOR INICIADO. Escaneando {self.driver.symbol}...")

        while self.is_running:
            try:
                # 1. OBTENCIÓN DE DATOS (Delegada al Driver)
                # El Driver ya nos devuelve un DF con Index=Datetime
                df = self.driver.get_market_data(n_candles=500)

                if df is not None and len(df) > 100:
                    # 2. INDICADORES
                    df = self.indicators.add_all_features(df)

                    # 3. LÓGICA PO3
                    last_idx = len(df) - 2  # Vela confirmada
                    detector = PO3Detector(df)
                    signal = detector.scan_for_signals(last_idx)

                    current_price = df["close"].iloc[-1]
                    if not signal:
                        self.latest_status = (
                            f"Escaneando... Precio: {current_price:.2f}"
                        )

                    if signal:
                        msg = f"🔎 Patrón {signal['signal_type']} detectado @ {signal['entry_price']}"
                        if not self.logs or msg not in self.logs[-1]:
                            self.log(msg)

                        # 4. INTELIGENCIA ARTIFICIAL
                        should_trade = False

                        if self.model:
                            features = self._prepare_features_for_ai(signal, df)
                            try:
                                prob = self.model.predict_proba(features)[0][1]
                                if prob >= self.threshold:
                                    self.log(
                                        f"✅ IA APROBADO ({prob:.1%}). EJECUTANDO SNIPER..."
                                    )
                                    should_trade = True
                                else:
                                    self.log(
                                        f"🛡 IA RECHAZADO ({prob:.1%}). (Req: {self.threshold:.1%})"
                                    )
                            except Exception as e:
                                self.log(f"❌ Error IA: {e}")
                                should_trade = False
                        else:
                            should_trade = True  # Sin IA, operamos la señal pura

                        # 5. EJECUCIÓN
                        if should_trade:
                            order = self.driver.place_limit_order(
                                signal["signal_type"],
                                signal["entry_price"],
                                signal["stop_loss"],
                                signal["take_profit"],
                            )

                            if order:
                                self.log(f"🎫 Orden Ticket: {order}")
                                await asyncio.sleep(60)  # Cooldown

            except Exception as e:
                self.log(f"❌ Error Loop Crítico: {e}")
                import traceback

                traceback.print_exc()
                await asyncio.sleep(5)

            await asyncio.sleep(5)  # Polling

    def _prepare_features_for_ai(self, signal, df):
        """Reconstruye el vector de características para la IA"""
        idx = len(df) - 2
        row = df.iloc[idx]

        # --- FIX PARA DATETIME INDEX ---
        # Como el driver hizo set_index('time'), el tiempo ahora es row.name
        # NO BUSCAR row['time'] porque esa columna ya no existe.
        timestamp = row.name

        # Gestión de Timezones
        if timestamp.tzinfo is None:
            current_time_utc = timestamp.replace(tzinfo=pytz.utc)
        else:
            current_time_utc = timestamp.astimezone(pytz.utc)

        current_time_ny = current_time_utc.astimezone(self.ny_tz)
        feat_hour = current_time_ny.hour  # ENTERO, igual que en labeler.py

        atr_val = row["ATRr_14"] if row["ATRr_14"] > 0 else 1.0
        entry_price = signal["entry_price"]

        # DataFrame con orden de columnas forzado para seguridad de XGBoost
        data = {
            "hour": feat_hour,
            "is_ny_session": 1 if (9 <= feat_hour < 16) else 0,
            "distance_to_ema50": (entry_price - row["ema_50"]) / atr_val,
            "trend_ema200": 1 if entry_price > row["ema_200"] else 0,
            "volatility_shock": (row["high"] - row["low"]) / atr_val,
        }

        # Orden explícito de columnas
        cols_order = [
            "hour",
            "is_ny_session",
            "distance_to_ema50",
            "trend_ema200",
            "volatility_shock",
        ]
        return pd.DataFrame([data])[cols_order]

    def stop(self):
        self.is_running = False
        self.log("🛑 Sistema Detenido.")

    def panic(self):
        self.stop()
        self.driver.close_all_positions()
        self.log("🚨 PÁNICO EJECUTADO: Todo cerrado.")
