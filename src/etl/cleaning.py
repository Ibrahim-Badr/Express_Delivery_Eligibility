import pandas as pd

def validate_dataset(df: pd.DataFrame) -> bool:
    """
    Contrôles de qualité élémentaires sur les données d'entrée.
    """
    required_columns = {
        "order_id",
        "order_date",
        "hour",
        "day_of_week",
        "weekend",
        "distance_km",
        "order_value_eur",
        "weight_kg",
        "stock_available",
        "preparation_time_min",
        "carrier_capacity",
        "weather",
        "delivery_zone",
        "customer_type",
        "express_eligible",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Colonnes obligatoires absentes : {sorted(missing_columns)}"
        )

    if df["order_id"].duplicated().any():
        raise ValueError("Des identifiants de commande sont dupliqués.")

    if df["express_eligible"].isna().any():
        raise ValueError("La variable cible contient des valeurs manquantes.")

    if not df["hour"].between(0, 23).all():
        raise ValueError("Certaines heures sont invalides.")

    if not df["distance_km"].ge(0).all():
        raise ValueError("La distance ne peut pas être négative.")

    if not df["weight_kg"].ge(0).all():
        raise ValueError("Le poids ne peut pas être négatif.")

    if not df["preparation_time_min"].ge(0).all():
        raise ValueError("Le temps de préparation ne peut pas être négatif.")

    if not df["carrier_capacity"].between(0, 1).all():
        raise ValueError(
            "La capacité du transporteur doit être comprise entre 0 et 1."
        )

    if not df["stock_available"].isin([0, 1]).all():
        raise ValueError(
            "La variable stock_available doit contenir uniquement 0 ou 1."
        )

    return True


def clean_orders_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoyage automatique des données.
    """
    cleaned = df.copy()

    # Suppression des doublons sur l'identifiant métier
    cleaned = cleaned.drop_duplicates(
        subset=["order_id"],
        keep="last"
    )

    # Conversion des dates
    cleaned["order_date"] = pd.to_datetime(
        cleaned["order_date"],
        errors="coerce"
    )

    # Suppression des lignes dont les champs essentiels sont invalides
    essential_columns = [
        "order_id",
        "distance_km",
        "weight_kg",
        "stock_available",
        "preparation_time_min",
        "carrier_capacity",
        "express_eligible",
    ]

    cleaned = cleaned.dropna(subset=essential_columns)

    # Bornage des valeurs numériques
    cleaned = cleaned[cleaned["distance_km"] >= 0]
    cleaned = cleaned[cleaned["weight_kg"] >= 0]
    cleaned = cleaned[cleaned["preparation_time_min"] >= 0]
    cleaned = cleaned[cleaned["carrier_capacity"].between(0, 1)]
    cleaned = cleaned[cleaned["stock_available"].isin([0, 1])]

    return cleaned.reset_index(drop=True)
