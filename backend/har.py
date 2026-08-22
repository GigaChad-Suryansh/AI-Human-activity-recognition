from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import math

import numpy as np


ACTIONS = [
    "Pick up container",
    "Open container",
    "Insert tool",
    "Transfer sample",
    "Close container",
    "Place container back",
]


@dataclass
class ActionPrediction:
    label: str
    confidence: float
    mode: str

    def as_dict(self) -> dict[str, Any]:
        return {"label": self.label, "confidence": round(self.confidence, 3), "mode": self.mode}


def feature_vector(result: dict[str, Any]) -> np.ndarray:
    """Convert one backend inference result into a stable temporal feature vector."""
    persons = float(result.get("persons", 0))
    objects = float(result.get("objects", 0))
    motion = float(result.get("motion", 0.0))
    interaction = result.get("interaction") or {}
    hands = result.get("hands") or []

    hand_x = [float(h.get("x", 0)) for h in hands]
    hand_y = [float(h.get("y", 0)) for h in hands]
    hand_conf = [float(h.get("confidence", 0)) for h in hands]

    # Normalise image-independent-ish hand coordinates to [0, 1].
    w = max(float(result.get("frame_width", 1)), 1.0)
    h = max(float(result.get("frame_height", 1)), 1.0)
    values = [
        persons,
        objects,
        motion / 100.0,
        (hand_x[0] / w) if hand_x else 0.0,
        (hand_y[0] / h) if hand_y else 0.0,
        (hand_x[1] / w) if len(hand_x) > 1 else 0.0,
        (hand_y[1] / h) if len(hand_y) > 1 else 0.0,
        float(interaction.get("distance_px", 999.0)) / max(w, h),
        float(interaction.get("confidence", 0.0)),
        float(len(hands)),
    ]
    return np.asarray(values, dtype=np.float32)


class TemporalHAR:
    """Temporal action layer.

    If a trained model exists at model_path, it can be loaded by the caller.
    Until then, this provides a deterministic baseline from short motion and
    interaction histories. It deliberately labels uncertain frames as
    'No interaction detected' rather than inventing a protocol action.
    """

    def __init__(self, window: int = 20):
        self.buffer: deque[np.ndarray] = deque(maxlen=window)
        self.previous: np.ndarray | None = None
        self.stable_label = "No interaction detected"
        self.stable_confidence = 0.0

    def update(self, result: dict[str, Any]) -> ActionPrediction:
        x = feature_vector(result)
        self.buffer.append(x)

        interaction = result.get("interaction")
        motion = float(result.get("motion", 0.0))
        label = "No interaction detected"
        confidence = 0.0

        if interaction:
            obj = str(interaction.get("object", "")).lower()
            ic = float(interaction.get("confidence", 0.0))
            distance_px = float(interaction.get("distance_px", 9999.0))
            recent = np.asarray(self.buffer)
            motion_now = float(np.mean(recent[-5:, 2])) if len(recent) >= 5 else motion / 100.0

            # Baseline action mapping. These are intentionally conservative;
            # the trained temporal model will replace this mapping for the SIH
            # experiment once labeled sequences are collected.
            if obj in {"bottle", "cup"}:
                label = "Pick up container"
                confidence = ic
            elif obj in {"scissors", "knife"}:
                label = "Insert tool"
                confidence = ic
            elif obj in {"book", "backpack", "suitcase"}:
                label = "Hand-object interaction"
                confidence = ic
            elif distance_px < 0.08 * max(float(result.get("frame_width", 1)), float(result.get("frame_height", 1))) and motion_now > 0.03:
                label = "Hand-object interaction"
                confidence = min(0.85, ic + 0.15)

        # Require repeated evidence before changing the displayed prediction.
        if label != "No interaction detected" and confidence >= 0.35:
            self.stable_label = label
            self.stable_confidence = confidence
        elif label == "No interaction detected" and len(self.buffer) >= 5:
            self.stable_confidence *= 0.9
            if self.stable_confidence < 0.15:
                self.stable_label = label
                self.stable_confidence = 0.0

        self.previous = x
        return ActionPrediction(self.stable_label, self.stable_confidence, "temporal-baseline")


def save_feature_sequence(results: list[dict[str, Any]], label: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"label": label, "features": [feature_vector(r).tolist() for r in results]}
    output.write_text(json.dumps(payload), encoding="utf-8")
