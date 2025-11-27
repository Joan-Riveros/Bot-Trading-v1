import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
import joblib
import os
import json


def train_model():
    print("🧠 INICIANDO ENTRENAMIENTO DE IA (XGBOOST)...")

    # 1. Cargar Dataset Etiquetado
    dataset_path = "quant_lab/datasets/dataset_labeled.csv"
    if not os.path.exists(dataset_path):
        print("❌ No existe el dataset etiquetado.")
        return

    df = pd.read_csv(dataset_path)

    # 2. Definir Features (X) y Target (y)
    # Estas son las columnas que la IA podrá ver para tomar decisiones
    features = [
        "hour",
        "is_ny_session",
        "distance_to_ema50",
        "trend_ema200",
        "volatility_shock",
        "atr",
    ]

    target = "target"

    X = df[features]
    y = df[target]

    # 3. División Cronológica (Train / Test)
    # NO usamos random_split porque en trading el tiempo importa.
    # Entrenamos con el pasado (primer 80%) y probamos con el futuro (último 20%)
    split_point = int(len(df) * 0.80)

    X_train = X.iloc[:split_point]
    y_train = y.iloc[:split_point]

    X_test = X.iloc[split_point:]
    y_test = y.iloc[split_point:]

    print(f"📊 Datos de Entrenamiento: {len(X_train)} muestras")
    print(f"📊 Datos de Prueba (Futuro simulado): {len(X_test)} muestras")

    # 4. Configuración del Modelo XGBoost
    # Usamos parámetros conservadores para evitar sobreajuste
    model = xgb.XGBClassifier(
        objective="binary:logistic",
        n_estimators=100,  # Número de árboles
        max_depth=4,  # Profundidad máxima (evita memorizar ruido)
        learning_rate=0.05,  # Velocidad de aprendizaje
        subsample=0.8,  # Usar 80% de datos por árbol
        random_state=42,
    )

    print("🔥 Entrenando modelo...")
    model.fit(X_train, y_train)

    # 5. Evaluación y Búsqueda de Umbral
    # El modelo predice una probabilidad (ej. 0.75 de ganar).
    # ¿A partir de qué número disparamos? ¿0.50? ¿0.60?
    probs = model.predict_proba(X_test)[:, 1]

    best_threshold = 0.5
    best_precision = 0.0

    print("\n🔍 Optimizando Umbral de Decisión:")
    for threshold in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75]:
        preds = (probs >= threshold).astype(int)
        precision = precision_score(y_test, preds, zero_division=0)
        recall = recall_score(y_test, preds, zero_division=0)
        trades = sum(preds)

        print(
            f"   Umbral > {threshold:.2f} | Precisión: {precision:.2%} | Trades: {trades}"
        )

        # Queremos maximizar precisión, pero asegurando que haga al menos algunos trades
        if precision > best_precision and trades > 10:
            best_precision = precision
            best_threshold = threshold

    print(
        f"\n🏆 MEJOR UMBRAL ELEGIDO: {best_threshold} (Precisión: {best_precision:.2%})"
    )

    # 6. Guardar el Cerebro
    model_dir = "quant_lab/models"
    os.makedirs(model_dir, exist_ok=True)

    # Guardamos el modelo en formato JSON (ligero y rápido)
    model_path = os.path.join(model_dir, "po3_sniper_v1.json")
    model.save_model(model_path)

    # Guardamos también la metadata (el umbral elegido)
    metadata = {"threshold": best_threshold, "features": features}
    with open(os.path.join(model_dir, "model_config.json"), "w") as f:
        json.dump(metadata, f)

    print(f"💾 Modelo guardado en: {model_path}")
    print("🏁 SPRINT 2 FINALIZADO.")


if __name__ == "__main__":
    train_model()
