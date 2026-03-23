from pathlib import Path
from typing import Literal, Optional
import typer
from prepro import create_dataset  


app = typer.Typer(help="Préprocesseur d'images radiographiques COVID-19")


@app.command()
def preprocess(
    resolution: int = typer.Option(
        256,
        "--resolution",
        "-r",
        help="Résolution cible (carrée), ex: 256 pour 256x256",
    ),
    with_masking: bool = typer.Option(
        False,
        "--with-masking",
        help="Appliquer les masques si activé",
    ),
    normalize: Optional[Literal["minmax", "standard"]] = typer.Option(
        None,
        "--normalize",
        "--normalization",
        help="Normalisation: 'minmax' (0-1) ou 'standard' (z-score), None pour aucune",
    ),
):
    """
    Crée un dataset prétraité à partir du dataset brut COVID-19_Radiography_Dataset.

    NB : les chemins source/sortie sont gérés à l'intérieur de create_dataset.
    """
    typer.echo(f"Résolution: {resolution}x{resolution}")
    typer.echo(f"Masquage activé: {with_masking}")
    typer.echo(f"Normalisation: {normalize or 'aucune'}")

    create_dataset(
        resolution=resolution,
        with_masking=with_masking,
        normalize_method=normalize,
    )

    typer.echo("Préprocessing terminé.")


if __name__ == "__main__":
    app()
