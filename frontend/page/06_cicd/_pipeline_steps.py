"""Construction de la liste des étapes du pipeline Sklearn."""

# pylint: disable=import-error


def build_pipeline_steps(cfg: dict, data_dir: str) -> list:
    """Construit la liste des étapes à partir de la configuration UI.

    Args:
        cfg: dictionnaire des options cochées dans l'interface.
        data_dir: chemin vers le répertoire des données brutes.

    Returns:
        Liste de tuples (nom, transformateur) pour sklearn.Pipeline.
    """
    # pylint: disable=too-many-locals
    from src.features.St_Pipeline.Transformateurs import (  # noqa: PLC0415
        ImageAnalyser,
        ImageAugmenter,
        ImageFlattener,
        ImageHistogram,
        ImageMasker,
        ImageNormalizer,
        ImagePathLoader,
        ImagePCA,
        ImageResizer,
        RGB_to_L,
        SaveTransformer,
        TrainTestSplitter,
        TupleToDataFrame,
    )

    kw = {"verbose": True, "use_streamlit": True}
    steps = [
        ("loader", ImagePathLoader(root_dir=data_dir, **kw)),
        ("tuple_to_df", TupleToDataFrame(**kw)),
        (
            "analyzer",
            ImageAnalyser(load_images=True, analyze_masks=cfg["use_masks"], **kw),
        ),
    ]

    if cfg["do_resize"]:
        steps.append(
            ("resizer", ImageResizer(img_size=(cfg["img_size"], cfg["img_size"]), **kw))
        )
    if cfg["do_normalize"]:
        steps.append(("normalizer", ImageNormalizer(**kw)))
    if cfg["use_augmentation"]:
        steps.append(
            (
                "augmenter",
                ImageAugmenter(
                    flip_horizontal=True,
                    rotation_range=15,
                    brightness_range=0.2,
                    probability=0.5,
                    **kw,
                ),
            )
        )
    if cfg["use_masks"]:
        steps.append(("masker", ImageMasker(**kw)))
    if cfg["do_grayscale"]:
        steps.append(("gray", RGB_to_L(**kw)))
    if cfg["do_flatten"]:
        steps.append(("flattener", ImageFlattener(**kw)))
    if cfg["do_histogram"]:
        steps.append(("histogram", ImageHistogram(bins=cfg.get("n_bins", 32), **kw)))
    if cfg["do_pca"] and cfg["do_flatten"]:
        steps.append(("pca", ImagePCA(n_components=cfg.get("n_components", 50), **kw)))
    if cfg["do_split"]:
        steps.append(
            (
                "splitter",
                TrainTestSplitter(
                    test_size=cfg.get("test_size", 0.2),
                    random_state=42,
                    **kw,
                ),
            )
        )
    if cfg["do_save"]:
        steps.append(
            (
                "saver",
                SaveTransformer(
                    save_dir="outputs",
                    prefix=cfg["pipeline_name"],
                    **kw,
                ),
            )
        )

    return steps
