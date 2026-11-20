from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "eligibilite-livraison-express"
    environment: str = "local"
    artifacts_dir: str = "artifacts"
    model_path: str = "artifacts/express_delivery_model.joblib"
    model_threshold: float = 0.5
    model_version: str = "1.0.0"
    random_seed: int = 42
    log_level: str = "INFO"
    database_url: str = "sqlite:///./local_databases/local.db"
    rabbitmq_url: str = ""
    rabbitmq_queue: str = "live_orders"
    mlflow_tracking_uri: str = "sqlite:///./local_databases/mlflow.db"
    mlflow_experiment_name: str = "livraison-express"
    retrain_interval_seconds: float = 60.0
    retrain_min_new_orders: int = 300
    retrain_growth_ratio: float = 0.05
    retrain_min_roc_auc: float = 0.75
    retrain_min_f1_score: float = 0.75

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
