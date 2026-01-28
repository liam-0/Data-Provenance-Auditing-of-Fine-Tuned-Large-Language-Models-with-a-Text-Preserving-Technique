#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Summarize per-user second_match stability across random seeds.

This script:
- Recursively finds all water*.json under a given root directory.
- Extracts (wm_version, seed, user_id, second_match) and (row_id for cnn_news).
- Extracts config = "Txxx_Ux_Px" from wm_version.
- For each (dataset, model, config, user_id):
    1) Within each seed: average second_match (0/1) values
    2) Across seeds: compute mean and variance of the per-seed averages

Special rule for cnn_news:
- cnn_news may contain multiple chunks per row_id.
- Within the same (dataset, model, config, user_id, seed, row_id),
  if ANY chunk has second_match == True, treat that row_id as success (1), else failure (0).
- Then proceed normally (per-seed average across row_ids, then across seeds mean/var).

Robustness:
- Handles non-standard JSON trailing commas (",}" and ",]").
- Robust boolean parsing for second_match (bool/int/str).
- Infers dataset/model from:
    .../dataset/processed/<dataset>/probe_outputs/<model>/...
"""

import argparse
import json
import csv
import re
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Optional

CONFIG_RE = re.compile(r"(T\d+_U\d+_P\d+)", re.IGNORECASE)


def extract_config(wm_version: str) -> str:
    if not wm_version:
        return ""
    m = CONFIG_RE.search(wm_version)
    return m.group(1) if m else ""


def safe_bool_to01(x: Any) -> Optional[int]:
    """Convert various representations to 0/1. Return None if unrecognized."""
    if isinstance(x, bool):
        return 1 if x else 0
    if isinstance(x, (int, float)) and x in (0, 1):
        return int(x)
    if isinstance(x, str):
        xl = x.strip().lower()
        if xl in ("true", "t", "yes", "y", "1"):
            return 1
        if xl in ("false", "f", "no", "n", "0"):
            return 0
    return None


def clean_trailing_commas(txt: str) -> str:
    """Fix non-standard JSON with trailing commas before } or ]."""
    return re.sub(r",\s*([}\]])", r"\1", txt)


def load_json_records(path: Path) -> List[Dict[str, Any]]:
    """
    Load records from a water*.json file.
    Common form: JSON array of dicts, but also handles:
    - dict wrapper with keys like records/data/items/results
    - non-standard trailing commas
    - (fallback) jsonl-like lines
    """
    txt = path.read_text(encoding="utf-8", errors="replace").strip()
    if not txt:
        return []

    txt2 = clean_trailing_commas(txt)

    # 1) Standard JSON
    try:
        obj = json.loads(txt2)
        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict)]
        if isinstance(obj, dict):
            for k in ("records", "data", "items", "results"):
                if k in obj and isinstance(obj[k], list):
                    return [x for x in obj[k] if isinstance(x, dict)]
            return [obj]
    except Exception:
        pass

    # 2) jsonl fallback
    records: List[Dict[str, Any]] = []
    for line in txt.splitlines():
        line = clean_trailing_commas(line.strip()).rstrip(",")
        if not line:
            continue
        try:
            r = json.loads(line)
            if isinstance(r, dict):
                records.append(r)
        except Exception:
            continue
    return records


def find_watermark_jsons(root: Path) -> List[Path]:
    """Match watermark_probe_*.json etc. by water*.json."""
    return list(root.rglob("water*.json"))


def infer_dataset_model(path: Path) -> Tuple[str, str]:
    """
    Infer dataset/model from:
      .../dataset/processed/<dataset>/probe_outputs/<model>/...
    If not found, returns ("", "").
    """
    parts = path.parts
    dataset = ""
    model = ""
    for i in range(len(parts) - 1):
        if parts[i] == "processed" and i + 1 < len(parts):
            dataset = parts[i + 1]
        if parts[i] == "probe_outputs" and i + 1 < len(parts):
            model = parts[i + 1]
    return dataset, model


def mean_var(xs: List[float]) -> Tuple[float, float]:
    """Population variance (divide by N)."""
    if not xs:
        return 0.0, 0.0
    m = sum(xs) / len(xs)
    v = sum((x - m) ** 2 for x in xs) / len(xs)
    return m, v


def main():
    parser = argparse.ArgumentParser(
        description="Summarize per-user second_match stability across random seeds from water*.json files."
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Root directory to recursively search for water*.json (default: current directory).",
    )
    parser.add_argument(
        "--out_csv",
        type=str,
        default="GLOBAL_user_seed_second_match_summary.csv",
        help="Output CSV path (default: GLOBAL_user_seed_second_match_summary.csv).",
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    out_path = Path(args.out_csv).expanduser().resolve()

    json_files = find_watermark_jsons(root)
    print(f"[INFO] ROOT = {root}")
    print(f"[INFO] found {len(json_files)} watermark json files")

    # cnn_news: aggregate chunks into row-level success per seed
    # key=(dataset, model, config, user_id, seed, row_id) -> [0/1 per chunk]
    row_bucket_ccnews = defaultdict(list)

    # Final bucket after any special handling:
    # key=(dataset, model, config, user_id, seed) -> [0/1 values]
    seed_bucket = defaultdict(list)

    # Debug counters
    cnt_files_nonempty = 0
    cnt_records_total = 0
    cnt_no_wm = 0
    cnt_no_config = 0
    cnt_no_user = 0
    cnt_no_seed = 0
    cnt_no_second = 0
    cnt_ccnews_no_rowid_fallback = 0
    cnt_kept = 0

    for jf in json_files:
        dataset, model = infer_dataset_model(jf)
        records = load_json_records(jf)
        if records:
            cnt_files_nonempty += 1

        for r in records:
            cnt_records_total += 1

            wm_version = r.get("wm_version", None)
            if wm_version is None:
                cnt_no_wm += 1
                continue
            wm_version = str(wm_version)

            config = extract_config(wm_version)
            if not config:
                cnt_no_config += 1
                continue

            user_id = r.get("user_id", None)
            if user_id is None or str(user_id) == "":
                cnt_no_user += 1
                continue
            user_id = str(user_id)

            seed = r.get("seed", None)
            if seed is None:
                cnt_no_seed += 1
                continue
            try:
                seed_norm = int(seed)
            except Exception:
                seed_norm = str(seed)

            sm01 = safe_bool_to01(r.get("second_match", None))
            if sm01 is None:
                cnt_no_second += 1
                continue

            # Special rule for cnn_news
            if dataset == "cnn_news":
                row_id = r.get("row_id", None)
                if row_id is None or str(row_id) == "":
                    # Fallback: treat record as standalone if row_id missing
                    cnt_ccnews_no_rowid_fallback += 1
                    key_seed = (dataset, model, config, user_id, seed_norm)
                    seed_bucket[key_seed].append(sm01)
                else:
                    try:
                        row_id_norm = int(row_id)
                    except Exception:
                        row_id_norm = str(row_id)
                    key_row = (dataset, model, config, user_id, seed_norm, row_id_norm)
                    row_bucket_ccnews[key_row].append(sm01)
            else:
                key_seed = (dataset, model, config, user_id, seed_norm)
                seed_bucket[key_seed].append(sm01)

            cnt_kept += 1

    # cnn_news row-level OR aggregation
    for (dataset, model, config, user_id, seed_norm, row_id), vals in row_bucket_ccnews.items():
        row_success = 1 if any(v == 1 for v in vals) else 0
        key_seed = (dataset, model, config, user_id, seed_norm)
        seed_bucket[key_seed].append(row_success)

    # Aggregate per seed -> average, then across seeds -> mean/var
    per_user_seed_avg = defaultdict(dict)  # (dataset,model,config,user)-> {seed: avg}
    for (dataset, model, config, user_id, seed_norm), vals in seed_bucket.items():
        per_user_seed_avg[(dataset, model, config, user_id)][seed_norm] = sum(vals) / len(vals)

    rows: List[Dict[str, Any]] = []
    for (dataset, model, config, user_id), seed_avg_map in per_user_seed_avg.items():
        per_seed_vals = list(seed_avg_map.values())
        m, v = mean_var(per_seed_vals)
        rows.append({
            "dataset": dataset,
            "model": model,
            "config": config,
            "user_id": user_id,
            "n_seeds": len(per_seed_vals),
            "mean_second_match": m,
            "var_second_match": v,
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "dataset", "model", "config", "user_id",
                "n_seeds", "mean_second_match", "var_second_match"
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"[OK] wrote {out_path}")
    print(f"[INFO] total rows = {len(rows)}")
    print("[DEBUG] parsing/filter stats:")
    print(f"  files_nonempty_records               = {cnt_files_nonempty}/{len(json_files)}")
    print(f"  records_total                        = {cnt_records_total}")
    print(f"  kept                                 = {cnt_kept}")
    print(f"  dropped_no_wm_version                = {cnt_no_wm}")
    print(f"  dropped_no_config(T_U_P)             = {cnt_no_config}")
    print(f"  dropped_no_user_id                   = {cnt_no_user}")
    print(f"  dropped_no_seed                      = {cnt_no_seed}")
    print(f"  dropped_no_second_match              = {cnt_no_second}")
    print(f"  cnn_news_missing_row_id_fallback     = {cnt_ccnews_no_rowid_fallback}")
    print(f"  cnn_news_row_groups                  = {len(row_bucket_ccnews)}")


if __name__ == "__main__":
    main()
