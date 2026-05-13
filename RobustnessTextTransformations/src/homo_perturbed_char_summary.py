#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import csv
from collections import defaultdict, Counter

# =========================
# path configuration
# =========================
INPUT_JSONL = "output/homo_perturbed.jsonl"
DETAIL_OUTPUT_JSONL = "output/homoglyph_charlevel_details.jsonl"
SUMMARY_OUTPUT_CSV = "output/homoglyph_charlevel_summary.csv"

# =========================
# Homoglyph mapping
# =========================
UNICODE_PAIRS = [
    ("abcdefghijklmnopqrstuvwxyz", "аbϲdеfɡhіϳklmnοрqrѕtuvwхуz"),
    ("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "ΑΒϹDΕFGΗΙЈΚLΜΝΟΡQRЅΤUVWΧΥΖ"),
]

CHAR_DICT = {}
for s1, s2 in UNICODE_PAIRS:
    for c1, c2 in zip(s1, s2):
        if c1 != c2:
            CHAR_DICT[c1] = c2

HOMOGLYPH_CHARS = set(CHAR_DICT.values())


# =========================
# 工具函数
# =========================
def normalize_text(text):
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    return text.replace("\r\n", "\n")


def extract_homoglyph_chars(text: str):
    text = normalize_text(text) or ""
    return [ch for ch in text if ch in HOMOGLYPH_CHARS]


def safe_ratio(num, den):
    return num / den if den not in (0, None) else None


def load_grouped_records(path: str):
    groups = defaultdict(lambda: {"origin": None, "attacks": []})

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
            except:
                continue

            sid = item.get("_sample_id")
            if sid is None:
                continue

            if item.get("attack") is None:
                groups[sid]["origin"] = item
            else:
                groups[sid]["attacks"].append(item)

    return groups


# =========================
# Core Analysis
# =========================
def analyze(origin_text, perturbed_text):
    origin_chars = extract_homoglyph_chars(origin_text)
    perturbed_chars = extract_homoglyph_chars(perturbed_text)

    origin_counter = Counter(origin_chars)
    perturbed_counter = Counter(perturbed_chars)

    exact_preserved = (origin_counter == perturbed_counter)

    return {
        "origin_count": len(origin_chars),
        "perturbed_count": len(perturbed_chars),
        "exact_preserved": exact_preserved,
        "origin_counter": dict(origin_counter),
        "perturbed_counter": dict(perturbed_counter),
    }


# =========================
# summary
# =========================
def init_summary():
    return {
        "num_records": 0,
        "num_ok_records": 0,
        "exact_preserved_count": 0,
        "sum_origin_count": 0,
        "sum_perturbed_count": 0,
    }


def update_summary(summary, attack, result):
    s = summary[attack]
    s["num_records"] += 1

    if result.get("status") != "ok":
        return

    s["num_ok_records"] += 1

    s["sum_origin_count"] += result["origin_count"]
    s["sum_perturbed_count"] += result["perturbed_count"]

    if result["exact_preserved"]:
        s["exact_preserved_count"] += 1


def finalize(summary):
    rows = []
    for attack in sorted(summary.keys()):
        s = summary[attack]
        ok = s["num_ok_records"]

        rows.append({
            "attack": attack,
            "num_records": s["num_records"],
            "num_ok_records": ok,

            "char_exact_preserved_count": s["exact_preserved_count"],
            "char_exact_preserved_rate": safe_ratio(s["exact_preserved_count"], ok),

            "avg_origin_homo_chars": safe_ratio(s["sum_origin_count"], ok),
            "avg_perturbed_homo_chars": safe_ratio(s["sum_perturbed_count"], ok),
            "remaining_ratio": safe_ratio(s["sum_perturbed_count"], s["sum_origin_count"]),
        })
    return rows


def write_csv(rows, path):
    if not rows:
        return

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


# =========================
# main
# =========================
def main():
    groups = load_grouped_records(INPUT_JSONL)
    summary = defaultdict(init_summary)

    with open(DETAIL_OUTPUT_JSONL, "w", encoding="utf-8") as out:

        for sid in groups:
            origin = groups[sid]["origin"]
            attacks = groups[sid]["attacks"]

            if origin is None:
                continue

            if not origin.get("is_watermarked", False):
                continue

            origin_text = origin.get("watermarked")
            if origin_text is None:
                continue

            comparisons = []

            for item in attacks:
                attack = item.get("attack")
                pert = item.get("perturbed_watermarked")

                if pert is None:
                    rec = {"attack": attack, "status": "missing"}
                    comparisons.append(rec)
                    update_summary(summary, attack, rec)
                    continue

                result = analyze(origin_text, pert)

                rec = {
                    "attack": attack,
                    "status": "ok",
                    **result
                }

                comparisons.append(rec)
                update_summary(summary, attack, rec)

            out.write(json.dumps({
                "_sample_id": sid,
                "comparisons": comparisons
            }, ensure_ascii=False) + "\n")

    rows = finalize(summary)
    write_csv(rows, SUMMARY_OUTPUT_CSV)

    print("Done.")
    print("Detail:", DETAIL_OUTPUT_JSONL)
    print("Summary:", SUMMARY_OUTPUT_CSV)


if __name__ == "__main__":
    main()