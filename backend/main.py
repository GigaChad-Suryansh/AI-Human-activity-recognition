from __future__ import annotations

import base64
import json
import time
from collections import deque
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Space Experiment AI Edge API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pretrained models are downloaded automatically by Ultralytics on first run.
# For the SIH deployment, replace these with your custom experiment weights.
object_model = YOLO("yolo11n.pt")
pose_model = YOLO("yolo11n-pose.pt")

LABELS = [
    "Pick up container",
    "Open container",
    "Insert tool",
    "Transfer sample",
    "Close container",
    "Place container back",
]

# A short motion history gives us a stable demo activity estimate without
# pretending that a real temporal HAR model has already been trained.
motion_history: deque[float] = deque(maxlen=20)


def decode_frame(payload: str) -> np.ndarray:
    if payload.startswith("data:"):
        payload = payload.split(",", 1)[1]
    raw = base64.b64decode(payload)
    frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Invalid JPEG frame")
    return frame


def box_center(box: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def infer(frame: np.ndarray) -> dict[str, Any]:
    started = time.perf_counter()
    h, w = frame.shape[:2]

    detection = object_model.predict(frame, verbose=False, conf=0.35, imgsz=640)[0]
    pose = pose_model.predict(frame, verbose=False, conf=0.35, imgsz=640)[0]

    objects: list[dict[str, Any]] = []
    if detection.boxes is not None:
        names = detection.names
        for box, conf, cls in zip(
            detection.boxes.xyxy.cpu().tolist(),
            detection.boxes.conf.cpu().tolist(),
            detection.boxes.cls.cpu().tolist(),
        ):
            label = names[int(cls)]
            # Keep useful classes for the prototype. Custom labels can be added
            # when the experiment dataset/model is trained.
            if label in {"person", "bottle", "cup", "book", "scissors", "knife", "cell phone", "backpack", "suitcase", "sports ball"}:
                objects.append({
                    "label": label,
                    "confidence": round(float(conf), 3),
                    "box": [round(float(v), 1) for v in box],
                })

    persons = [o for o in objects if o["label"] == "person"]
    hands: list[dict[str, Any]] = []
    if pose.keypoints is not None and len(pose.keypoints) > 0:
        pts = pose.keypoints.xy.cpu().numpy()
        confs = pose.keypoints.conf.cpu().numpy() if pose.keypoints.conf is not None else None
        # COCO pose indices: 9=left wrist, 10=right wrist.
        for p_idx, person_points in enumerate(pts):
            for side, idx in (("left", 9), ("right", 10)):
                if idx >= len(person_points):
                    continue
                x, y = person_points[idx]
                c = float(confs[p_idx][idx]) if confs is not None else 1.0
                if c >= 0.35:
                    hands.append({"side": side, "x": round(float(x), 1), "y": round(float(y), 1), "confidence": round(c, 3)})

    # Interaction heuristic: associate the closest visible wrist with the
    # nearest non-person object. This is intentionally explicit and replaceable
    # by a learned hand-object interaction model later.
    interaction = None
    if hands:
        candidates = [o for o in objects if o["label"] != "person"]
        best = None
        for hand in hands:
            for obj in candidates:
                d = distance((hand["x"], hand["y"]), box_center(obj["box"]))
                if best is None or d < best[0]:
                    best = (d, hand, obj)
        if best:
            d, hand, obj = best
            threshold = max(70.0, min(w, h) * 0.16)
            if d <= threshold:
                interaction = {
                    "hand": hand["side"],
                    "object": obj["label"],
                    "distance_px": round(d, 1),
                    "confidence": round(max(0.0, 1.0 - d / threshold) * min(hand["confidence"], obj["confidence"]), 3),
                }

    # Simple motion signal. It is not a trained HAR classifier; it provides a
    # deterministic bridge until the team's temporal model is supplied.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (64, 36))
    motion = float(np.mean(cv2.Laplacian(small, cv2.CV_32F) ** 2) ** 0.5)
    motion_history.append(motion)

    if interaction:
        obj = interaction["object"]
        if obj in {"bottle", "cup"}:
            activity = "Pick up container"
        elif obj in {"scissors", "knife"}:
            activity = "Insert tool"
        else:
            activity = "Hand-object interaction"
        activity_conf = interaction["confidence"]
    else:
        activity = "No interaction detected"
        activity_conf = 0.0

    latency = (time.perf_counter() - started) * 1000
    return {
        "type": "inference",
        "timestamp": time.time(),
        "frame_width": w,
        "frame_height": h,
        "persons": len(persons),
        "objects": len(objects),
        "detections": objects,
        "hands": hands,
        "interaction": interaction,
        "activity": activity,
        "confidence": round(float(activity_conf), 3),
        "motion": round(motion, 3),
        "latency_ms": round(latency, 1),
        "model": "YOLO11 object + YOLO11 pose",
        "har_mode": "interaction heuristic (replace with temporal HAR)",
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "Space Experiment AI Edge API", "status": "ready"}


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "object_model": "yolo11n.pt", "pose_model": "yolo11n-pose.pt"}


@app.websocket("/ws/inference")
async def inference_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_text()
            try:
                message = json.loads(payload)
                frame = decode_frame(message["frame"])
                result = infer(frame)
                await websocket.send_text(json.dumps(result))
            except Exception as exc:
                await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
    except WebSocketDisconnect:
        return


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
