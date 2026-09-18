FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /build/requirements.txt
RUN pip install --no-cache-dir -r /build/requirements.txt onnx>=1.16,<2
RUN python - <<'PY'
from pathlib import Path
from ultralytics import YOLO
out=Path("/build/models")
out.mkdir(parents=True,exist_ok=True)
for name in ("yolo11n.pt","yolo11n-pose.pt"):
    model=YOLO(name)
    exported=model.export(format="onnx",imgsz=640,simplify=False,dynamic=False,opset=12)
    Path(exported).rename(out/f"{Path(name).stem}.onnx")
PY

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements-render.txt /app/backend/requirements-render.txt
RUN pip install --no-cache-dir -r /app/backend/requirements-render.txt
COPY backend /app/backend
COPY --from=builder /build/models /app/models
ENV PYTHONPATH=/app/backend
EXPOSE 10000
CMD ["sh","-c","uvicorn main_render:app --host 0.0.0.0 --port ${PORT:-10000}"]