# Space Experiment AI

SIH prototype for offline Human Activity Recognition and experiment-sequence validation.

## What is working now

- Responsive mission-control dashboard
- Live browser camera input
- Local video-file input
- Real local YOLO11 object detection backend
- Real local YOLO11 pose estimation backend
- Wrist/hand keypoint extraction
- Transparent hand-to-object interaction heuristic
- WebSocket browser ↔ Python inference connection
- Experiment state machine for a predefined 6-step protocol
- Correct / skipped-sequence validation controls
- Browser voice alerts
- Timestamped JSONL export
- Camera snapshot export
- Offline-first operation after model weights are available locally
- GitHub Pages deployment workflow for the dashboard

## Architecture

```text
Camera / Video
      ↓
FastAPI WebSocket
      ↓
YOLO11 Object Detection ─────┐
                             ├→ Hand/Object Interaction
YOLO11 Pose ─────────────────┘
      ↓
Activity bridge / temporal-HAR insertion point
      ↓
Experiment State Machine
      ↓
Alert + Log + Dashboard
```

## Run the real AI backend locally

From the repository root on Windows PowerShell:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

The API starts at `http://localhost:8000`.

Then open the GitHub Pages dashboard (or the local `index.html`) and click **Start Camera**. The dashboard will try to connect to `ws://localhost:8000/ws/inference` and display real YOLO/pose results.

### First run

Ultralytics downloads `yolo11n.pt` and `yolo11n-pose.pt` on first use. For a true offline/air-gapped deployment, download the weights once and keep them on the edge machine.

## Custom SIH model stage

The current backend uses general pretrained models so the entire pipeline can be tested immediately. Generic COCO labels are **not** a substitute for the final experiment-specific detector.

When your team has collected annotated experiment footage, train a custom detector and replace:

```python
object_model = YOLO("yolo11n.pt")
```

with something like:

```python
object_model = YOLO("../models/experiment_objects.pt")
```

The temporal HAR model is the next learned component. It should consume a window of pose/object/interaction features and output one of the experiment activities. The current `infer()` activity mapping is deliberately a bridge so the real camera → detection → interaction → GUI path is already testable.

## Browser ↔ backend

The browser sends downsampled JPEG frames to `/ws/inference`. The backend returns JSON containing:

- `detections`
- `hands`
- `interaction`
- `activity`
- `confidence`
- `persons`
- `objects`
- `latency_ms`

You can point the frontend at another edge computer by setting the browser console/local storage value:

```js
localStorage.setItem('SPACE_AI_API', 'http://EDGE-COMPUTER-IP:8000')
```

Reload the page afterward.

## Deployment note

GitHub Pages hosts the static dashboard only. Python/YOLO must run on the local edge computer or another reachable inference machine. This separation is intentional for the offline/edge architecture.

GitHub Actions deploys the static application to GitHub Pages on pushes to `main`. In repository **Settings → Pages**, choose **GitHub Actions** as the source if it is not already selected.
