from __future__ import annotations
from pathlib import Path
from typing import Any
import cv2
import numpy as np
import onnxruntime as ort

COCO_NAMES=["person","bicycle","car","motorcycle","airplane","bus","train","truck","boat","traffic light","fire hydrant","stop sign","parking meter","bench","bird","cat","dog","horse","sheep","cow","elephant","bear","zebra","giraffe","backpack","umbrella","handbag","tie","suitcase","frisbee","skis","snowboard","sports ball","kite","baseball bat","baseball glove","skateboard","surfboard","tennis racket","bottle","wine glass","cup","fork","knife","spoon","bowl","banana","apple","sandwich","orange","broccoli","carrot","hot dog","pizza","donut","cake","chair","couch","potted plant","bed","dining table","toilet","tv","laptop","mouse","remote","keyboard","cell phone","microwave","oven","toaster","sink","refrigerator","book","clock","vase","scissors","teddy bear","hair drier","toothbrush"]
KEEP_LABELS={"person","bottle","cup","book","scissors","knife","cell phone","backpack","suitcase","sports ball"}

def letterbox(image,size=640):
    h,w=image.shape[:2]; scale=min(size/max(w,1),size/max(h,1))
    nw,nh=int(round(w*scale)),int(round(h*scale))
    resized=cv2.resize(image,(nw,nh),interpolation=cv2.INTER_LINEAR)
    canvas=np.full((size,size,3),114,dtype=np.uint8); px,py=(size-nw)/2,(size-nh)/2
    x0,y0=int(round(px)),int(round(py)); canvas[y0:y0+nh,x0:x0+nw]=resized
    return canvas,scale,(px,py)

def preprocess(image,size=640):
    img,scale,pad=letterbox(image,size)
    blob=img[:,:,::-1].transpose(2,0,1).astype(np.float32)/255.0
    return np.expand_dims(blob,0),scale,pad

def xywh_to_xyxy(boxes):
    out=np.empty_like(boxes); out[:,0]=boxes[:,0]-boxes[:,2]/2; out[:,1]=boxes[:,1]-boxes[:,3]/2
    out[:,2]=boxes[:,0]+boxes[:,2]/2; out[:,3]=boxes[:,1]+boxes[:,3]/2
    return out

def nms(boxes,scores,iou_threshold=.45):
    order=scores.argsort()[::-1]; keep=[]
    while len(order):
        i=int(order[0]); keep.append(i)
        if len(order)==1: break
        rest=order[1:]; xx1=np.maximum(boxes[i,0],boxes[rest,0]); yy1=np.maximum(boxes[i,1],boxes[rest,1])
        xx2=np.minimum(boxes[i,2],boxes[rest,2]); yy2=np.minimum(boxes[i,3],boxes[rest,3])
        inter=np.maximum(0,xx2-xx1)*np.maximum(0,yy2-yy1)
        ai=np.maximum(0,boxes[i,2]-boxes[i,0])*np.maximum(0,boxes[i,3]-boxes[i,1])
        ar=np.maximum(0,boxes[rest,2]-boxes[rest,0])*np.maximum(0,boxes[rest,3]-boxes[rest,1])
        union=ai+ar-inter+1e-7; order=rest[(inter/union)<=iou_threshold]
    return keep

def normalize_output(output):
    a=np.asarray(output)
    if a.ndim==3:a=a[0]
    if a.ndim!=2:raise ValueError(f"Unexpected ONNX output shape: {a.shape}")
    return a if a.shape[0]<a.shape[1] else a.T

class YOLOONNX:
    def __init__(self,model_path: str|Path,imgsz=640):
        self.session=ort.InferenceSession(str(model_path),providers=["CPUExecutionProvider"])
        self.input_name=self.session.get_inputs()[0].name; self.imgsz=imgsz
    def _run(self,frame):
        tensor,scale,pad=preprocess(frame,self.imgsz)
        return self.session.run(None,{self.input_name:tensor})[0],scale,pad
    def detect(self,frame,conf_threshold=.35):
        raw,scale,pad=self._run(frame); data=normalize_output(raw)
        boxes=xywh_to_xyxy(data[:,:4]); scores_all=data[:,4:]; cls=scores_all.argmax(1)
        scores=scores_all[np.arange(len(cls)),cls]; mask=scores>=conf_threshold
        boxes,scores,cls=boxes[mask],scores[mask],cls[mask]; h,w=frame.shape[:2]; results=[]
        for i in nms(boxes,scores):
            x1,y1,x2,y2=boxes[i]
            vals=[max(0,min(w,(x1-pad[0])/scale)),max(0,min(h,(y1-pad[1])/scale)),max(0,min(w,(x2-pad[0])/scale)),max(0,min(h,(y2-pad[1])/scale))]
            label=COCO_NAMES[int(cls[i])] if int(cls[i])<len(COCO_NAMES) else str(int(cls[i]))
            if label in KEEP_LABELS: results.append({"label":label,"confidence":round(float(scores[i]),3),"box":[round(float(v),1) for v in vals]})
        return results
    def pose_points(self,frame,conf_threshold=.35):
        raw,scale,pad=self._run(frame); data=normalize_output(raw)
        if data.shape[1]<56:return []
        scores=data[:,4]; keypoints=data[:,5:56].reshape(-1,17,3); out=[]; h,w=frame.shape[:2]
        for i in np.where(scores>=conf_threshold)[0]:
            k=keypoints[i].copy(); k[:,0]=np.clip((k[:,0]-pad[0])/scale,0,w); k[:,1]=np.clip((k[:,1]-pad[1])/scale,0,h)
            out.append({"confidence":float(scores[i]),"keypoints":k})
        return out
