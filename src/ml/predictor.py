import pandas as pd
from typing import Dict, Any

def predict_single_order(pipeline, order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prend un dictionnaire représentant une commande,
    le transforme en DataFrame 1-ligne, et effectue la prédiction.
    """
    # Conversion du dictionnaire en DataFrame (1 ligne)
    df = pd.DataFrame([order_data])
    
    # Prédiction (classe 1 ou 0)
    prediction = pipeline.predict(df)[0]
    
    # Probabilité (pour la classe 1 : éligible)
    probability = pipeline.predict_proba(df)[0][1]
    
    return {
        "express_eligible": bool(prediction),
        "decision": "oui" if prediction == 1 else "non",
        "probability": round(float(probability), 4)
    }
