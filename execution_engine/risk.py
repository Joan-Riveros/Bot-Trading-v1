import MetaTrader5 as mt5
import math


class RiskManager:
    """
    Gestor de Riesgo Institucional.
    Calcula el tamaño de posición dinámico basado en % de balance y volatilidad (SL).
    """

    def __init__(self, risk_percent=1.0, max_daily_loss=3.0):
        self.risk_percent = risk_percent
        self.max_daily_loss = max_daily_loss

    def get_lot_size(self, entry_price, sl_price, symbol):
        """
        Calcula lotaje para arriesgar exactamente X% de la cuenta.
        Fórmula: Riesgo_Dinero / (Distancia_Precio * Valor_1_Punto)
        """
        # 1. Obtener Balance
        account_info = mt5.account_info()
        if account_info is None:
            print("❌ RiskManager: No se pudo obtener info de cuenta")
            return 0.01  # Retorno seguro por defecto

        balance = account_info.balance
        risk_amount = balance * (self.risk_percent / 100)

        # 2. Calcular Geometría del Trade
        dist_price = abs(entry_price - sl_price)
        if dist_price == 0:
            return 0.0

        # 3. Obtener Datos del Contrato (Tick Value)
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"❌ RiskManager: No info para {symbol}")
            return 0.01

        tick_value = symbol_info.trade_tick_value  # Valor de un tick ($)
        tick_size = symbol_info.trade_tick_size  # Tamaño de un tick (puntos)

        if tick_size == 0:
            return 0.01

        # Valor monetario de mover 1.00 de precio completo
        # Ej NQ: Si 0.25 pts valen $5, entonces 1.00 pts valen $20.
        point_value = tick_value * (1.0 / tick_size)

        if point_value == 0:
            return 0.01

        # 4. Cálculo del lote crudo
        # Fórmula: Dinero_Riesgo / (Distancia_Puntos * Valor_Por_Punto)
        raw_lot_size = risk_amount / (dist_price * point_value)

        # 5. Normalización (Institutional Grade)
        step = symbol_info.volume_step
        if step == 0:
            return 0.01

        # Redondeo hacia ABAJO (math.floor) para nunca exceder el riesgo
        # Matemáticamente: (1.237 / 0.01) = 123.7 -> floor -> 123 -> * 0.01 -> 1.23
        lot_size = math.floor(raw_lot_size / step) * step
        lot_size = round(lot_size, 2)  # Limpieza final de decimales flotantes

        # 6. Límites del Broker
        lot_size = max(lot_size, symbol_info.volume_min)
        lot_size = min(lot_size, symbol_info.volume_max)

        # Debug Log (Opcional, para ver qué calcula)
        # print(f"Risk calc: ${risk_amount:.2f} risk / ({dist_price:.2f} dist * ${point_value} val) = {lot_size} lots")

        return lot_size

    def check_daily_drawdown(self):
        # TODO: Implementar en v2 leyendo historial de deals del día
        return True
