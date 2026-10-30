#!/usr/bin/env python3
"""Fair head-crop comparison on 5 SeaTurtleID individuals (2 imgs each), bbox=head.
Tests: MiewID-msv3 finetuned turtles (440, 512-d) AND seaturtle MobileNetV2 (384).
Read-only. Update CKPT paths per this box.
Usage (in jupyter):  python3 turtle_head_compare.py
"""
import json
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as T
import timm
from PIL import Image

COCO = "/home/jovyan/work/coco_annotations.json"
IMG_ROOT = "/home/jovyan/work/turtles5"
CKPT = "/home/jovyan/work/hf_turtle2/models--yoavram-lab--AnimalCLEF2026-sub231/snapshots/855af5b907007b233718415899dc5ae6921f0d99/resources/weights/miewid_turtle_ext_finetuned.pt"
MINE = {'images/t243/ALfgTHysAv.jpeg':'t1_t243_a','images/t243/AhuTQfBYTN.JPG':'t1_t243_b',
        'images/t217/AuugpclqfN.JPG':'t2_t217_a','images/t217/AyeTaetytF.JPG':'t2_t217_b',
        'images/t323/ADIpQIzlZR.JPG':'t3_t323_a','images/t323/AiySvdvtDM.JPG':'t3_t323_b',
        'images/t048/AHzXGRWzlN.jpg':'t4_t048_a','images/t048/ASJDBfiBYc.JPG':'t4_t048_b',
        'images/t441/AWmdGjCEnN.JPG':'t5_t441_a','images/t441/AiXKGyQQmA.jpeg':'t5_t441_b'}
HEAD = {"t1_t243_a":1,"t1_t243_b":1,"t2_t217_a":2,"t2_t217_b":2,"t3_t323_a":3,
        "t3_t323_b":3,"t4_t048_a":4,"t4_t048_b":4,"t5_t441_a":5,"t5_t441_b":5}


def head_boxes():
    a = json.load(open(COCO))
    byimg = {i['id']: i for i in a['images']}
    boxes = {}
    for an in a['annotations']:
        f = byimg[an['image_id']]['file_name']
        if f in MINE and an.get('category_id') == 3:
            x, y, w, h = an['bbox']
            boxes[MINE[f]] = (int(x), int(y), int(x + w), int(y + h))
    return boxes


class FT(nn.Module):
    def __init__(self, sd):
        super().__init__()
        bb = timm.create_model("efficientnetv2_rw_m", pretrained=False)
        bb.load_state_dict({k: v for k, v in sd.items() if k.startswith("backbone.")}, strict=False)
        self.b = bb
        self.proj = nn.Sequential(nn.Linear(bb.num_features, 512), nn.BatchNorm1d(512))
        self.proj.load_state_dict({k.replace("proj.", "", 1): v for k, v in sd.items() if k.startswith("proj.")}, strict=False)

    def forward(self, x):
        x = self.b.forward_features(x)
        x = torch.nn.functional.adaptive_avg_pool2d(x, 1).flatten(1)
        return self.proj(x)


def run(name, model, tf):
    dev = next(model.parameters()).device
    boxes = head_boxes()
    E = []
    names = list(HEAD.keys())
    for n in names:
        img = Image.open(f"{IMG_ROOT}/{n}").convert("RGB")
        if n in boxes:
            img = img.crop(boxes[n])
        with torch.no_grad():
            emb = model(tf(img).unsqueeze(0).to(dev))
            emb = torch.nn.functional.normalize(emb, p=2, dim=1)
        E.append(emb.cpu().numpy()[0])
    sim = np.vstack(E) @ np.vstack(E).T
    cr = 0; d = {}
    for i, n in enumerate(names):
        s = sim[i].copy(); s[i] = -1
        top = [names[j] for j in np.argsort(-s)[:3]]
        ok = HEAD[top[0]] == HEAD[n]; cr += int(ok); d.setdefault(HEAD[n], []).append(ok)
    i5 = sum(1 for v in d.values() if all(v))
    print(f"[{name}] head-crop rank1 {cr}/10 | individuals-both {i5}/5")


def main():
    cp = torch.load(CKPT, map_location="cpu", weights_only=False)
    ft = FT(cp["model_state_dict"])
    ft = ft.to("cuda" if torch.cuda.is_available() else "cpu").eval()
    run("miewid_turtle_FT", ft, T.Compose([T.Resize((440, 440)), T.ToTensor(),
        T.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))]))
    from model import MobileNetV2ReID
    st = MobileNetV2ReID.from_pretrained(
        "marcmarais-ru/seaturtle_reid_mobilenetv2-quadruplet-random-combined_datasets",
        embedding_dim=512).eval()
    st = st.to("cuda" if torch.cuda.is_available() else "cpu").eval()
    run("seaturtle_ReID", st, T.Compose([T.Resize((384, 384)), T.ToTensor(),
        T.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))]))


if __name__ == "__main__":
    main()
