import typer
from src.ml.data_generation import generate_orders_dataset
from src.ml.training import train
from pathlib import Path

app = typer.Typer(help="CLI pour les tâches ML du projet")

@app.command("generate-data")
def generate_data_cmd(n_rows: int = 6000, random_state: int = 42):
    typer.echo(f"Génération de {n_rows} commandes...")
    df = generate_orders_dataset(n_rows, random_state)
    Path("data").mkdir(exist_ok=True)
    df.to_csv("data/raw_orders.csv", index=False)
    typer.echo("Terminé ! Fichier sauvegardé sous data/raw_orders.csv")

@app.command("train")
def train_cmd():
    typer.echo("Lancement de l'entraînement du modèle...")
    train()
    typer.echo("Entraînement terminé !")

if __name__ == "__main__":
    app()
