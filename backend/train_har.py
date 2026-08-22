from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

LABELS = [
    "Pick up container",
    "Open container",
    "Insert tool",
    "Transfer sample",
    "Close container",
    "Place container back",
]
LABEL_TO_ID = {label: i for i, label in enumerate(LABELS)}


class SequenceDataset(Dataset):
    def __init__(self, files: list[Path], window: int = 20):
        self.samples = []
        self.window = window
        for path in files:
            item = json.loads(path.read_text(encoding="utf-8"))
            label = item["label"]
            if label not in LABEL_TO_ID:
                continue
            x = np.asarray(item["frames"], dtype=np.float32)
            if len(x) < 2:
                continue
            if len(x) >= window:
                starts = range(0, len(x) - window + 1, max(1, window // 2))
                for s in starts:
                    self.samples.append((x[s:s + window], LABEL_TO_ID[label]))
            else:
                pad = np.repeat(x[-1: ], window - len(x), axis=0)
                self.samples.append((np.concatenate([x, pad]), LABEL_TO_ID[label]))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        x, y = self.samples[i]
        return torch.tensor(x), torch.tensor(y)


class HARLSTM(nn.Module):
    def __init__(self, features: int = 10, hidden: int = 96, classes: int = 6):
        super().__init__()
        self.lstm = nn.LSTM(features, hidden, num_layers=2, batch_first=True, dropout=0.15)
        self.head = nn.Sequential(nn.LayerNorm(hidden), nn.Linear(hidden, classes))

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.head(out[:, -1])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="dataset/sequences")
    p.add_argument("--out", default="models/experiment_har.pt")
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch", type=int, default=16)
    args = p.parse_args()

    files = list(Path(args.data).glob("**/sequence_*.json"))
    if not files:
        raise SystemExit("No labeled sequences found. Collect sequences first.")

    rng = np.random.default_rng(42)
    rng.shuffle(files)
    split = max(1, int(len(files) * 0.8))
    train_files, val_files = files[:split], files[split:]
    train = SequenceDataset(train_files)
    val = SequenceDataset(val_files)
    if not len(train):
        raise SystemExit("Training dataset is empty.")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = HARLSTM().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    loss_fn = nn.CrossEntropyLoss()
    loader = DataLoader(train, batch_size=args.batch, shuffle=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        total = correct = 0
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            logits = model(x)
            loss = loss_fn(logits, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            total += len(y)
            correct += int((logits.argmax(1) == y).sum())
        print(f"epoch {epoch:02d}: train_acc={correct / max(total, 1):.3f}")

    val_acc = None
    if len(val):
        model.eval(); correct = total = 0
        with torch.no_grad():
            for x, y in DataLoader(val, batch_size=args.batch):
                pred = model(x.to(device)).argmax(1).cpu()
                correct += int((pred == y).sum()); total += len(y)
        val_acc = correct / max(total, 1)
        print(f"validation_acc={val_acc:.3f}")

    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "labels": LABELS, "features": 10, "window": 20, "validation_accuracy": val_acc}, out)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
