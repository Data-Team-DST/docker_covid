"""Configuration, constantes et CSS de la page 02_donnees."""

from pathlib import Path

DATASET_DIR = Path("dataset")
N_PER_CLASS_DEFAULT = 6
THUMBNAIL_MAX = (512, 512)
IMG_EXTS = {".png"}
KAGGLE_SLUG = "tawsifurrahman/covid19-radiography-database"
CLASS_NAMES = ["COVID", "Lung_Opacity", "Normal", "Viral Pneumonia"]

DEFAULT_CLASS_COUNTS = {
    "COVID": 3616,
    "Normal": 10192,
    "Viral Pneumonia": 1345,
    "Lung Opacity": 6012,
}
DEFAULT_TOTAL = sum(DEFAULT_CLASS_COUNTS.values())

CSS = (
    "\n<style>\n"
    ".section-card {\n"
    "    background: linear-gradient("
    "90deg, rgba(12,18,30,0.95), rgba(8,12,20,0.95));\n"
    "    padding:12px; border-radius:8px;"
    " border:1px solid rgba(255,255,255,0.03);\n"
    "    color:#cfe8ff; margin-bottom:12px;\n"
    "}\n"
    ".card {\n"
    "    background:#131416; padding:8px; border-radius:8px;\n"
    "    border:1px solid rgba(255,255,255,0.04);\n"
    "    width:100%; max-width:260px;"
    " box-shadow:0 6px 14px rgba(0,0,0,0.35); margin-bottom:8px;\n"
    "}\n"
    ".label { font-weight:700; color:#cfe8ff; margin-bottom:6px; }\n"
    ".kv { font-size:12px; color:#98a1b3; }\n"
    ".small-note { font-size:12px; color:#98a1b3; }\n"
    "</style>\n"
)
