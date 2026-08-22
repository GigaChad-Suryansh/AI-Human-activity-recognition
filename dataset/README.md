# Experiment HAR dataset

The backend now supports a temporal LSTM classifier, but a trustworthy experiment-specific classifier requires labeled examples.

Collect short sequences for each action:

1. Pick up container
2. Open container
3. Insert tool
4. Transfer sample
5. Close container
6. Place container back

Each labeled JSON sequence contains 10 temporal features derived from YOLO detection, pose/wrist locations, hand-object distance/confidence, and motion.

## Recommended collection

Record multiple people, camera positions, lighting conditions, object placements, speeds, and correct/incorrect executions. Aim for at least 50-100 sequences per class for a first prototype; more is better.

The current `backend/har.py` uses a conservative baseline until `models/experiment_har.pt` exists. Do not interpret baseline accuracy as trained HAR accuracy.

## Train

From `backend/` with the virtual environment active:

```powershell
python train_har.py --data ../dataset/sequences --out ../models/experiment_har.pt --epochs 30
```

Restart the FastAPI server after training. `/health` will report `trained-LSTM` when the weights are present.
