#!/usr/bin/env python3
"""Compare MiewID msv3 vs SeaTurtleID MobileNetV2-ReID on the same 5 SeaTurtleID
individuals (2 images each). Reports rank-1 per model.

SeaTurtleID model: 512-d, lic MIT (model.py ships from the Hub). Read-only.
Usage (in jupyter):  python3 seaturtle_test.py
"""
import json, sys
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image
from model import MobileNetV2ReID

IMAGES = {
    "t1_t243_a": 1, "t1_t243_b": 1,
    "t2_t217_a": 2, "t2_t217_b": 2,
    "t3_t323_a": 3, "t3_t323_b": 3,
    "t4_t048_a": 4, "t4_t048_b": 4,
    "t5_t441_a": 5, "t5_t441_b": 5,
}
ROOT = "/home/jovyan/work/turtles5"
MODEL_ID = "marcmarais-ru/seaturtle_reid_mobilenetv2-quadruplet-random-combined_datasets"

tf = T.Compose([
    T.Resize((384, 384)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def main():
    names = list(IMAGES.keys())
    model = MobileNetV2ReID.from_pretrained(MODEL_ID, embedding_dim=512).eval()
    model = model.cuda() if torch.cuda.is_available() else model
    embs = []
    for n in names:
        img = Image.open(f"{ROOT}/{n}").convert("RGB")
        with torch.no_grad():
            e = model(tf(img).unsqueeze(0).cuda() if torch.cuda.is_available()
                      else tf(img).unsqueeze(0))
            e = torch.nn.functional.normalize(e, p=2, dim=1)
        embs.append(e.cpu().numpy()[0])
        print(f"{n} dim={e.shape[1]}")
    E = np.vstack(embs)
    sim = E @ E.T
    correct = 0
    ind_ok = {}
    for i, n in enumerate(names):
        s = sim[i].copy(); s[i] = -1
        top = [names[j] for j in np.argsort(-s)[:3]]
        ok = IMAGES[top[0]] == IMAGES[n]
        correct += int(ok)
        ind_ok.setdefault(IMAGES[n], []).append(int(ok))
        print(f"{n} (ind{IMAGES[n]}): rank1={top[0]} ok={ok}")
    inds = sum(1 for v in ind_ok.values() if all(v))
    print(f"=== seaturtle rank1 {correct}/10 | individuals both-correct {inds}/5 ===")


if __name__ == "__main__":
    main()
