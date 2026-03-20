import typer
from pathlib import Path
from image_processor import ImagePreprocessor
from typing import Literal

app = typer.Typer(help="Préprocesseur d'images médicales COVID-19")

@app.command()
def preprocess(
    source: Path = typer.Argument(..., help="Dossier source des images"),
    output: Path = typer.Argument(..., help="Dossier de sortie"),
    size: str = typer.Option("256,256", "--size", help="Taille cible (ex: 256,256)"),
    mode: Literal["L"] = typer.Option("L", "--mode", help="Mode image unique (L=grayscale)"),
    with_masking: bool = typer.Option(False, "--with-masking", help="Appliquer les masques si True"),
    classes: str = typer.Option(
        "COVID,Normal,Lung_Opacity,Viral Pneumonia",
        "--classes",
        help="Classes séparées par virgules"
    ),
    normalization: str = typer.Option(
        None,
        "--normalization",
        "--normalize",
        help="Normalisation: 'minmax' ou 'standard' (z-score), None pour aucune",
        case_sensitive=False,
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Ne fait que lister sans traiter")
):
    """Prétraite un dataset d'images radiologiques"""

    # Parse les paramètres
    target_size = tuple(map(int, size.split(",")))
    classes_list = [c.strip() for c in classes.split(",")]

    processor = ImagePreprocessor(
        source_path=source,
        output_path=output,
        target_size=target_size,
        image_mode=mode,
        classes=classes_list,
        with_masking=with_masking,
        normalize_method=normalization 
    )

    if dry_run:
        typer.echo("Mode dry-run: analyse seulement")
        stats = processor.process(dry_run=True)
        return
   
    stats = processor.process(dry_run=False)
    typer.echo(f"\n✨ Dataset prêt: {output}")

if __name__ == "__main__":
    app()