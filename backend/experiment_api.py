from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/experiments", tags=["experiments"])
ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "dataset" / "experiments"
STORE.mkdir(parents=True, exist_ok=True)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_") or "experiment"


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    steps = payload.get("steps")
    if not name:
        raise HTTPException(status_code=400, detail="Experiment name is required")
    if not isinstance(steps, list) or not steps:
        raise HTTPException(status_code=400, detail="At least one step is required")
    cleaned = []
    for i, step in enumerate(steps, 1):
        if isinstance(step, str):
            step = {"name": step}
        label = str(step.get("name", "")).strip()
        if not label:
            raise HTTPException(status_code=400, detail=f"Step {i} has no name")
        cleaned.append({
            "id": step.get("id", f"step-{i}"),
            "name": label,
            "description": str(step.get("description", "")).strip(),
            "objects": list(step.get("objects", [])) if isinstance(step.get("objects", []), list) else [],
            "interaction": str(step.get("interaction", "")).strip(),
            "required": bool(step.get("required", True)),
        })
    return {"name": name, "description": str(payload.get("description", "")).strip(), "steps": cleaned}


@router.get("")
def list_experiments() -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(STORE.glob("*.json"))]


@router.post("")
def save_experiment(payload: dict[str, Any]) -> dict[str, Any]:
    data = validate(payload)
    data["slug"] = slug(data["name"])
    path = STORE / f"{data['slug']}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"status": "saved", "experiment": data}


@router.get("/{experiment_slug}")
def get_experiment(experiment_slug: str) -> dict[str, Any]:
    path = STORE / f"{slug(experiment_slug)}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Experiment not found")
    return json.loads(path.read_text(encoding="utf-8"))
