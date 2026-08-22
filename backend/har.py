from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

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
    persons = float(result.get("persons", 0))
    objects = float(result.get("objects", 0))
    motion = float(result.get("motion", 0.0))
    interaction = result.get("interaction") or {}
    hands = result.get("hands") or []
    hand_x = [float(h.get("x", 0)) for h in hands]
    hand_y = [float(h.get("y", 0)) for h in hands]
    w = max(float(result.get("frame_width", 1)), 1.0)
    h = max(float(result.get("frame_height", 1)), 1.0)
    return np.asarray([
        persons, objects, motion / 100.0,
        (hand_x[0] / w) if hand_x else 0.0,
        (hand_y[0] / h) if hand_y else 0.0,
        (hand_x[1] / w) if len(hand_x) > 1 else 0.0,
        (hand_y[1] / h) if len(hand_y) > 1 else 0.0,
        float(interaction.get("distance_px", 999.0)) / max(w, h),
        float(interaction.get("confidence", 0.0)),
        float(len(hands)),
    ], dtype=np.float32)


class TemporalHAR:
    """Use trained LSTM weights when present, otherwise conservative baseline."""

    def __init__(self, window: int = 20, model_path: Path | None = None):
        self.buffer: deque[np.ndarray] = deque(maxlen=window)
        self.window = window
        self.previous: np.ndarray | None = None
        self.stable_label = "No interaction detected"
        self.stable_confidence = 0.0
        self.model = None
        self.mode = "temporal-baseline"

        if model_path and model_path.exists():
            try:
                import torch
                from torch import nn

                class HARLSTM(nn.Module):
                    def __init__(self):
                        super().__init__()
                        self.lstm = nn.LSTM(10, 96, num_layers=2, batch_first=True, dropout=0.15)
                        self.head = nn.Sequential(nn.LayerNorm(96), nn.Linear(96, len(ACTIONS)))

                    def forward(self, x):
                        out, _ = self.lstm(x)
                        return self.head(out[:, -1])

                checkpoint = torch.load(model_path, map_location="cpu")
                model = HARLSTM()
                model.load_state_dict(checkpoint["state_dict"])
                model.eval()
                self.model = model
                self.mode = "trained-LSTM"
            except Exception:
                self.model = None
                self.mode = "temporal-baseline"

    def update(self, result: dict[str, Any]) -> ActionPrediction:
        x = feature_vector(result)
        self.buffer.append(x)

        if self.model is not None and len(self.buffer) >= self.window:
            import torch
            with torch.no_grad():
                sequence = torch.tensor(np.asarray(self.buffer), dtype=torch.float32).unsqueeze(0)
                probabilities = torch.softmax(self.model(sequence), dim=1)[0]
                idx = int(probabilities.argmax())
                confidence = float(probabilities[idx])
            self.stable_label = ACTIONS[idx]
            self.stable_confidence = confidence
            self.previous = x
            return ActionPrediction(self.stable_label, confidence, self.mode)

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
            if obj in {"bottle", "cup"}:
                label, confidence = "Pick up container", ic
            elif obj in {"scissors", "knife"}:
                label, confidence = "Insert tool", ic
            elif distance_px < 0.08 * max(float(result.get("frame_width", 1)), float(result.get("frame_height", 1))) and motion_now > 0.03:
                label, confidence = "Hand-object interaction", min(0.85, ic + 0.15)

        if label != "No interaction detected" and confidence >= 0.35:
            self.stable_label = label
            self.stable_confidence = confidence
        elif label == "No interaction detected" and len(self.buffer) >= 5:
            self.stable_confidence *= 0.9
            if self.stable_confidence < 0.15:
                self.stable_label = label
                self.stable_confidence = 0.0
        self.previous = x
        return ActionPrediction(self.stable_label, self.stable_confidence, self.mode)


def save_feature_sequence(results: list[dict[str, Any]], label: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"label": label, "frames": [feature_vector(r).tolist() for r in results]}
    output.write_text(json.dumps(payload), encoding="utf-8")
