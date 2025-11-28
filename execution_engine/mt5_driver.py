import MetaTrader5 as mt5
import os
from dotenv import load_dotenv
from execution_engine.risk import RiskManager  # Importamos el módulo de Dev A


class MT5Driver:
    def __init__(self):
        load_dotenv()
        self.symbol_nq = os.getenv("SYMBOL_NQ")
        self.risk_manager = RiskManager()  # Instanciamos el gestor de riesgo

        # Inicializar MT5 si no está conectado
        if not mt5.terminal_info():
            path = os.getenv("MT5_PATH")
            if not mt5.initialize(path=path):
                print(f"❌ Error MT5 Driver: {mt5.last_error()}")

    def place_limit_order(self, signal_type, entry, sl, tp):
        """Envía una orden usando el lotaje calculado por RiskManager"""

        # 1. Delegar el cálculo del lotaje al RiskManager
        lot = self.risk_manager.get_lot_size(entry, sl, self.symbol_nq)

        # 2. Configurar tipo de orden
        order_type = (
            mt5.ORDER_TYPE_BUY_LIMIT
            if signal_type == "BULLISH"
            else mt5.ORDER_TYPE_SELL_LIMIT
        )

        # 3. Construir Request
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.symbol_nq,
            "volume": lot,
            "type": order_type,
            "price": entry,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 888999,
            "comment": "PO3_AI_Sniper",
            "type_time": mt5.ORDER_TIME_SPECIFIED,
            "expiration": 0,  # (Pendiente: Expiración 45 min)
        }

        # 4. Enviar
        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Error MT5: {result.comment} ({result.retcode})")
            return None

        print(f"✅ ORDEN ENVIADA: {signal_type} {lot} lots @ {entry}")
        return result.order

    def close_all_positions(self):
        """PANIC BUTTON: Cierra todo"""
        positions = mt5.positions_get(symbol=self.symbol_nq)
        if positions:
            for pos in positions:
                type_close = (
                    mt5.ORDER_TYPE_SELL
                    if pos.type == mt5.ORDER_TYPE_BUY
                    else mt5.ORDER_TYPE_BUY
                )
                price = (
                    mt5.symbol_info_tick(self.symbol_nq).bid
                    if type_close == mt5.ORDER_TYPE_SELL
                    else mt5.symbol_info_tick(self.symbol_nq).ask
                )
                req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol_nq,
                    "volume": pos.volume,
                    "type": type_close,
                    "position": pos.ticket,
                    "price": price,
                    "magic": 888999,
                }
                mt5.order_send(req)
