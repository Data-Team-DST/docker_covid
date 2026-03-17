"""
Parser pour les annotations code-smell dans les fichiers Python.
"""

import re
from pathlib import Path


ANNOTATION_PATTERN = re.compile(
    r"#\s*code-smell:\s*max-lines=(\d+)(?:\s+reason=\"([^\"]+)\")?"
)

TOLERANCE_PERCENT = 10  # 10% de tolérance avant re-déclenchement


def get_file_annotation(file_path: Path) -> dict | None:
    """
    Lit l'annotation code-smell d'un fichier.

    Returns:
        dict avec max_lines, reason, tolerance_limit
        ou None si pas d'annotation
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                match = ANNOTATION_PATTERN.search(line)
                if match:
                    max_lines = int(match.group(1))
                    reason = match.group(2) or "Aucune raison fournie"
                    tolerance_limit = int(
                        max_lines * (1 + TOLERANCE_PERCENT / 100)
                    )
                    return {
                        "max_lines": max_lines,
                        "reason": reason,
                        "tolerance_limit": tolerance_limit,
                    }
    except OSError:
        pass
    return None


def evaluate_file(file_path: Path, line_count: int, global_max: int) -> dict:
    """
    Évalue le statut d'un fichier selon son annotation et son nombre de lignes.

    Returns:
        dict avec status (ok/warning/error/suppressed/tolerance_exceeded)
    """
    annotation = get_file_annotation(file_path)
    warn_threshold = int(global_max * 0.8)

    if annotation:
        max_lines = annotation["max_lines"]
        tolerance_limit = annotation["tolerance_limit"]
        reason = annotation["reason"]

        if line_count <= max_lines:
            # En dessous du max annoté → OK
            return {
                "status": "suppressed",
                "line_count": line_count,
                "annotation_max": max_lines,
                "tolerance_limit": tolerance_limit,
                "reason": reason,
                "message": (
                    f"🟠 [SUPPRIMÉ] {line_count}L"
                    f" (max annoté: {max_lines}L) — {reason}"
                ),
            }
        elif line_count <= tolerance_limit:
            # Dans la tolérance → warning spécial
            over = line_count - max_lines
            return {
                "status": "tolerance_warning",
                "line_count": line_count,
                "annotation_max": max_lines,
                "tolerance_limit": tolerance_limit,
                "reason": reason,
                "message": (
                    f"⚠️  [TOLÉRANCE] {line_count}L "
                    f"(+{over}L au-dessus du max annoté {max_lines}L, "
                    f"limite tolérance: {tolerance_limit}L) — {reason}"
                ),
            }
        else:
            # Dépasse la tolérance → erreur même avec annotation
            over = line_count - max_lines
            return {
                "status": "tolerance_exceeded",
                "line_count": line_count,
                "annotation_max": max_lines,
                "tolerance_limit": tolerance_limit,
                "reason": reason,
                "message": (
                    f"❌ [TOLÉRANCE DÉPASSÉE] {line_count}L "
                    f"(+{over}L au-dessus du max annoté {max_lines}L, "
                    f"limite: {tolerance_limit}L) — {reason}"
                ),
            }

    # Pas d'annotation → comportement normal
    if line_count > global_max:
        return {
            "status": "error",
            "line_count": line_count,
            "message": f"❌ {line_count}L (seuil: {global_max}L)",
        }
    elif line_count >= warn_threshold:
        return {
            "status": "warning",
            "line_count": line_count,
            "message": f"⚠️  {line_count}L (seuil: {global_max}L)",
        }
    else:
        return {
            "status": "ok",
            "line_count": line_count,
            "message": f"✅ {line_count}L",
        }
