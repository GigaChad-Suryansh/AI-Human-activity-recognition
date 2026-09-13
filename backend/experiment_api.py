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
    return {
        "name": name,
        "description": str(payload.get("description", "")).strip(),
        "steps": cleaned,
        "verification": str(payload.get("verification", "human-pending")),
        "source": str(payload.get("source", "user-defined")),
    }


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


# Offline-first protocol assistant.  It intentionally produces a REVIEW DRAFT,
# not an authoritative mission procedure. This keeps the application usable on
# a standalone edge computer without requiring an internet connection or API key.
TEMPLATES = [
    {
        "keys": ("sample", "transfer"),
        "steps": [
            ("Pick up sample container", ["person", "container"], "hand-object pickup"),
            ("Open sample container", ["container"], "hand-object manipulation"),
            ("Pick up transfer tool", ["person", "tool"], "hand-object pickup"),
            ("Transfer sample", ["sample", "tool"], "hand-object transfer"),
            ("Close sample container", ["container"], "hand-object manipulation"),
            ("Place container back", ["container"], "hand-object placement"),
        ],
    },
    {
        "keys": ("pipette",),
        "steps": [
            ("Pick up pipette", ["person", "pipette"], "hand-object pickup"),
            ("Position pipette over sample", ["pipette", "sample"], "hand-object alignment"),
            ("Aspirate sample", ["pipette", "sample"], "hand-object manipulation"),
            ("Move pipette to target container", ["pipette", "container"], "hand-object transfer"),
            ("Dispense sample", ["pipette", "container"], "hand-object manipulation"),
            ("Return pipette", ["pipette"], "hand-object placement"),
        ],
    },
    {
        "keys": ("weigh", "weight", "balance"),
        "steps": [
            ("Pick up sample", ["person", "sample"], "hand-object pickup"),
            ("Place sample on balance", ["sample", "balance"], "hand-object placement"),
            ("Wait for stable reading", ["balance"], "stationary observation"),
            ("Record measurement", ["person", "balance"], "observation"),
            ("Remove sample", ["sample", "balance"], "hand-object pickup"),
            ("Return sample", ["sample"], "hand-object placement"),
        ],
    },
    {
        "keys": ("inspect", "inspection"),
        "steps": [
            ("Pick up inspection item", ["person", "object"], "hand-object pickup"),
            ("Position item for inspection", ["object"], "hand-object positioning"),
            ("Inspect item", ["person", "object"], "observation"),
            ("Record inspection result", ["person", "object"], "observation"),
            ("Return item", ["object"], "hand-object placement"),
        ],
    },
]


def build_suggestion(name: str, description: str = "") -> dict[str, Any]:
    text = f"{name} {description}".lower()
    selected = next((t for t in TEMPLATES if all(k in text for k in t["keys"])), None)
    if selected is None:
        selected = next((t for t in TEMPLATES if any(k in text for k in t["keys"])), None)

    if selected is None:
        steps = [
            ("Prepare experiment equipment", ["person", "equipment"], "object positioning"),
            ("Pick up required item", ["person", "object"], "hand-object pickup"),
            ("Perform the main experiment action", ["person", "object"], "hand-object interaction"),
            ("Record the experiment result", ["person", "object"], "observation"),
            ("Return equipment to its position", ["object"], "hand-object placement"),
        ]
        basis = "generic offline protocol pattern"
    else:
        steps = selected["steps"]
        basis = f"offline protocol template: {' + '.join(selected['keys'])}"

    return {
        "name": name.strip(),
        "source": "offline-assistant-draft",
        "verification": "human-pending",
        "basis": basis,
        "warning": "Draft only. Review against the official experiment protocol before training or mission use.",
        "steps": [
            {
                "id": f"step-{i}",
                "name": label,
                "description": f"Suggested action for {name.strip()}",
                "objects": objects,
                "interaction": interaction,
                "required": True,
            }
            for i, (label, objects, interaction) in enumerate(steps, 1)
        ],
    }


@router.post("/suggest")
def suggest_experiment(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Experiment name is required")
    return {"status": "draft", "suggestion": build_suggestion(name, description)}


@router.get("/{experiment_slug}")
def get_experiment(experiment_slug: str) -> dict[str, Any]:
    path = STORE / f"{slug(experiment_slug)}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Experiment not found")
    return json.loads(path.read_text(encoding="utf-8"))
