from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from har import feature_vector


LABELS = [
    "Pick up container",
    "Open container",
    "Insert tool",
    "Transfer sample",
    "Close container",
    "Place container back",
]


def write_sequence(results: list[dict[str, Any]], label: str, output_dir: str = "dataset/sequences") -> str:
    if label not in LABELS:
        raise ValueError(f"Unknown action label: {label}")
    if not results:
        raise ValueError("At least one inference result is required")
    root = Path(output_dir) / label.lower().replace(" ", "_")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"sequence_{len(list(root.glob('sequence_*.json')))+1:04d}.json"
    payload = {
        "label": label,
        "frames": [feature_vector(r).tolist() for r in results],
        "feature_count": 10,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)
