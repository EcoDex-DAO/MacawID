"""Lot T3 — Ré-identification TORTUE avec le modèle dédié SeaTurtleID (MobileNetV2ReID).

Utilise le checkpoint HuggingFace marcmarais-ru/seaturtle_reid_mobilenetv2
(emb 512-d, résol 384, GeM) téléchargé dans /home/jovyan/work/turtle_reid/.
Extraits sur les 5 individus SeaTurtleID (2 imgs chacun, t243/t217/t323/t048/t441)
puis rang-1 cosinus. NOTE: licence SeaTurtleID non-commerciale; échantillon, pas
une précision globale.

Usage (conteneur jupyter) :
    python3 turtle_reid_rank.py
"""
import os, time, json
import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from model import MobileNetV2ReID

WORK = "/home/jovyan/work/turtles5"
REID = "/home/jovyan/work/turtle_reid"
# stems : (identité, image_a, image_b)
INDS = [("t243", "t1_t243_a", "t1_t243_b"),
        ("t217", "t2_t217_a", "t2_t217_b"),
        ("t323", "t3_t323_a", "t3_t323_b"),
        ("t048", "t4_t048_a", "t4_t048_b"),
        ("t441", "t5_t441_a", "t5_t441_b")]
# carapace (turtle, category_id=1) bbox (x, y, w, h) per brute stem,
# from real/turtles-data/data annotations.json.
CROPS = {
    "t1_t243_a": (613, 0, 1090, 936),
    "t1_t243_b": (215, 260, 1049, 648),
    "t2_t217_a": (400, 208, 1600, 977),
    "t2_t217_b": (298, 323, 1702, 1007),
    "t3_t323_a": (297, 184, 1197, 758),
    "t3_t323_b": (571, 412, 1141, 918),
    "t4_t048_a": (71, 395, 1303, 929),
    "t4_t048_b": (887, 730, 98, 134),
    "t5_t441_a": (621, 500, 916, 829),
    "t5_t441_b": (0, 409, 1350, 782),
}
PRE = transforms.Compose([
    transforms.Resize((384, 384)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225]),
])


def embed(model, img_path, crop=None):
    dev = next(model.parameters()).device
    im = Image.open(img_path).convert("RGB")
    if crop is not None:
        x, y, w, h = crop
        im = im.crop((x, y, x + w, y + h))
    x = PRE(im).unsqueeze(0).to(dev)
    with torch.no_grad():
        e = model(x)
    return e.squeeze().cpu().numpy()


def main():
    t = time.time()
    out = {"model": "seaturtle_reid_mobilenetv2", "notes": "HF marcmarais-ru, emb512, resol384", "results": []}
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MobileNetV2ReID.from_pretrained(REID, embedding_dim=512)
    model = model.to(dev).eval()
    print("device", dev)
    names, vecs, ind_of = [], [], {}
    for ind, a, b in INDS:
        for stem in (a, b):
            e = embed(model, f"{WORK}/{stem}", CROPS.get(stem))
            names.append(stem); vecs.append(e); ind_of[stem] = ind
    V = np.vstack(vecs)
    V = V / (np.linalg.norm(V, axis=1, keepdims=True) + 1e-9)
    S = V @ V.T
    correct = 0
    n = len(names)
    for i, nm in enumerate(names):
        s = S[i].copy(); s[i] = -1
        ranked = [names[j] for j in np.argsort(-s)]
        ok = (ind_of[ranked[0]] == ind_of[nm])
        correct += int(ok)
        out["results"].append({"img": nm, "ind": ind_of[nm], "rank1": ranked[0], "ok": ok})
        print(f"{nm} (ind {ind_of[nm]}): rank1={ranked[0]} ok={ok}")
    out["rank1"] = f"{correct}/{n}"
    out["elapsed"] = round(time.time()-t, 1)
    with open(f"{WORK}/turtle_reid_rank_result.json", "w") as f:
        json.dump(out, f, indent=1)
    print("=== RANK-1 turtle-dedicated model:", out["rank1"], "==")
    print("wrote", f"{WORK}/turtle_reid_rank_result.json")


if __name__ == "__main__":
    main()
