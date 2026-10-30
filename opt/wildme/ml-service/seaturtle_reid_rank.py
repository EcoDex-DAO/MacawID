#!/usr/bin/env python3
"""Rank-1 of real SeaTurtleID turtles using the accessible MobileNetV2 re-id model.

Embeddings 512-d (L2-normalised) via
`marcmarais-ru/seaturtle_reid_mobilenetv2-quadruplet-random-combined_datasets`
(green/hawksbill/loggerhead). Computes cosine rank-1 : query = image A, gallery
= the other N-1. Read-only (no DB writes). License MIT.
"""
import json, os, sys
import numpy as np
from PIL import Image
import torch
from model import MobileNetV2ReID

MODEL = ("marcmarais-ru/"
         "seaturtle_reid_mobilenetv2-quadruplet-random-combined_datasets")
# (stem, fileA, fileB) for the 5 individuals already exercised (2 imgs each).
PAIRS = [
    ("t243",  "ALfgTHysAv.jpeg", "AhuTQfBYTN.JPG"),
    ("t217",  "AuugpclqfN.JPG",  "AyeTaetytF.JPG"),
    ("t323",  "ADIpQIzlZR.JPG",  "AiySvdvtDM.JPG"),
    ("t048",  "AHzXGRWzlN.jpg",  "ASJDBfiBYc.JPG"),
    ("t441",  "AWmdGjCEnN.JPG",  "AiXKGyQQmA.jpeg"),
]


def _prep(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))
    im = im.resize((384, 384))
    x = torch.from_numpy(np.asarray(im).astype(np.float32) / 255.0).permute(2, 0, 1)
    # ImageNet-ish mean/std
    mean = torch.tensor([0.485, 0.456, 0.406])[:, None, None]
    std = torch.tensor([0.229, 0.224, 0.225])[:, None, None]
    return (x - mean) / std


def main(root):
    model = MobileNetV2ReID.from_pretrained(MODEL, embedding_dim=512)
    model.eval()
    buf = []
    names = []
    for ind, a, b in PAIRS:
        fa, fb = os.path.join(root, ind, a), os.path.join(root, ind, b)
        with torch.no_grad():
            ea = model(_prep(fa)[None])
            eb = model(_prep(fb)[None])
        buf += [ea[0], eb[0]]
        names += [f"{ind}_a", f"{ind}_b"]
    E = torch.stack(buf)
    E = E / (E.norm(dim=1, keepdim=True) + 1e-9)
    S = E @ E.T
    ind_of = {f"{i}_a": i for i in range(len(names))}
    idmap = {"t243": 0, "t217": 1, "t323": 2, "t048": 3, "t441": 4}
    lbl = [idmap[n[:-2]] for n in names]
    correct = 0
    for i, n in enumerate(names):
        s = S[i].clone(); s[i] = -1
        top = names[int(s.argmax())]
        ok = lbl[int(s.argmax())] == lbl[i]
        correct += int(ok)
        print(f"{n}: rank1={top} ok={ok}")
    print(f"=== seaturtle re-id rank-1 {correct}/{len(names)} ({correct/len(names)*100:.0f}%) ===")
    out = {"model": MODEL, "rank1": f"{correct}/{len(names)}", "emb_dim": int(E.shape[1])}
    with open("/home/jovyan/work/seaturtle_rank_result.json", "w") as f:
        json.dump(out, f)
    print(json.dumps(out))
    return 0 if correct > 0 else 2


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "/work/turtles/data/images"
    sys.exit(main(root))
