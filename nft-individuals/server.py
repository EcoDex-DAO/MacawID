#!/usr/bin/env python3
"""MacawID individuals page: read-only view of the individuals indexed by Wildbook,
each linked to one NFT of the generated "Las Guacamayas" collection.

Serves index.html, /api/individuals, the collection images and per-NFT metadata
on :8090. Data comes straight from the OpenSearch indices `individual` and
`encounter` (127.0.0.1:9200); nothing is written to Wildbook or OpenSearch.

Linking: a background thread polls Wildbook every LINK_EVERY seconds. Any
individual not yet in links.json gets the lowest free edition (in order of
creation), keyed by its Wildbook individual id. Links are never reassigned.
/nft/<edition>.json returns the HashLips metadata with `extensions.ara_id` etc.
filled in from the link (off-chain; nothing is minted here).
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

OPENSEARCH = "http://127.0.0.1:9200"
PUBLIC_HOST = "http://65.108.33.121"
PORT = 8090
CACHE_SECONDS = 30
LINK_EVERY = 60
HERE = Path(__file__).resolve().parent
COLLECTION = HERE / "collection"  # images/N.png, thumbs/N.webp, json/N.json
LINKS = HERE / "links.json"

_cache: dict = {"at": 0.0, "data": None}
_lock = threading.Lock()


def editions() -> list[int]:
    return sorted(int(p.stem) for p in (COLLECTION / "json").glob("*.json"))


def read_links() -> dict:
    return json.loads(LINKS.read_text()) if LINKS.exists() else {}


def link_new(inds: list[dict]) -> dict:
    """Give every unlinked individual the lowest free edition; persist atomically."""
    with _lock:
        links = read_links()
        used = {l["edition"] for l in links.values()}
        free = [e for e in editions() if e not in used]
        new = sorted((i for i in inds if i["id"] not in links), key=lambda i: i.get("version") or 0)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for i, ed in zip(new, free):
            links[i["id"]] = {"edition": ed, "name": i.get("displayName"), "linked_at": now}
        if new and free:
            tmp = LINKS.with_suffix(".tmp")
            tmp.write_text(json.dumps(links, indent=1, ensure_ascii=False))
            os.replace(tmp, LINKS)
        return links


def nft_metadata(edition: int) -> dict | None:
    p = COLLECTION / "json" / f"{edition}.json"
    if not p.exists():
        return None
    meta = json.loads(p.read_text())
    meta["image"] = f"{PUBLIC_HOST}:{PORT}/collection/images/{edition}.png"
    for ind_id, l in read_links().items():
        if l["edition"] == edition:
            meta["extensions"].update({
                "ara_id": ind_id,
                "ara_name": l["name"],
                "id_source": "wildbook",
                "id_proof_uri": f"{PUBLIC_HOST}/individuals.jsp?id={ind_id}",
                "linked_at": l["linked_at"],
                "last_modified": l["linked_at"],
                "updater": "wildbook-sync",
            })
    return meta


def search(index: str, body: dict) -> list[dict]:
    req = urllib.request.Request(
        f"{OPENSEARCH}/{index}/_search",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return [h["_source"] for h in json.load(r)["hits"]["hits"]]


def public_url(url: str | None) -> str | None:
    if not url:
        return None
    return url.replace("http://localhost:81", PUBLIC_HOST).replace("http://localhost", PUBLIC_HOST)


def featured_photo(enc: dict) -> str | None:
    assets = [a for a in enc.get("mediaAssets") or [] if a.get("mimeTypeMajor") == "image"]
    for a in assets:
        if a.get("uuid") == enc.get("featuredAssetUuid"):
            return public_url(a.get("url"))
    return public_url(assets[0].get("url")) if assets else None


def load_individuals() -> list[dict]:
    inds = search("individual", {"size": 500, "query": {"match_all": {}}})
    links = link_new(inds)
    ids = [i["id"] for i in inds]
    encs = search("encounter", {
        "size": 2000,
        "query": {"terms": {"individualId": ids}},
        "sort": [{"dateMillis": {"order": "asc", "missing": "_last"}}],
    }) if ids else []

    by_ind: dict[str, list[dict]] = {}
    for e in encs:
        by_ind.setdefault(e.get("individualId"), []).append(e)

    out = []
    for i in inds:
        mine = by_ind.get(i["id"], [])
        dates = [e["date"] for e in mine if e.get("date")]
        photo = next((p for p in map(featured_photo, mine) if p), None)
        link = links.get(i["id"])
        nft = None
        if link:
            ed = link["edition"]
            meta = json.loads((COLLECTION / "json" / f"{ed}.json").read_text())
            nft = {
                "edition": ed,
                "name": meta["name"],
                "thumb": f"/collection/thumbs/{ed}.webp",
                "image": f"/collection/images/{ed}.png",
                "metadata": f"/nft/{ed}.json",
                "attributes": meta.get("attributes", []),
                "linked_at": link["linked_at"],
            }
        out.append({
            "id": i["id"],
            "name": i.get("displayName") or (i.get("names") or ["?"])[0],
            "taxonomy": i.get("taxonomy"),
            "sex": i.get("sex"),
            "encounters": i.get("numberEncounters") or len(mine),
            "first": min(dates) if dates else None,
            "last": max(dates) if dates else None,
            "photo": photo,
            "wildbookUrl": f"{PUBLIC_HOST}/individuals.jsp?id={i['id']}",
            "nft": nft,
        })
    out.sort(key=lambda x: ((x["taxonomy"] or "~"), x["name"]))
    return out


def all_nfts() -> list[dict]:
    """Every edition of the collection, with the individual it is linked to (if any)."""
    by_ed = {l["edition"]: (ind_id, l) for ind_id, l in read_links().items()}
    taxa = {i["id"]: i for i in cached_individuals()}
    out = []
    for ed in editions():
        meta = json.loads((COLLECTION / "json" / f"{ed}.json").read_text())
        linked = None
        if ed in by_ed:
            ind_id, l = by_ed[ed]
            ind = taxa.get(ind_id, {})
            linked = {"id": ind_id, "name": l["name"], "taxonomy": ind.get("taxonomy"),
                      "photo": ind.get("photo"), "linked_at": l["linked_at"],
                      "wildbookUrl": f"{PUBLIC_HOST}/individuals.jsp?id={ind_id}"}
        out.append({
            "edition": ed, "name": meta["name"],
            "thumb": f"/collection/thumbs/{ed}.webp", "image": f"/collection/images/{ed}.png",
            "metadata": f"/nft/{ed}.json", "attributes": meta.get("attributes", []),
            "linked": linked,
        })
    return out


def cached_individuals() -> list[dict]:
    now = time.time()
    if _cache["data"] is None or now - _cache["at"] > CACHE_SECONDS:
        _cache["data"] = load_individuals()
        _cache["at"] = now
    return _cache["data"]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str, cache: bool = False) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=86400" if cache else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html", "/individuals", "/nfts"):
            self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/individuals":
            try:
                body = json.dumps(cached_individuals(), ensure_ascii=False).encode()
                self._send(200, body, "application/json; charset=utf-8")
            except Exception as e:  # noqa: BLE001
                self._send(502, json.dumps({"error": repr(e)}).encode(), "application/json")
        elif path == "/api/nfts":
            try:
                self._send(200, json.dumps(all_nfts(), ensure_ascii=False).encode(),
                           "application/json; charset=utf-8")
            except Exception as e:  # noqa: BLE001
                self._send(502, json.dumps({"error": repr(e)}).encode(), "application/json")
        elif m := re.fullmatch(r"/nft/(\d+)\.json", path):
            meta = nft_metadata(int(m.group(1)))
            if meta is None:
                self._send(404, b"not found", "text/plain")
            else:
                self._send(200, json.dumps(meta, ensure_ascii=False, indent=2).encode(),
                           "application/json; charset=utf-8")
        elif m := re.fullmatch(r"/collection/(images|thumbs)/(\d+)\.(png|webp)", path):
            f = COLLECTION / m.group(1) / f"{m.group(2)}.{m.group(3)}"
            if f.exists():
                self._send(200, f.read_bytes(), f"image/{m.group(3)}", cache=True)
            else:
                self._send(404, b"not found", "text/plain")
        else:
            self._send(404, b"not found", "text/plain")

    def log_message(self, fmt: str, *args) -> None:
        pass


def link_loop() -> None:
    """Link new individuals even when nobody has the page open."""
    while True:
        try:
            link_new(search("individual", {"size": 500, "query": {"match_all": {}}}))
        except Exception as e:  # noqa: BLE001
            print("link_loop:", repr(e), flush=True)
        time.sleep(LINK_EVERY)


if __name__ == "__main__":
    threading.Thread(target=link_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
