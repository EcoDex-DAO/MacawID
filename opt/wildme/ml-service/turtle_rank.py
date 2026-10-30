#!/usr/bin/env python3
"""Analyze/rank MiewID msv3 embeddings over N real turtle individuals.

Reads embeddings produced by the ml-service (/extract/) for 2 images per
individual and reports cosine rank-1 (does image `_a` match its own `_b`?).

Proof basis for MESSAGE-codex-5-tortues.md: the ml-service msv3 can embed real
SeaTurtleID turtles (Any species; independent of the blocked WBIA turtle .bin).

Usage (inside jupyter, after running the extract loop):
    python3 turtle_rank.py /home/jovyan/work/turtles5 emb_t1_t243_a.json ...
Or with a simple manifest below. Read-only.
"""
import json, os, sys
import numpy as np

# (file-stem, individual-index) for the 5 SeaTurtleID individuals seeded.
MANIFEST = [
    ("emb_t1_t243_a", 1), ("emb_t1_t243_b", 1),
    ("emb_t2_t217_a", 2), ("emb_t2_t217_b", 2),
    ("emb_t3_t323_a", 3), ("emb_t3_t323_b", 3),
    ("emb_t4_t048_a", 4), ("emb_t4_t048_b", 4),
    ("emb_t5_t441_a", 5), ("emb_t5_t441_b", 5),
]


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "/home/jovyan/work/turtles5"
    embs = {}
    for stem, _ in MANIFEST:
        p = os.path.join(root, stem + ".json")
        if not os.path.exists(p):
            print("missing", p)
            sys.exit(2)
        embs[stem] = np.array(json.load(open(p))["embedding"], dtype=float)
    E = np.vstack([embs[s] for s, _ in MANIFEST])
    E = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
    sim = E @ E.T
    names = [s for s, _ in MANIFEST]
    ind_of = {s: ind for s, ind in MANIFEST}   # stem -> individual index (1..5)
    correct = 0
    ind_neighbors = {}
    for i, (n, ind) in enumerate(MANIFEST):
        s = sim[i].copy(); s[i] = -1
        top = [names[j] for j in np.argsort(-s)[:3]]
        ok = ind_of[top[0]] == ind
        correct += int(ok)
        ind_neighbors.setdefault(ind, []).append(int(ok))
        print(f"{n} (ind{ind}): rank1={top[0]} ok={ok} | next={top[1:]}")
    inds_ok = sum(1 for ind, oks in ind_neighbors.items() if all(oks))
    print(f"=== rank1 {correct}/{len(MANIFEST)}  | individuals with both "
          f"images rank-1 correct: {inds_ok}/5 ===")
    print("NOTE: sample only; NOT a precision claim. License SeaTurtleID "
          "non-commercial.")


if __name__ == "__main__":
    main()
