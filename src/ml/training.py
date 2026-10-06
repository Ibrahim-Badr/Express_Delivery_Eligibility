import pandas as pd
import joblib
import json
from pathlib import Path
from sklearn.model_selection import train_test_split
from src.ml.pipeline import create_pipeline
from src.ml.evaluation import evaluate_model
from src.core.constants import RANDOM_STATE

def train():
    # 1. Load Data
    data_path = Path("data/raw_orders.csv")
    if not data_path.exists():
        raise FileNotFoundError("Raw data not found. Please run data generation first.")
    
    df = pd.read_csv(data_path)
    X = df.drop(columns=["order_id", "order_date", "express_eligible"])
    y = df["express_eligible"]

    # 2. Split Data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=RANDOM_STATE)

    # 3. Train Pipeline
    pipeline = create_pipeline()
    pipeline.fit(X_train, y_train)

    # 4. Evaluate & Create Model Card
    model_card = evaluate_model(pipeline, X_test, y_test)

    # 5. Save Artifacts
    Path("artifacts").mkdir(exist_ok=True)
    joblib.dump(pipeline, "artifacts/pipeline.pkl")
    
    with open("artifacts/model_card.json", "w") as f:
        json.dump(model_card, f, indent=4)
        
    print("Training complete. Artifacts saved to artifacts/")

if __name__ == "__main__":
    train()
