from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from har import ACTIONS

router = APIRouter(prefix="/dataset", tags=["dataset"])
ROOT = Path(__file__).resolve().parent.parent
DATASET_ROOT = ROOT / "dataset" / "sequences"


def safe_label(label: str) -> str:
    if label not in ACTIONS:
        raise HTTPException(status_code=400, detail="Invalid action label")
    return re.sub(r"[^a-z0-9_]+", "_", label.lower()).strip("_")


@router.get("/stats")
def stats() -> dict[str, Any]:
    counts: dict[str, int] = {}
    for label in ACTIONS:
        folder = DATASET_ROOT / safe_label(label)
        counts[label] = len(list(folder.glob("sequence_*.json"))) if folder.exists() else 0
    return {"actions": counts, "total": sum(counts.values())}


@router.post("/sequence")
def save_sequence(payload: dict[str, Any]) -> dict[str, Any]:
    label = str(payload.get("label", ""))
    frames = payload.get("frames")
    if label not in ACTIONS:
        raise HTTPException(status_code=400, detail="Invalid action label")
    if not isinstance(frames, list) or len(frames) < 8:
        raise HTTPException(status_code=400, detail="A sequence needs at least 8 inference frames")
    if any(not isinstance(frame, list) or len(frame) != 10 for frame in frames):
        raise HTTPException(status_code=400, detail="Each frame must contain 10 temporal features")

    folder = DATASET_ROOT / safe_label(label)
    folder.mkdir(parents=True, exist_ok=True)
    existing = sorted(folder.glob("sequence_*.json"))
    path = folder / f"sequence_{len(existing) + 1:04d}.json"
    record = {
        "label": label,
        "frames": frames,
        "feature_count": 10,
        "frame_count": len(frames),
    }
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return {"status": "saved", "label": label, "frame_count": len(frames), "path": str(path.relative_to(ROOT))}
