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
        "keys": ("sample", "transfer", "tube", "vial", "specimen"),
        "steps": [
            ("Pick up sample container", ["person", "container"], "hand-object pickup"),
            ("Open sample container lid", ["container"], "hand-object manipulation"),
            ("Pick up transfer tool", ["person", "tool"], "hand-object pickup"),
            ("Transfer sample to target vessel", ["sample", "tool"], "hand-object transfer"),
            ("Close sample container", ["container"], "hand-object manipulation"),
            ("Place container back in storage rack", ["container", "rack"], "hand-object placement"),
        ],
    },
    {
        "keys": ("pipette", "liquid", "reagent", "solution"),
        "steps": [
            ("Pick up micropipette", ["person", "pipette"], "hand-object pickup"),
            ("Attach sterile pipette tip", ["pipette", "tip"], "hand-object manipulation"),
            ("Aspirate reagent sample", ["pipette", "sample"], "hand-object manipulation"),
            ("Dispense into test microwell", ["pipette", "well"], "hand-object transfer"),
            ("Eject tip into waste receptacle", ["pipette", "waste"], "hand-object manipulation"),
            ("Return pipette to stand", ["pipette"], "hand-object placement"),
        ],
    },
    {
        "keys": ("weigh", "weight", "balance", "scale", "mass"),
        "steps": [
            ("Calibrate precision microbalance", ["balance"], "device calibration"),
            ("Place tare container on pan", ["container", "balance"], "hand-object placement"),
            ("Zero balance display", ["balance"], "device calibration"),
            ("Add specimen to target mass", ["specimen", "tool"], "hand-object transfer"),
            ("Record stable mass readout", ["balance"], "observation"),
            ("Remove weighed sample and secure", ["container"], "hand-object pickup"),
        ],
    },
    {
        "keys": ("inspect", "inspection", "microscope", "visual", "optical"),
        "steps": [
            ("Pick up specimen slide mount", ["person", "slide"], "hand-object pickup"),
            ("Secure slide onto microscope stage", ["slide", "stage"], "hand-object placement"),
            ("Adjust optical focus and illumination", ["microscope"], "device calibration"),
            ("Examine field and capture high-res frame", ["microscope", "camera"], "observation"),
            ("Log visual inspection findings", ["console"], "data entry"),
            ("Remove slide and store in tray", ["slide"], "hand-object placement"),
        ],
    },
    {
        "keys": ("plant", "seed", "leaf", "botany", "crop", "biology"),
        "steps": [
            ("Open plant growth chamber", ["chamber"], "hand-object manipulation"),
            ("Inspect leaf foliage and stems", ["plant"], "observation"),
            ("Measure canopy height and root moisture", ["sensor", "plant"], "measurement"),
            ("Administer nutrient hydration dose", ["dispenser", "plant"], "hand-object transfer"),
            ("Capture multispectral growth scan", ["camera", "plant"], "observation"),
            ("Seal growth chamber enclosure", ["chamber"], "hand-object manipulation"),
        ],
    },
    {
        "keys": ("centrifuge", "spin", "separation", "pellet", "serum"),
        "steps": [
            ("Prepare balanced centrifuge tube pairs", ["tubes", "balance"], "hand-object manipulation"),
            ("Load tubes into rotor symmetrically", ["tubes", "centrifuge"], "hand-object placement"),
            ("Latch and lock safety lid", ["centrifuge"], "hand-object manipulation"),
            ("Execute timed separation cycle", ["centrifuge"], "device operation"),
            ("Wait for rotor to come to complete stop", ["centrifuge"], "stationary observation"),
            ("Carefully extract supernatant fraction", ["tubes", "tool"], "hand-object pickup"),
        ],
    },
    {
        "keys": ("crystal", "crystallization", "protein", "macromolecule"),
        "steps": [
            ("Verify crystallization cell seals", ["cell"], "observation"),
            ("Inject precipitant solution into well", ["syringe", "cell"], "hand-object transfer"),
            ("Seal vapor diffusion chamber", ["cell", "seal"], "hand-object manipulation"),
            ("Mount cassette in microgravity locker", ["cell", "locker"], "hand-object placement"),
            ("Acquire initial polarization baseline", ["camera", "cell"], "observation"),
            ("Engage continuous optical logging", ["console"], "system activation"),
        ],
    },
    {
        "keys": ("sensor", "telemetry", "wire", "cable", "probe", "hardware"),
        "steps": [
            ("Position payload module in test bay", ["module"], "hand-object positioning"),
            ("Attach multichannel sensor leads", ["probe", "module"], "hand-object manipulation"),
            ("Power on instrumentation bus", ["switch"], "hand-object manipulation"),
            ("Run automated diagnostic sweep", ["console"], "device calibration"),
            ("Verify telemetry data stream", ["display"], "observation"),
            ("Power down and decouple sensor harness", ["probe", "module"], "hand-object placement"),
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
            (f"Prepare {name.strip()} equipment", ["person", "equipment"], "object positioning"),
            ("Inspect specimen and apparatus", ["person", "specimen"], "observation"),
            (f"Execute primary {name.strip()} procedure", ["specimen", "tool"], "hand-object interaction"),
            ("Monitor real-time sensor telemetry", ["console", "sensor"], "observation"),
            ("Record observations and results", ["console"], "observation"),
            ("Secure test items and clean workstation", ["equipment"], "hand-object placement"),
        ]
        basis = "synthesized experiment sequence"
    else:
        steps = selected["steps"]
        basis = f"template: {' + '.join(selected['keys'])}"

    return {
        "name": name.strip(),
        "source": "edge-ai-assistant",
        "verification": "human-pending",
        "basis": basis,
        "message": "AI draft sequence generated successfully.",
        "steps": [
            {
                "id": f"step-{i}",
                "name": label,
                "description": f"Action for {name.strip()}",
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
