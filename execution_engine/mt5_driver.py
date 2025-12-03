import MetaTrader5 as mt5
import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from execution_engine.risk import RiskManager


class MT5Driver:
    def __init__(self, symbol: str = None):
        load_dotenv()
        self.symbol = symbol if symbol else os.getenv("SYMBOL_NQ", "USTEC")
        # --- NUEVO: Cargamos también el nombre del SP500 ---
        self.symbol_es = os.getenv("SYMBOL_ES", "US500")

        if not mt5.initialize():
            print(f"❌ Error Crítico MT5: {mt5.last_error()}")
            mt5_path = os.getenv("MT5_PATH")
            if mt5_path and not mt5.initialize(path=mt5_path):
                print("⚠ Advertencia: No se pudo iniciar MetaTrader 5")

        # Verificar ambos símbolos
        for sym in [self.symbol, self.symbol_es]:
            if mt5.terminal_info() and not mt5.symbol_select(sym, True):
                print(f"❌ Error: Símbolo '{sym}' no encontrado en Market Watch.")

        self.risk_manager = RiskManager()
        print(f"🚜 MT5 Driver Activo | NQ: {self.symbol} | ES: {self.symbol_es}")

    def get_market_data(self, timeframe=mt5.TIMEFRAME_M1, n_candles=500):
        """Descarga velas para el NQ (Principal)"""
        if not mt5.terminal_info() and not mt5.initialize():
            return None
        rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, n_candles)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)
        if "tick_volume" in df.columns:
            df.rename(columns={"tick_volume": "volume"}, inplace=True)
        return df

    # --- NUEVO MÉTODO RÁPIDO ---
    def get_current_price(self, symbol):
        """Obtiene el precio actual (Bid) de cualquier símbolo"""
        if not mt5.terminal_info() and not mt5.initialize():
            return 0.0
        tick = mt5.symbol_info_tick(symbol)
        return tick.bid if tick else 0.0

    def place_limit_order(self, signal_type, entry, sl, tp, expiration_minutes=45):
        # ... (El código de órdenes se mantiene igual que antes) ...
        # Copia el método place_limit_order de tu versión anterior si lo necesitas,
        # o usa el del mensaje anterior. Aquí lo resumo para brevedad.
        lot = self.risk_manager.calculate_lot_size(entry, sl, self.symbol)
        if lot == 0.0:
            return None

        order_type = (
            mt5.ORDER_TYPE_BUY_LIMIT
            if signal_type == "BULLISH"
            else mt5.ORDER_TYPE_SELL_LIMIT
        )
        expiration = int(
            (datetime.now() + timedelta(minutes=expiration_minutes)).timestamp()
        )

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
            "comment": "PO3_AI",
            "type_time": mt5.ORDER_TIME_SPECIFIED,
            "expiration": expiration,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        res = mt5.order_send(request)
        if res.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Error MT5: {res.comment}")
            return None
        print(f"✅ ORDEN: {signal_type} {lot} lots")
        return res.order

    def close_all_positions(self):
        # ... (Igual que antes) ...
        if not mt5.initialize():
            return
        # Cerrar todo para NQ
        self._close_symbol(self.symbol)

    def _close_symbol(self, sym):
        # Helper para cerrar
        orders = mt5.orders_get(symbol=sym)
        if orders:
            for o in orders:
                mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket})
        positions = mt5.positions_get(symbol=sym)
        if positions:
            for p in positions:
                type_c = (
                    mt5.ORDER_TYPE_SELL
                    if p.type == mt5.ORDER_TYPE_BUY
                    else mt5.ORDER_TYPE_BUY
                )
                price = (
                    mt5.symbol_info_tick(sym).bid
                    if type_c == mt5.ORDER_TYPE_SELL
                    else mt5.symbol_info_tick(sym).ask
                )
                mt5.order_send(
                    {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": sym,
                        "volume": p.volume,
                        "type": type_c,
                        "position": p.ticket,
                        "price": price,
                    }
                )
