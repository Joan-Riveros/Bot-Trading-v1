import pandas as pd
import numpy as np
import xgboost as xgb
import json
import os
import sys
from datetime import timedelta

# Imports del sistema para encontrar módulos hermanos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data_core.po3_logic import PO3Detector
from data_core.indicators import Indicators

# Intentar importar la librería de features centralizada
try:
    from quant_lab.features import build_features
except ImportError:
    print("❌ Error: No se encontró quant_lab/features.py")
    sys.exit(1)

class Backtester:
    def __init__(self, data_path, model_path, config_path):
        self.data_path = data_path
        self.model = xgb.XGBClassifier()
        self.model.load_model(model_path)
        
        with open(config_path, 'r') as f:
            conf = json.load(f)
            self.threshold = conf.get("threshold", 0.70)
            
        print(f"🤖 Backtester Iniciado. Umbral IA: {self.threshold:.2%}")
        
        # Estadísticas
        self.trades = []
        self.balance = 10000.0 # Balance inicial simulado
        self.equity_curve = [10000.0]

    def load_and_prep_data(self):
        print("📂 Cargando datos de prueba...")
        if not os.path.exists(self.data_path):
            print(f"❌ Error: No existe {self.data_path}")
            return None

        df = pd.read_csv(self.data_path, index_col="time", parse_dates=True)
        
        # Normalizar nombres
        if 'nq_close' in df.columns:
            df.rename(columns={'nq_open': 'open', 'nq_high': 'high', 'nq_low': 'low', 
                               'nq_close': 'close', 'nq_vol': 'volume'}, inplace=True)
        
        # Calcular Indicadores
        print("⚙️ Calculando indicadores...")
        indicators = Indicators()
        df = indicators.add_all_features(df)
        return df

    def run(self):
        df = self.load_and_prep_data()
        if df is None: return

        print(f"🏎️ Corriendo simulación sobre {len(df)} velas...")
        detector = PO3Detector(df)
        
        for i in range(50, len(df)):
            # 1. Detectar Señal
            signal = detector.scan_for_signals(i)
            
            if signal:
                # 2. Consultar a la IA
                row = df.iloc[i]
                market_ctx = {
                    'atr': row.get('ATRr_14', 1.0),
                    'ema_50': row.get('ema_50', 0.0),
                    'ema_200': row.get('ema_200', 0.0)
                }
                
                features = build_features(row, signal['entry_price'], market_ctx)
                
                try:
                    prob = self.model.predict_proba(features)[0][1]
                except:
                    prob = 0.0

                # 3. Decisión de Trading
                if prob >= self.threshold:
                    result = self._simulate_trade_outcome(df, i, signal)
                    self._record_trade(signal, result, prob)

        self._export_results()

    def _simulate_trade_outcome(self, df, entry_idx, signal):
        entry_price = signal['entry_price']
        tp = signal['take_profit']
        sl = signal['stop_loss']
        direction = signal['signal_type']
        
        max_holding = 45 # minutos
        pnl = 0.0
        risk_money = 100.0 # Riesgo fijo por trade
        
        future_df = df.iloc[entry_idx + 1 : entry_idx + 1 + max_holding]
        
        for _, candle in future_df.iterrows():
            if direction == "BULLISH":
                if candle['low'] <= sl: pnl = -risk_money; break
                if candle['high'] >= tp: pnl = risk_money * 2; break
            elif direction == "BEARISH":
                if candle['high'] >= sl: pnl = -risk_money; break
                if candle['low'] <= tp: pnl = risk_money * 2; break
        
        return pnl

    def _record_trade(self, signal, pnl, prob):
        self.balance += pnl
        self.equity_curve.append(self.balance)
        self.trades.append({
            "time": str(signal['timestamp']),
            "type": signal['signal_type'],
            "prob": round(prob * 100, 2), # Porcentaje limpio
            "pnl": round(pnl, 2),
            "result": "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "TIMEOUT"
        })

    def _export_results(self):
        total_trades = len(self.trades)
        wins = len([t for t in self.trades if t['pnl'] > 0])
        losses = len([t for t in self.trades if t['pnl'] < 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        net_profit = self.balance - 10000.0

        print("\n" + "="*40)
        print(f"📊 RESULTADO FINAL: {win_rate:.2f}% Win Rate | ${net_profit:.2f} Profit")
        print("="*40)

        # JSON para el Frontend
        export_data = {
            "summary": {
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 2),
                "final_balance": round(self.balance, 2),
                "net_profit": round(net_profit, 2)
            },
            "recent_trades": self.trades[-20:] # Últimos 20 trades
        }

        # Guardar donde el server.py pueda leerlo
        output_file = "execution_engine/backtest_results.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=4)
            
        print(f"💾 Reporte generado para Flutter: {output_file}")

if __name__ == "__main__":
    data_file = "data_core/datasets/SYNC_DATA_M1.csv"
    model_file = "quant_lab/models/po3_sniper_v1.json"
    config_file = "quant_lab/models/model_config.json"
    
    bt = Backtester(data_file, model_file, config_file)
    bt.run()