import json
from pathlib import Path

import typer

from src.core.config import settings
from src.core.dependencies import get_model_repository
from src.core.logging import setup_logging
from src.domain.entities import OrderEntity
from src.ml.data_generation import generate_orders_dataset
from src.ml.predictor import MLPredict
from src.ml.training import train

setup_logging()

app = typer.Typer(help="CLI for ML tasks and service operations")


@app.command("generate-data")
def generate_data_cmd(n_rows: int = 6000, random_state: int = 42):
    """Generate a synthetic dataset at data/raw_orders.csv."""
    typer.echo(f"Generating {n_rows} orders...")
    df = generate_orders_dataset(n_rows, random_state)
    Path("data").mkdir(exist_ok=True)
    df.to_csv("data/raw_orders.csv", index=False)
    typer.echo("Done! Dataset saved to data/raw_orders.csv")


@app.command("train")
def train_cmd():
    """Train the ML model and persist artifacts via ModelRepository."""
    typer.echo("Starting model training...")
    model_card = train()
    typer.echo(
        f"Training complete! (ROC AUC = {model_card.metrics.get('roc_auc')})"
    )


@app.command("serve")
def serve_cmd(host: str = "127.0.0.1", port: int = 8000):
    """Start the FastAPI HTTP server using Uvicorn."""
    import uvicorn

    from src.main import app as fastapi_app

    uvicorn.run(fastapi_app, host=host, port=port)


@app.command("predict")
def predict_cmd(
    file: Path = typer.Option(
        ...,
        "--file",
        "-f",
        exists=True,
        readable=True,
        help="Path to a JSON file containing order features.",
    ),
):
    """Predict express delivery eligibility for an order read from a JSON file."""
    repo = get_model_repository()
    if not repo.is_available():
        typer.echo("Error: Model is unavailable. Run 'train' first.", err=True)
        raise typer.Exit(code=1)

    payload = json.loads(file.read_text(encoding="utf-8"))
    order = OrderEntity(**payload)
    predictor = MLPredict(pipeline=repo.load_pipeline())
    result = predictor.predict(order)
    typer.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


@app.command("retrain-should-run")
def retrain_should_run_cmd(
    min_new_orders: int = settings.retrain_min_new_orders,
    growth_ratio: float = settings.retrain_growth_ratio,
):
    """Exit 0 if hybrid retraining threshold is reached, else exit 2 (for Airflow branching)."""
    from src.orchestration.retraining import RetrainingOrchestrator

    orchestrator = RetrainingOrchestrator(
        growth_ratio=growth_ratio,
        state_path=RetrainingOrchestrator.default_state_path(),
    )
    if orchestrator.should_trigger_retrain(min_new_orders=min_new_orders):
        typer.echo("TRIGGER_RETRAINING")
        raise typer.Exit(code=0)
    typer.echo("SKIP_RETRAINING")
    raise typer.Exit(code=2)


@app.command("retrain-check")
def retrain_check_cmd(
    min_new_orders: int = settings.retrain_min_new_orders,
    growth_ratio: float = settings.retrain_growth_ratio,
):
    """One-shot check if sufficient new orders exist and retrain model."""
    from src.orchestration.retraining import RetrainingOrchestrator

    orchestrator = RetrainingOrchestrator(
        growth_ratio=growth_ratio,
        state_path=RetrainingOrchestrator.default_state_path(),
    )
    promoted = orchestrator.trigger_retrain_if_needed(min_new_orders=min_new_orders)
    if promoted:
        typer.echo("Retraining succeeded and candidate model was promoted.")
    else:
        typer.echo("No retraining needed or candidate did not beat active champion.")


@app.command("retrain-daemon")
def retrain_daemon_cmd(
    interval_seconds: float = settings.retrain_interval_seconds,
    min_new_orders: int = settings.retrain_min_new_orders,
    growth_ratio: float = settings.retrain_growth_ratio,
):
    """Start continuous background model retraining orchestrator."""
    from src.orchestration.retraining import RetrainingOrchestrator

    typer.echo(
        f"Starting retraining orchestrator (interval={interval_seconds}s, "
        f"min_new_orders={min_new_orders}, growth_ratio={growth_ratio:.2%})..."
    )
    orchestrator = RetrainingOrchestrator(
        growth_ratio=growth_ratio,
        state_path=RetrainingOrchestrator.default_state_path(),
    )
    orchestrator.run_daemon_loop(
        interval_seconds=interval_seconds, min_new_orders=min_new_orders
    )


if __name__ == "__main__":
    app()
