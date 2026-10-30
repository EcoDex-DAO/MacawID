#!/usr/bin/env python3
"""Minimal ml-service compliant with Wildbook's MlServiceClient v2 contract.

Endpoints (POST):
  /pipeline/  body {image_uri, predict_model_id?, extract_model_id?}
              -> {"success": true, "results": [ {"bbox":[x,y,w,h],"theta":0.0,
                 "type":..., "score":..., "embedding":[...]} ]}
  /extract/    body {image_uri, bbox:[x,y,w,h], theta, extract_model_id?}
              -> {"success": true, "embedding":[...]}

Model : conservationxlabs/miewid-msv3 (safetensors + trust_remote_code), embedded
by torch on CUDA. No training, no Wildbook DB access. Serves on 0.0.0.0:8000.
"""
from __future__ import annotations

import io
import os
import json

MODEL_DIR = os.environ.get("MIEWID_MODEL_DIR", "/work/miewid-msv3")
IMPORT_MODE = os.environ.get("MIEWID_IMPORT_MODE", "huggingface")  # hug or saffron
# Wildbook contract (MlServiceClient) requires each result / /extract/ top-level
# to carry embedding_model_id + embedding_model_version. MlServiceProcessor
# dash-splits embedding_model_id into {method, version} ("miewid-msv3" -> miewid/msv3).
MODEL_ID = os.environ.get("MIEWID_MODEL_ID", "miewid-msv3")
MODEL_VERSION = os.environ.get("MIEWID_MODEL_VERSION", "msv3")

_device = None
_model = None


def _load():
    global _device, _model
    if _model is not None:
        return
    import torch
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    from transformers import AutoModel, AutoConfig
    cfg = AutoConfig.from_pretrained(MODEL_DIR, trust_remote_code=True)
    _model = AutoModel.from_pretrained(
        MODEL_DIR, config=cfg, trust_remote_code=True,
        torch_dtype=torch.float16 if _device.type == "cuda" else torch.float32,
    ).to(_device)
    _model.eval()


def _load_image(image_uri: str):
    """Return a PIL image, reading from a local path or URL."""
    from PIL import Image
    if image_uri.startswith("http://") or image_uri.startswith("https://"):
        import urllib.request
        with urllib.request.urlopen(image_uri, timeout=60) as r:
            data = r.read()
        return Image.open(io.BytesIO(data)).convert("RGB")
    return Image.open(image_uri).convert("RGB")


def _embed(image):
    """MiewID forward: 440x440 image -> 2152-dim embedding (float list)."""
    import torch
    import torchvision.transforms as tf
    pre = tf.Compose([
        tf.Resize((440, 440)),
        tf.ToTensor(),
        tf.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    _load()
    x = pre(image).unsqueeze(0).to(_device)
    if _device.type == "cuda":
        x = x.half()
    with torch.no_grad():
        feat = _model(x)
    feat = feat.detach().float().cpu().numpy()
    return [float(v) for v in feat.reshape(-1)]


def _base(app, headers, body=None):
    import json as _json
    from bottle import HTTPError  # noqa: F401
    if body is None:
        # bottle gives body dict via bjson = request.json
        body = dict(request.json or {})
    image_uri = body.get("image_uri")
    if not image_uri:
        raise HTTPError(400, "image_uri required")
    image = _load_image(image_uri)
    w, h = image.size
    return image, w, h


# --- Bottle app ---------------------------------------------------------------
try:
    from bottle import Bottle, request, run
except Exception:  # pragma: no cover
    Bottle = None


def _json_response(d):
    import json as _json
    from bottle import HTTPResponse
    return HTTPResponse(_json.dumps(d), 200,
                        headers={"Content-Type": "application/json"})


if Bottle is not None:
    app = Bottle()

    @app.post("/pipeline/")
    def pipeline():
        img, w, h = _base(app, request.query, request.json)
        _load()
        emb = _embed(img)
        result = {
            "bbox": [0.0, 0.0, float(w), float(h)],
            "theta": 0.0,
            "type": "individual-bounding-box",
            "score": 1.0,
            "embedding": emb,
            "conf": 1.0,
            "embedding_model_id": MODEL_ID,
            "embedding_model_version": MODEL_VERSION,
        }
        return _json_response({"success": True, "results": [result]})

    @app.post("/extract/")
    def extract():
        import json as kfoo  # unused
        b = request.json or {}
        image_uri = b.get("image_uri")
        if not image_uri:
            from bottle import HTTPError
            raise HTTPError(400, "image_uri required")
        img = _load_image(image_uri)
        _load()
        emb = _embed(img)
        return _json_response({
            "success": True,
            "embedding": emb,
            "embedding_model_id": MODEL_ID,
            "embedding_model_version": MODEL_VERSION,
        })

    def serve(host="0.0.0.0", port=8000):
        print(f"ml-service (miewid) up on {host}:{port}, model={MODEL_DIR}", flush=True)
        run(app, host=host, port=port)


if __name__ == "__main__":
    serve()
