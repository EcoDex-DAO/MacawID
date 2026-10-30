#!/usr/bin/env python3
"""Rank-1 real SeaTurtleID with the ACCESSIBLE MiewID turtle fine-tuned weights.

Loads model_state_dict from yoavram-lab/AnimalCLEF2026-sub231 (fine-tuned on
SeaTurtleIDHeads, an accessible analogue to the 404 miew_id.iot_v2.bin) inside
the msv3 backbone, then embeds 2 images x 5 turtles via the ml-service /extract
preprocessing. Cosine rank-1. Read-only.
"""
import json, os, sys
import numpy as np
import torch

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/home/jovyan/work/str"
CKT = sys.argv[2] if len(sys.argv) > 2 else (
    "/home/jovyan/work/hf_turtle2/models--yoavram-lab--AnimalCLEF2026-sub231/"
    "snapshots/855af5b907007b233718415899dc5ae6921f0d99/resources/weights/"
    "miewid_turtle_ext_finetuned.pt")
MDIR = "/home/jovyan/work/miewid-msv3"
PAIRS = [
    ("t243", "ALfgTHysAv.jpeg", "AhuTQfBYTN.JPG"),
    ("t217", "AuugpclqfN.JPG", "AyeTaetytF.JPG"),
    ("t323", "ADIpQIzlZR.JPG", "AiySvdvtDM.JPG"),
    ("t048", "AHzXGRWzlN.jpg", "ASJDBfiBYc.JPG"),
    ("t441", "AWmdGjCEnN.JPG", "AiXKGyQQmA.jpeg"),
]

import sys as _s
_s.path.insert(0, MDIR)
from modeling_miewid import MiewIDModel  # noqa: E402


def load():
    arch = torch.load(CKT, map_location="cpu")
    model = MiewIDModel.from_pretrained(MDIR)  # architecture msv3 backbone
    model.load_state_dict(arch["model_state_dict"], strict=False)
    model.eval()
    return model


def embed(model, path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    x = im  # msv3 /extract preproc: resize to model input inside modeling
    with torch.no_grad():
        out = model(x) if isinstance(x, torch.Tensor) else model(None)
    return out


def main():
    if not os.path.exists(CKT):
        print("missing ckpt", CKT); return 2
    print("loading", os.path.basename(CKT))
    model = load()
    names = []
    vecs = []
    for ind, a, b in PAIRS:
        for tag, fn in (("a", a), ("b", b)):
            p = os.path.join(ROOT, ind, fn)
            im = Image.open(p)
            em = model.preprocess(im)["embedding"] if hasattr(model, "preprocess") else list(model._extract(im))
            vecs.append(np.asarray(em, dtype=np.float32))
            names.append(f"{ind}_{tag}")
    E = np.stack(vecs); E = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
    idmap = {"t243": 0, "t217": 1, "t323": 2, "t048": 3, "t441": 4}
    lbl = [idmap[n[:-2]] for n in names]
    S = E @ E.T
    correct = 0
    for i, n in enumerate(names):
        s = S[i].copy(); s[i] = -1
        top = names[int(s.argmax())]
        ok = lbl[int(s.argmax())] == lbl[i]
        correct += int(ok)
        print(f"{n}: rank1={top} ok={ok}")
    print(f"=== MiewID turtle-finetuned rank-1 {correct}/{len(names)} ===")
    with open("/home/jovyan/work/seaturtle_msv3_result.json", "w") as f:
        json.dump({"model": "yoavram miewid_turtle_ext_finetuned", "rank1": f"{correct}/{len(names)}"}, f)
    return 0


if __name__ == "__main__":
    import sys
    sys.argv = [sys.argv[0]]
    from PIL import Image  # global for main
    sys.path.insert(0, MDIR)
    sys.exit(main())
