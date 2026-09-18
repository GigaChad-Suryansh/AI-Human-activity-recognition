from __future__ import annotations
import base64,json,os,time
from pathlib import Path
from typing import Any
import cv2,numpy as np
from fastapi import FastAPI,WebSocket,WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from har import TemporalHAR
from training_api import router as dataset_router
from experiment_api import router as experiment_router
from infer_onnx import YOLOONNX

ROOT=Path(__file__).resolve().parent.parent; MODEL_DIR=ROOT/"models"
app=FastAPI(title="Space Experiment AI Render API",version="1.5.1")
origins=["https://gigachad-suryansh.github.io","http://localhost:8000","http://127.0.0.1:8000"]
if os.getenv("FRONTEND_ORIGIN"):origins.append(os.getenv("FRONTEND_ORIGIN").rstrip("/"))
app.add_middleware(CORSMiddleware,allow_origins=sorted(set(origins)),allow_credentials=False,allow_methods=["*"],allow_headers=["*"])
app.include_router(dataset_router); app.include_router(experiment_router)
object_model=None; pose_model=None; HAR_MODEL=MODEL_DIR/"experiment_har.pt"

def load_models():
    global object_model,pose_model
    if object_model is None:object_model=YOLOONNX(MODEL_DIR/"yolo11n.onnx")
    if pose_model is None:pose_model=YOLOONNX(MODEL_DIR/"yolo11n-pose.onnx")

def decode_frame(payload):
    if payload.startswith("data:"):payload=payload.split(",",1)[1]
    frame=cv2.imdecode(np.frombuffer(base64.b64decode(payload),dtype=np.uint8),cv2.IMREAD_COLOR)
    if frame is None:raise ValueError("Invalid JPEG frame")
    return frame

def center(box):return ((box[0]+box[2])/2,(box[1]+box[3])/2)
def distance(a,b):return float(np.hypot(a[0]-b[0],a[1]-b[1]))

def infer(frame,har):
    started=time.perf_counter(); h,w=frame.shape[:2]; load_models()
    objects=object_model.detect(frame); pose=pose_model.pose_points(frame)
    persons=[o for o in objects if o["label"]=="person"]; hands=[]
    for person in pose:
        k=person["keypoints"]
        for side,idx in (("left",9),("right",10)):
            x,y,c=k[idx]
            if float(c)>=.35:hands.append({"side":side,"x":round(float(x),1),"y":round(float(y),1),"confidence":round(float(c),3)})
    interaction=None; candidates=[o for o in objects if o["label"]!="person"]; best=None
    for hand in hands:
        for obj in candidates:
            d=distance((hand["x"],hand["y"]),center(obj["box"]))
            if best is None or d<best[0]:best=(d,hand,obj)
    if best:
        d,hand,obj=best; threshold=max(70.0,min(w,h)*.16)
        if d<=threshold:interaction={"hand":hand["side"],"object":obj["label"],"distance_px":round(d,1),"confidence":round(max(0,1-d/threshold)*min(hand["confidence"],obj["confidence"]),3)}
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); small=cv2.resize(gray,(64,36)); motion=float(np.mean(cv2.Laplacian(small,cv2.CV_32F)**2)**.5)
    base={"frame_width":w,"frame_height":h,"persons":len(persons),"objects":len(objects),"detections":objects,"hands":hands,"interaction":interaction,"motion":round(motion,3)}
    prediction=har.update(base)
    return {**base,"type":"inference","timestamp":time.time(),"activity":prediction.label,"confidence":prediction.confidence,"latency_ms":round((time.perf_counter()-started)*1000,1),"model":"YOLO11n ONNX + YOLO11n-pose ONNX + "+prediction.mode,"har_mode":prediction.mode}

@app.get("/health")
def health():return {"status":"ok","runtime":"onnxruntime","object_model":"yolo11n.onnx","pose_model":"yolo11n-pose.onnx","har":"trained-LSTM" if HAR_MODEL.exists() else "temporal-baseline","websocket":"/ws/inference"}

@app.websocket("/ws/inference")
async def inference_socket(websocket:WebSocket):
    await websocket.accept()
    try:
        har=TemporalHAR(window=20,model_path=HAR_MODEL)
        while True:
            try:
                message=json.loads(await websocket.receive_text()); result=infer(decode_frame(message["frame"]),har)
                await websocket.send_text(json.dumps(result))
            except Exception as exc:await websocket.send_text(json.dumps({"type":"error","message":str(exc)}))
    except WebSocketDisconnect:pass

if __name__=="__main__":
    import uvicorn
    uvicorn.run("main_render:app",host="0.0.0.0",port=int(os.getenv("PORT","10000")))
