# Edge AI Backend

This service connects the browser dashboard to real local inference.

## What it does

- Accepts JPEG frames over WebSocket at `/ws/inference`.
- Runs YOLO11 object detection.
- Runs YOLO11 pose estimation.
- Extracts wrist positions.
- Performs a transparent hand-to-object interaction heuristic.
- Returns structured JSON containing detections, hands, interaction, activity, confidence and latency.
- Works offline after the YOLO weights have been downloaded once.

## Run on Windows

From the repository root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

The API will be at `http://localhost:8000` and WebSocket inference at `ws://localhost:8000/ws/inference`.

## First run

Ultralytics downloads `yolo11n.pt` and `yolo11n-pose.pt` automatically if they are not present. This is a one-time setup. For an air-gapped/space-station deployment, download the weights before deployment and keep them on the edge computer.

## Custom SIH models

Replace the two model names in `main.py` with local paths such as:

```python
object_model = YOLO("../models/experiment_objects.pt")
pose_model = YOLO("../models/experiment_pose.pt")
```

The current activity label is deliberately a bridge. A trained temporal HAR model should consume a sequence of per-frame features and replace the heuristic in `infer()`.
