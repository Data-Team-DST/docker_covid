"""Exécution des commandes DVC (status/pull/push/repro) — extrait de
data-service (chantier point 16, split lecture/opérations DVC)."""

import logging
import os
import subprocess
from pathlib import Path

from fastapi import HTTPException

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", "/app"))


def run_dvc(cmd: list[str]) -> dict:
    """Exécute une commande dvc dans PROJECT_ROOT et retourne son résultat."""
    logger.info("dvc run: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            ["dvc"] + cmd,
            capture_output=True, text=True,
            cwd=str(PROJECT_ROOT), timeout=300,
            check=False,
        )
        out = {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "success": result.returncode == 0,
        }
        if out["success"]:
            logger.info("dvc %s OK (rc=0)", cmd[0])
        else:
            logger.warning(
                "dvc %s failed rc=%s stderr=%s",
                cmd[0], result.returncode, result.stderr.strip()[:200],
            )
        return out
    except FileNotFoundError:
        logger.error("dvc not found in container")
        raise HTTPException(
            status_code=500, detail="DVC non installé dans ce container"
        )
    except subprocess.TimeoutExpired:
        logger.error("dvc %s timeout after 300s", cmd[0])
        raise HTTPException(status_code=504, detail="DVC timeout (> 5 min)")
