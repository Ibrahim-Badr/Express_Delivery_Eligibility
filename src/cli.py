import json
from pathlib import Path

import typer

from src.core.dependencies import get_model_repository
from src.domain.entities import OrderEntity
from src.ml.data_generation import generate_orders_dataset
from src.ml.predictor import MLPredict
from src.ml.training import train

app = typer.Typer(help="CLI pour les tâches ML et l'exploitation du service")


@app.command("generate-data")
def generate_data_cmd(n_rows: int = 6000, random_state: int = 42):
    """Générer un jeu de données synthétique sous data/raw_orders.csv."""
    typer.echo(f"Génération de {n_rows} commandes...")
    df = generate_orders_dataset(n_rows, random_state)
    Path("data").mkdir(exist_ok=True)
    df.to_csv("data/raw_orders.csv", index=False)
    typer.echo("Terminé ! Fichier sauvegardé sous data/raw_orders.csv")


@app.command("train")
def train_cmd():
    """Entraîner le modèle et sauvegarder les artefacts via ModelRepository."""
    typer.echo("Lancement de l'entraînement du modèle...")
    model_card = train()
    typer.echo(
        f"Entraînement terminé ! (ROC AUC = {model_card.metrics.get('roc_auc')})"
    )


@app.command("serve")
def serve_cmd(host: str = "127.0.0.1", port: int = 8000):
    """Démarrer le serveur API FastAPI avec Uvicorn."""
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
        help="Fichier JSON contenant une commande.",
    ),
):
    """Prédire l'éligibilité d'une commande lue depuis un fichier JSON."""
    repo = get_model_repository()
    if not repo.is_available():
        typer.echo("Erreur : modèle indisponible. Lancez 'train' d'abord.", err=True)
        raise typer.Exit(code=1)

    payload = json.loads(file.read_text(encoding="utf-8"))
    order = OrderEntity(**payload)
    predictor = MLPredict(pipeline=repo.load_pipeline())
    result = predictor.predict(order)
    typer.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
