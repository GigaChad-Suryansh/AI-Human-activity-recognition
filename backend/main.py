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
from fastapi.responses import FileResponse
from ultralytics import YOLO

from har import TemporalHAR
from training_api import router as dataset_router
from experiment_api import router as experiment_router

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Space Experiment AI Edge API", version="1.5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(dataset_router)
app.include_router(experiment_router)

object_model = YOLO("yolo11n.pt")
pose_model = YOLO("yolo11n-pose.pt")
HAR_MODEL = MODEL_DIR / "experiment_har.pt"
motion_history: deque[float] = deque(maxlen=20)

@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(ROOT / "index.html", media_type="text/html")

@app.get("/app.js", include_in_schema=False)
def frontend_js() -> FileResponse:
    return FileResponse(ROOT / "app.js", media_type="text/javascript")

@app.get("/styles.css", include_in_schema=False)
def frontend_css() -> FileResponse:
    return FileResponse(ROOT / "styles.css", media_type="text/css")

@app.get("/training.js", include_in_schema=False)
def training_js() -> FileResponse:
    return FileResponse(ROOT / "training.js", media_type="text/javascript")

@app.get("/experiment-builder.js", include_in_schema=False)
def experiment_builder_js() -> FileResponse:
    return FileResponse(ROOT / "experiment-builder.js", media_type="text/javascript")

def decode_frame(payload: str) -> np.ndarray:
    if payload.startswith("data:"):
        payload = payload.split(",", 1)[1]
    frame = cv2.imdecode(np.frombuffer(base64.b64decode(payload), dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Invalid JPEG frame")
    return frame

def box_center(box: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)

def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))

def infer(frame: np.ndarray, har: TemporalHAR) -> dict[str, Any]:
    started = time.perf_counter()
    h, w = frame.shape[:2]
    detection = object_model.predict(frame, verbose=False, conf=0.35, imgsz=640)[0]
    pose = pose_model.predict(frame, verbose=False, conf=0.35, imgsz=640)[0]
    objects: list[dict[str, Any]] = []
    if detection.boxes is not None:
        for box, conf, cls in zip(detection.boxes.xyxy.cpu().tolist(), detection.boxes.conf.cpu().tolist(), detection.boxes.cls.cpu().tolist()):
            label = detection.names[int(cls)]
            if label in {"person", "bottle", "cup", "book", "scissors", "knife", "cell phone", "backpack", "suitcase", "sports ball"}:
                objects.append({"label": label, "confidence": round(float(conf), 3), "box": [round(float(v), 1) for v in box]})
    persons = [o for o in objects if o["label"] == "person"]
    hands: list[dict[str, Any]] = []
    if pose.keypoints is not None and len(pose.keypoints) > 0:
        pts = pose.keypoints.xy.cpu().numpy()
        confs = pose.keypoints.conf.cpu().numpy() if pose.keypoints.conf is not None else None
        for p_idx, person_points in enumerate(pts):
            for side, idx in (("left", 9), ("right", 10)):
                if idx >= len(person_points):
                    continue
                x, y = person_points[idx]
                c = float(confs[p_idx][idx]) if confs is not None else 1.0
                if c >= 0.35:
                    hands.append({"side": side, "x": round(float(x), 1), "y": round(float(y), 1), "confidence": round(c, 3)})
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
                interaction = {"hand": hand["side"], "object": obj["label"], "distance_px": round(d, 1), "confidence": round(max(0.0, 1.0 - d / threshold) * min(hand["confidence"], obj["confidence"]), 3)}
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (64, 36))
    motion = float(np.mean(cv2.Laplacian(small, cv2.CV_32F) ** 2) ** 0.5)
    motion_history.append(motion)
    base_result = {"frame_width": w, "frame_height": h, "persons": len(persons), "objects": len(objects), "detections": objects, "hands": hands, "interaction": interaction, "motion": round(motion, 3)}
    prediction = har.update(base_result)
    latency = (time.perf_counter() - started) * 1000
    return {**base_result, "type": "inference", "timestamp": time.time(), "activity": prediction.label, "confidence": prediction.confidence, "latency_ms": round(latency, 1), "model": "YOLO11 object + YOLO11 pose + " + prediction.mode, "har_mode": prediction.mode}

@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "object_model": "yolo11n.pt", "pose_model": "yolo11n-pose.pt", "har": "trained-LSTM" if HAR_MODEL.exists() else "temporal-baseline", "dataset": "enabled", "experiments": "configurable", "dashboard": "http://localhost:8000/", "websocket": "ws://localhost:8000/ws/inference"}

@app.websocket("/ws/inference")
async def inference_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        har = TemporalHAR(window=20, model_path=HAR_MODEL)
        while True:
            payload = await websocket.receive_text()
            try:
                message = json.loads(payload)
                frame = decode_frame(message["frame"])
                await websocket.send_text(json.dumps(infer(frame, har)))
            except Exception as exc:
                await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
    except WebSocketDisconnect:
        return

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
