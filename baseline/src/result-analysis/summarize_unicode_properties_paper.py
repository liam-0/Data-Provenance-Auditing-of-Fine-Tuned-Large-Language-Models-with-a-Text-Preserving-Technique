#!/usr/bin/env python3
"""
Summary for unicode_properties score files.

Input: *_scores.csv produced by a unicode-properties scorer, format:
  row0: k (possibly quoted)
  row1..: per-token loss values of ONE document per row (variable length),
          stored as CSV floats: 0.12,0.34,0.56,...

This script:
- document statistic = mean token loss (optionally last_n tokens)
- W = first k documents
- N = remaining documents (null)
- p-value = one-sided empirical
- z-score = descriptive only: (mean_w - mean_null) / std_null

No trimming, no two-sided tests, no thresholds.
"""

import argparse
import csv
import glob
import os
import numpy as np


def parse_args():
    p = argparse.ArgumentParser("unicode_properties summary")
    p.add_argument("--input_dir", required=True,
                   help="Directory containing *_scores.csv files")
    p.add_argument("--output_csv", default="paper_summary.csv")
    p.add_argument("--last_n", type=int, default=0,
                   help="use only last N tokens per document (0 = use all)")
    p.add_argument("--direction", choices=["lower", "higher"], default="lower",
                   help="lower mean loss = stronger signal (usually 'lower')")
    return p.parse_args()


def _parse_k(cell: str) -> int:
    s = str(cell).strip()
    # handle quotes like "'40'" or '"40"'
    s = s.strip("'").strip('"')
    return int(float(s))


def _row_to_floats(row):
    vals = []
    for x in row:
        x = x.strip()
        if x == "":
            continue
        vals.append(float(x))
    return vals


def process_file(path: str, last_n: int, direction: str):
    doc_means = []
    k = None

    with open(path, "r", encoding="utf-8") as f:
        r = csv.reader(f)
        for i, row in enumerate(r):
            if i == 0:
                if not row:
                    raise ValueError(f"{path}: empty first row")
                k = _parse_k(row[0])
                continue

            losses = _row_to_floats(row)
            if len(losses) == 0:
                continue

            if last_n and len(losses) > last_n:
                losses = losses[-last_n:]

            doc_means.append(float(np.mean(losses)))

    if k is None:
        raise ValueError(f"{path}: failed to read k")
    if len(doc_means) < k:
        raise ValueError(f"{path}: not enough documents. k={k}, got={len(doc_means)}")

    T = np.array(doc_means, dtype=np.float64)
    W = T[:k]
    N = T[k:]

    mean_w = float(W.mean())
    mean_n = float(N.mean()) if len(N) else float("nan")
    std_n = float(N.std(ddof=1)) if len(N) > 1 else float("nan")

    z = (mean_w - mean_n) / std_n if (len(N) > 1 and std_n > 0) else float("nan")

    if len(N) == 0:
        p = float("nan")
    else:
        if direction == "lower":
            p = float(np.mean(N <= mean_w))
        else:
            p = float(np.mean(N >= mean_w))

    return {
        "file": os.path.basename(path),
        "k": k,
        "n_total": int(len(T)),
        "n_null": int(len(N)),
        "last_n": int(last_n),
        "direction": direction,
        "mean_w": mean_w,
        "mean_null": mean_n,
        "std_null": std_n,
        "z_score": float(z),
        "empirical_p_value": p,
    }


def main():
    args = parse_args()

    files = sorted(glob.glob(os.path.join(args.input_dir, "*_scores.csv")))
    if not files:
        raise RuntimeError(f"No *_scores.csv found in {args.input_dir}")

    rows = []
    for f in files:
        rows.append(process_file(f, args.last_n, args.direction))

    out_path = args.output_csv
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("===== SUMMARY =====")
    for r in rows:
        print(r)
    print("===================")
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
