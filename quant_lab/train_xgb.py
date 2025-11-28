import pandas as pd
import xgboost as xgb
from sklearn.metrics import precision_score, recall_score
import os
import json
import joblib

def train_model():
    print("🧠 INICIANDO ENTRENAMIENTO DE IA (XGBOOST)...")

    dataset_path = "quant_lab/datasets/dataset_labeled.csv"
    if not os.path.exists(dataset_path):
        print("❌ No existe el dataset etiquetado.")
        return

    df = pd.read_csv(dataset_path)
    
    # Limpieza final de seguridad
    df.dropna(inplace=True)

    features = [
        "hour",
        "is_ny_session",
        "distance_to_ema50",
        "trend_ema200",
        "volatility_shock"
    ]
    target = "target"

    X = df[features]
    y = df[target]

    # Split Cronológico
    split_point = int(len(df) * 0.80)
    X_train, y_train = X.iloc[:split_point], y.iloc[:split_point]
    X_test, y_test = X.iloc[split_point:], y.iloc[split_point:]

    print(f"📊 Train: {len(X_train)} | Test: {len(X_test)}")

    # Entrenamiento
    # scale_pos_weight: Ayuda si hay muchos más Loss que Wins (desbalance)
    # Calculamos ratio: Negativos / Positivos
    neg, pos = y_train.value_counts()[0], y_train.value_counts()[1]
    scale_weight = neg / pos if pos > 0 else 1.0

    model = xgb.XGBClassifier(
        objective="binary:logistic",
        n_estimators=150,
        max_depth=5, 
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_weight, # Balanceo automático
        random_state=42,
        eval_metric="logloss" # Evita warnings
    )

    print("🔥 Entrenando modelo...")
    model.fit(X_train, y_train)

    # Evaluación
    probs = model.predict_proba(X_test)[:, 1]
    
    best_threshold = 0.5
    best_precision = 0.0
    best_trades_count = 0

    print("\n🔍 Buscando el 'Punto Dulce' (Sweet Spot):")
    for threshold in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]:
        preds = (probs >= threshold).astype(int)
        precision = precision_score(y_test, preds, zero_division=0)
        trades = sum(preds)

        print(f"   Umbral > {threshold:.2f} | Precisión: {precision:.2%} | Trades: {trades}")

        # Criterio: Queremos alta precisión, pero al menos 5 trades en el test set
        if precision >= best_precision and trades >= 5:
            best_precision = precision
            best_threshold = threshold
            best_trades_count = trades

    print(f"\n🏆 UMBRAL GANADOR: {best_threshold}")
    print(f"   Precisión Esperada: {best_precision:.2%}")
    print(f"   Señales generadas en test: {best_trades_count}")

    # Guardado
    model_dir = "quant_lab/models"
    os.makedirs(model_dir, exist_ok=True)
    
    model_path = os.path.join(model_dir, "po3_sniper_v1.json")
    model.save_model(model_path)

    metadata = {"threshold": best_threshold, "features": features}
    with open(os.path.join(model_dir, "model_config.json"), "w") as f:
        json.dump(metadata, f)

    print(f"💾 Cerebro guardado en: {model_path}")

if __name__ == "__main__":
    train_model()