import MetaTrader5 as mt5
import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from execution_engine.risk import RiskManager


class MT5Driver:
    def __init__(self, symbol: str = None):
        load_dotenv()
        # Prioridad: Argumento > .env > Default
        env_symbol = os.getenv("SYMBOL_NQ", "USTEC")
        self.symbol = symbol if symbol else env_symbol

        # Inicialización Robusta
        if not mt5.initialize():
            print(f"❌ Error Crítico MT5: {mt5.last_error()}")
            mt5_path = os.getenv("MT5_PATH")
            if mt5_path and not mt5.initialize(path=mt5_path):
                # Si falla, no crasheamos aquí, permitimos reintentos externos
                print("⚠ Advertencia: No se pudo iniciar MetaTrader 5 en _init_")

        # Intentar seleccionar símbolo si MT5 está vivo
        if mt5.terminal_info():
            if not mt5.symbol_select(self.symbol, True):
                print(
                    f"❌ Error: Símbolo '{self.symbol}' no encontrado en Market Watch."
                )

        self.risk_manager = RiskManager()
        print(f"🚜 MT5 Driver Activo | Operando: {self.symbol}")

    def get_market_data(self, timeframe=mt5.TIMEFRAME_M1, n_candles=500):
        """
        Centraliza la obtención de datos.
        Devuelve un DataFrame limpio con DATETIME INDEX.
        """
        # Asegurar conexión antes de pedir datos
        if not mt5.terminal_info():
            if not mt5.initialize():
                return None

        rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, n_candles)

        if rates is None or len(rates) == 0:
            return None

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")

        # --- FIX CRÍTICO: ESTABLECER EL ÍNDICE TEMPORAL ---
        # Sin esto, indicators.py falla con "RangeIndex has no attribute tz"
        df.set_index("time", inplace=True)

        # Estandarización para compatibilidad
        if "tick_volume" in df.columns:
            df.rename(columns={"tick_volume": "volume"}, inplace=True)

        return df

    def place_limit_order(self, signal_type, entry, sl, tp, expiration_minutes=45):
        """Coloca orden pendiente con gestión de riesgo"""

        # 1. Calcular Riesgo
        lot = self.risk_manager.calculate_lot_size(entry, sl, self.symbol)

        if lot == 0.0:
            print(
                "⚠ Orden rechazada: Lotaje 0 (Riesgo alto/Balance bajo/Mercado cerrado)."
            )
            return None

        # 2. Configurar Orden
        order_type = (
            mt5.ORDER_TYPE_BUY_LIMIT
            if signal_type == "BULLISH"
            else mt5.ORDER_TYPE_SELL_LIMIT
        )

        expiration_time = datetime.now() + timedelta(minutes=expiration_minutes)
        expiration_timestamp = int(expiration_time.timestamp())

        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.symbol,
            "volume": lot,
            "type": order_type,
            "price": entry,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 123456,
            "comment": "PO3_AI_Sniper",
            "type_time": mt5.ORDER_TIME_SPECIFIED,
            "expiration": expiration_timestamp,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        # 3. Enviar
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Error MT5: {result.comment} ({result.retcode})")
            return None

        print(f"✅ ORDEN PENDIENTE: {signal_type} | {lot} Lots @ {entry}")
        return result.order

    def close_all_positions(self):
        """PÁNICO: Cierra todo"""
        print("🚨 EJECUTANDO PROTOCOLO DE PÁNICO...")

        if not mt5.initialize():
            return

        # 1. Borrar Pendientes
        orders = mt5.orders_get(symbol=self.symbol)
        if orders:
            for order in orders:
                mt5.order_send(
                    {"action": mt5.TRADE_ACTION_REMOVE, "order": order.ticket}
                )

        # 2. Cerrar Activas
        positions = mt5.positions_get(symbol=self.symbol)
        if positions:
            for pos in positions:
                type_close = (
                    mt5.ORDER_TYPE_SELL
                    if pos.type == mt5.ORDER_TYPE_BUY
                    else mt5.ORDER_TYPE_BUY
                )

                tick = mt5.symbol_info_tick(self.symbol)
                if tick is None:
                    continue

                price = tick.bid if type_close == mt5.ORDER_TYPE_SELL else tick.ask

                req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": pos.volume,
                    "type": type_close,
                    "position": pos.ticket,
                    "price": price,
                    "magic": 123456,
                    "comment": "PANIC EXIT",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                mt5.order_send(req)
            print(f"💥 {len(positions)} posiciones cerradas.")
        else:
            print("ℹ Sin posiciones abiertas.")
