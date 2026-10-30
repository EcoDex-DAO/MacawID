#!/usr/bin/env python3
"""Test MiewID-msv3 finetuned on SeaTurtle (embed_dim 512) on 5 real SeaTurtleID
individuals (2 images each). Compare to msv3 (6/10) / seaturtle (0/10).
Checkpoint: yoavram-lab/AnimalCLEF2026-sub231 resources/weights/miewid_turtle_ext_finetuned.pt
Read-only. Usage (in jupyter):
    python3 miewid_turtle_test.py /home/jovyan/work/hf_turtle2/models--yoavram-lab--AnimalCLEF2026-sub231/snapshots/*/resources/weights/miewid_turtle_ext_finetuned.pt
"""
import sys
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as T
import timm
from PIL import Image

IMAGES = {
    "t1_t243_a": 1, "t1_t243_b": 1,
    "t2_t217_a": 2, "t2_t217_b": 2,
    "t3_t323_a": 3, "t3_t323_b": 3,
    "t4_t048_a": 4, "t4_t048_b": 4,
    "t5_t441_a": 5, "t5_t441_b": 5,
}
ROOT = "/home/jovyan/work/turtles5"
CKPT = sys.argv[1] if len(sys.argv) > 1 else "miewid_turtle_ext_finetuned.pt"
tf = T.Compose([
    T.Resize((440, 440)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


class MiewIdNetFT(nn.Module):
    """backbone (effv2_rw_m) + AdaptiveAvgPool + proj(->512). Forward closes images."""
    def __init__(self, sd):
        super().__init__()
        bb = timm.create_model("efficientnetv2_rw_m", pretrained=False)
        bb.load_state_dict({k: v for k, v in sd.items() if k.startswith("backbone.")}, strict=False)
        self.backbone = bb
        self.proj = nn.Sequential(nn.Linear(bb.num_features, 512), nn.BatchNorm1d(512))
        self.proj.load_state_dict({k.replace("proj.", "", 1): v for k, v in sd.items() if k.startswith("proj.")}, strict=False)

    def forward(self, x, device="cuda"):
        x = x.to(device) if torch.cuda.is_available() else x
        x = self.backbone.forward_features(x)          # (B,1792,7,7)
        x = torch.nn.functional.adaptive_avg_pool2d(x, 1).flatten(1)
        return self.proj(x)


def build(cp):
    sd = cp["model_state_dict"]
    model = MiewIdNetFT(sd)
    return model.to("cuda" if torch.cuda.is_available() else "cpu").eval()


def main():
    cp = torch.load(CKPT, map_location="cpu", weights_only=False)
    print("embed_dim", cp.get("embed_dim"), "val_mapr", cp.get("val_mapr"), "classes", cp.get("n_train_classes"))
    model = build(cp)
    names = list(IMAGES.keys())
    dev = next(model.parameters()).device
    E = []
    for n in names:
        img = Image.open(f"{ROOT}/{n}").convert("RGB")
        with torch.no_grad():
            emb = model(tf(img).unsqueeze(0).to(dev))
            emb = torch.nn.functional.normalize(emb, p=2, dim=1)
        E.append(emb.cpu().numpy()[0])
    E = np.vstack(E)
    sim = E @ E.T
    correct = 0
    inds = {}
    for i, n in enumerate(names):
        s = sim[i].copy(); s[i] = -1
        top = [names[j] for j in np.argsort(-s)[:3]]
        ok = IMAGES[top[0]] == IMAGES[n]
        correct += int(ok)
        inds.setdefault(IMAGES[n], []).append(int(ok))
        print(f"{n}: rank1={top[0]} ok={ok}")
    i5 = sum(1 for v in inds.values() if all(v))
    print(f"=== miewid_turtle rank1 {correct}/10 | individuals both {i5}/5 ===")


if __name__ == "__main__":
    main()
