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
    mlflow_tracking_uri: str = "sqlite:///mlflow.db"
    mlflow_experiment_name: str = "livraison-express"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
