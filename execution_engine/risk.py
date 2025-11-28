# execution_engine/risk.py


class RiskManager:
    def __init__(self):
        # Aquí Dev A pondrá configuraciones de balance, % de riesgo, etc.
        pass

    def get_lot_size(self, entry_price: float, sl_price: float, symbol: str) -> float:
        """
        MOCK TEMPORAL (Para Dev B):
        Devuelve siempre 0.01 para probar que el servidor funciona.

        TODO: Dev A implementará aquí la fórmula de riesgo institucional:
        (Balance * 0.01) / (Distancia_SL * Tick_Value)
        """
        return 0.01
