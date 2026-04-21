"""Dashboard Flask — DS_COVID MLOps — suivi backlog agile."""
import json
import os
from collections import Counter
from pathlib import Path

import requests
import yaml
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

ROOT = Path(__file__).parent.parent
BACKLOG_FILE = Path(__file__).parent / "backlog.yaml"
STATE_FILE = Path(__file__).parent / "state.json"

DATA_DIR = ROOT / "data"
DVC_RAW_FILE = ROOT / "data" / "raw.dvc"
MODELS_DIR = ROOT / "data" / "models"

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:5001")


def load_backlog() -> dict:
    with open(BACKLOG_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def merge_state(backlog: dict, state: dict) -> dict:
    for sprint in backlog.get("sprints", []):
        sid = sprint["id"]
        sprint_state = state.get(sid, {})
        if "status" in sprint_state:
            sprint["status"] = sprint_state["status"]
        for story in sprint.get("stories", []):
            uid = story["id"]
            if uid in sprint_state.get("stories", {}):
                story["done"] = sprint_state["stories"][uid].get(
                    "done", story["done"]
                )
    return backlog


def compute_stats(backlog: dict) -> dict:
    sprints = backlog.get("sprints", [])
    total_stories = sum(len(s["stories"]) for s in sprints)
    done_stories = sum(
        sum(1 for st in s["stories"] if st.get("done")) for s in sprints
    )
    total_points = sum(s["points"] for s in sprints)
    done_points = sum(
        sum(st["points"] for st in s["stories"] if st.get("done"))
        for s in sprints
    )
    sprints_done = sum(1 for s in sprints if s["status"] == "completed")
    return {
        "total_stories": total_stories,
        "done_stories": done_stories,
        "pct_stories": (
            round(done_stories / total_stories * 100) if total_stories else 0
        ),
        "total_points": total_points,
        "done_points": done_points,
        "pct_points": (
            round(done_points / total_points * 100) if total_points else 0
        ),
        "sprints_done": sprints_done,
        "sprints_total": len(sprints),
    }


def load_dvc_info(dvc_file: Path) -> dict:
    if not dvc_file.exists():
        return {}
    with open(dvc_file, encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    outs = meta.get("outs", [{}])[0]
    return {
        "md5": outs.get("md5", "—"),
        "size_mb": round(outs.get("size", 0) / 1024 / 1024, 1),
        "nfiles": outs.get("nfiles", "—"),
        "path": outs.get("path", "—"),
    }


def load_data_stats() -> dict:
    raw_info = load_dvc_info(DVC_RAW_FILE)
    models = []
    if MODELS_DIR.exists():
        for ext in ("*.keras", "*.h5"):
            for f in sorted(MODELS_DIR.glob(ext)):
                models.append({
                    "name": f.name,
                    "size_mb": round(f.stat().st_size / 1024 / 1024, 1),
                })
    data_dirs = {}
    for subdir in ["raw", "processed", "models"]:
        p = DATA_DIR / subdir
        if p.exists():
            files = [f for f in p.rglob("*") if f.is_file()]
            ext_counter = Counter(f.suffix.lower() for f in files)
            data_dirs[subdir] = {
                "nfiles": len(files),
                "size_mb": round(
                    sum(f.stat().st_size for f in files) / 1024 / 1024, 1
                ),
                "types": dict(ext_counter.most_common(5)),
            }
    return {"raw_dvc": raw_info, "data_dirs": data_dirs, "models": models}


# ── Pages ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    backlog = load_backlog()
    state = load_state()
    backlog = merge_state(backlog, state)
    stats = compute_stats(backlog)
    return render_template("index.html", backlog=backlog, stats=stats)


@app.route("/data")
def data_explorer():
    try:
        r = requests.get(f"{DATA_SERVICE_URL}/v1/data/stats", timeout=10)
        ds = r.json()
        # Normalise vers le format attendu par le template
        raw_dvc = ds.get("raw", {}).get("dvc") or {}
        data_dirs = {}
        for key in ("raw", "processed", "models"):
            local = ds.get(key, {}).get("local") or {}
            if local.get("exists"):
                exts: dict = {}
                data_dirs[key] = {
                    "nfiles": local.get("nfiles", 0),
                    "size_mb": local.get("size_mb", 0),
                    "types": exts,
                }
        models = []
        stats = {
            "raw_dvc": raw_dvc or None,
            "data_dirs": data_dirs,
            "models": models,
        }
    except Exception:
        # Fallback 1 : lire le cache JSON écrit par data-service (instantané)
        cache_file = ROOT / "tmp" / "data_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    cached = json.load(f).get("stats", {})
                raw_dvc = cached.get("raw", {}).get("dvc") or {}
                data_dirs = {}
                for key in ("raw", "processed", "models"):
                    local = cached.get(key, {}).get("local") or {}
                    if local.get("exists"):
                        data_dirs[key] = {
                            "nfiles": local.get("nfiles", 0),
                            "size_mb": local.get("size_mb", 0),
                            "types": {},
                        }
                stats = {"raw_dvc": raw_dvc or None, "data_dirs": data_dirs, "models": []}
            except Exception:
                stats = load_data_stats()
        else:
            # Fallback 2 : scan filesystem (lent, dernier recours)
            stats = load_data_stats()
    return render_template("data_explorer.html", stats=stats)


# ── API backlog ────────────────────────────────────────────────────────────

@app.route("/api/toggle", methods=["POST"])
def toggle_story():
    data = request.get_json()
    sprint_id = data.get("sprint_id")
    story_id = data.get("story_id")
    done = data.get("done", False)
    state = load_state()
    state.setdefault(sprint_id, {}).setdefault("stories", {})[story_id] = {
        "done": done
    }
    save_state(state)
    return jsonify({"ok": True})


@app.route("/api/sprint-status", methods=["POST"])
def update_sprint_status():
    data = request.get_json()
    sprint_id = data.get("sprint_id")
    status = data.get("status")
    if status not in ("not_started", "in_progress", "completed", "blocked"):
        return jsonify({"error": "invalid status"}), 400
    state = load_state()
    state.setdefault(sprint_id, {})["status"] = status
    save_state(state)
    return jsonify({"ok": True})


@app.route("/api/data-stats")
def api_data_stats():
    return jsonify(load_data_stats())


# ── Proxy DVC → data-service ───────────────────────────────────────────────

@app.route("/api/dvc/<action>", methods=["GET", "POST"])
def dvc_proxy(action: str):
    if action not in ("status", "remotes", "pull", "push", "repro"):
        return jsonify({"error": "action inconnue"}), 400
    method = "POST" if action in ("pull", "push", "repro") else "GET"
    try:
        r = requests.request(
            method,
            f"{DATA_SERVICE_URL}/v1/dvc/{action}",
            timeout=310,
        )
        return jsonify(r.json()), r.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": f"data-service inaccessible ({DATA_SERVICE_URL})",
            "stdout": "",
            "stderr": "Lancer : make data-start",
        }), 503


# ── Proxy data-service : stats, search, image ─────────────────────────────

@app.route("/api/ds/stats")
def ds_stats_proxy():
    refresh = request.args.get("refresh", "false")
    try:
        r = requests.get(
            f"{DATA_SERVICE_URL}/v1/data/stats",
            params={"refresh": refresh}, timeout=30,
        )
        return jsonify(r.json()), r.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "data-service inaccessible"}), 503


@app.route("/api/ds/search")
def ds_search_proxy():
    try:
        r = requests.get(
            f"{DATA_SERVICE_URL}/v1/data/search",
            params=request.args, timeout=10,
        )
        return jsonify(r.json()), r.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "data-service inaccessible"}), 503


@app.route("/api/ds/image")
def ds_image_proxy():
    try:
        r = requests.get(
            f"{DATA_SERVICE_URL}/v1/data/image",
            params=request.args, stream=True, timeout=10,
        )
        from flask import Response
        return Response(
            r.content,
            status=r.status_code,
            content_type=r.headers.get("content-type", "image/png"),
        )
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "data-service inaccessible"}), 503


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", "5050"))
    app.run(host="0.0.0.0", port=port, debug=False)
