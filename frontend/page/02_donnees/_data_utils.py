"""Utilitaires de chargement et de traitement du dataset COVID."""

# code-smell: max-lines=165 reason="Module de données cohésif — scan+metrics"
# pylint: disable=import-error,too-many-locals

import random
from pathlib import Path

import kagglehub
import numpy as np
import streamlit as st
from _config import IMG_EXTS  # noqa: E402
from PIL import Image


def looks_like_images(p: Path) -> bool:
    """Return True if directory p contains image files (directly or in images/)."""
    if not p.exists() or not p.is_dir():
        return False
    img_exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
    for f in p.iterdir():
        if f.is_file() and f.suffix.lower() in img_exts:
            return True
    if (p / "images").exists():
        for f in (p / "images").iterdir():
            if f.is_file() and f.suffix.lower() in img_exts:
                return True
    return False


def _is_image_file(p: Path) -> bool:
    """Return True if p is a regular file with a known image extension."""
    return p.is_file() and p.suffix.lower() in IMG_EXTS


@st.cache_resource
def get_kaggle_dataset_path(dataset_slug: str) -> Path | None:
    """Download or locate the Kaggle dataset and return its local root path."""
    if kagglehub is None:
        return None
    try:
        p = kagglehub.dataset_download(dataset_slug)
        return Path(p)
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def compute_image_metrics(img: Image.Image) -> dict:
    """Compute luminosity mean, contrast std and Shannon entropy of an image."""
    arr = np.array(img.convert("RGB"), dtype=np.float32)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    l_channel = 0.299 * r + 0.587 * g + 0.114 * b
    mean_lum = float(np.mean(l_channel))
    std_lum = float(np.std(l_channel))
    hist, _ = np.histogram(l_channel.flatten(), bins=256, range=(0, 255))
    probs = hist / (hist.sum() + 1e-12)
    probs = probs[probs > 0]
    entropy = float(-(probs * np.log2(probs)).sum()) if probs.size > 0 else 0.0
    return {
        "luminosity_mean": mean_lum,
        "contrast_std": std_lum,
        "entropy": entropy,
    }


def mask_coverage(mask_path: Path) -> float | None:
    """Return percentage of non-zero pixels in a binary mask image."""
    if not mask_path.exists():
        return None
    try:
        m = Image.open(mask_path).convert("L")
        arr = np.array(m)
        covered = np.count_nonzero(arr)
        total = arr.size
        return 100.0 * covered / total if total > 0 else 0.0
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def sample_images_from_class(root: Path, cls: str, n: int) -> list[Path]:
    """Return up to n randomly sampled image paths from the given class directory."""
    images_dir = root / cls / "images"
    if not images_dir.exists():
        return []
    imgs = sorted([p for p in images_dir.iterdir() if _is_image_file(p)])
    if len(imgs) <= n:
        return imgs
    return random.Random().sample(imgs, k=n)


def overlay_mask_on_image(
    img_path: Path,
    mask_path: Path,
    alpha: float = 0.4,
) -> Image.Image:
    """Overlay a red semi-transparent mask on an image and return the composite."""
    img = Image.open(img_path).convert("RGBA")
    mask = Image.open(mask_path).convert("L").resize(img.size)
    mask_arr = np.array(mask)
    alpha_layer = (mask_arr > 0).astype(np.uint8) * int(255 * alpha)
    alpha_img = Image.fromarray(alpha_layer, mode="L")
    red = Image.new("RGBA", img.size, (255, 0, 0, 0))
    red.putalpha(alpha_img)
    return Image.alpha_composite(img, red)


@st.cache_data(show_spinner=False)
def run_full_dataset_scan(
    root: Path,
    classes: list[str],
    include_masks: bool = True,
) -> dict:
    """Scan all images in the dataset and return metrics aggregated per class."""
    results: dict = {"per_image": [], "by_class": {}}
    for cls in classes:
        results["by_class"][cls] = {
            "count": 0,
            "metrics": [],
            "mask_coverages": [],
            "files": [],
        }
        images_dir = root / cls / "images"
        if not images_dir.exists():
            continue
        files = sorted([p for p in images_dir.iterdir() if _is_image_file(p)])
        results["by_class"][cls]["count"] = len(files)
        for img_path in files:
            try:
                img = Image.open(img_path).convert("RGB")
                metrics = compute_image_metrics(img)
                mask_path = None
                mask_cov = None
                if include_masks:
                    candidate = root / cls / "masks" / img_path.name
                    if candidate.exists():
                        mask_path = candidate
                        mask_cov = mask_coverage(mask_path)
                entry = {
                    "path": str(img_path),
                    "class": cls,
                    "metrics": metrics,
                    "mask": str(mask_path) if mask_path else None,
                    "mask_coverage": mask_cov,
                }
                results["per_image"].append(entry)
                results["by_class"][cls]["metrics"].append(metrics)
                if mask_cov is not None:
                    results["by_class"][cls]["mask_coverages"].append(mask_cov)
                results["by_class"][cls]["files"].append(str(img_path))
            except Exception:  # pylint: disable=broad-exception-caught
                continue
    for _cls, info in results["by_class"].items():
        ms = info["metrics"]
        if ms:
            info["avg_lum"] = float(np.mean([m["luminosity_mean"] for m in ms]))
            info["avg_std"] = float(np.mean([m["contrast_std"] for m in ms]))
            info["avg_entropy"] = float(np.mean([m["entropy"] for m in ms]))
        else:
            info["avg_lum"] = info["avg_std"] = info["avg_entropy"] = 0.0
    return results
