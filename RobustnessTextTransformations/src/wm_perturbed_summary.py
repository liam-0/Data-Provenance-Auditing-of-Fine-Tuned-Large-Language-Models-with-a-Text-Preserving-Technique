#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import csv
from collections import Counter, defaultdict

# =========================
# path configuration
# =========================
INPUT_JSONL = "output/train_perturbed.jsonl"
DETAIL_OUTPUT_JSONL = "output/train_perturbed_wm_compare.jsonl"
SUMMARY_OUTPUT_CSV = "output/train_perturbed_wm_summary.csv"

# Statistics based on complete watermark samples
ALTERATION_SUMMARY_CSV = "output/train_perturbed_wm_alteration_summary.csv"

ALPHABET_FILE = "alphabet.txt"

# strict: Must strictly follow the loop c1->c2->c3->c4 continuously

# relaxed: Allows missing segments, but does not allow reverse or out-of-order execution

# both: Counts both
ORDER_MODE = "both"   # "strict" / "relaxed" / "both"

CLUSTER_SIZE = 4


# =========================
# 工具函数
# =========================
def load_alphabet_from_txt(path: str) -> list[str]:
    alphabet = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^U\+([0-9A-Fa-f]+)", line)
            if not m:
                continue
            code_point = int(m.group(1), 16)
            try:
                ch = chr(code_point)
            except ValueError:
                continue
            alphabet.append(ch)

    seen = set()
    dedup = []
    for ch in alphabet:
        if ch not in seen:
            seen.add(ch)
            dedup.append(ch)
    return dedup


def normalize_text(text):
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    return text.replace("\r\n", "\n")


def extract_zws_sequence(text: str, zws_set: set[str]) -> str:
    text = normalize_text(text) or ""
    return "".join(ch for ch in text if ch in zws_set)


def split_into_clusters(seq: str, cluster_size: int = CLUSTER_SIZE) -> list[str]:
    m = len(seq) - (len(seq) % cluster_size)
    return [seq[i:i + cluster_size] for i in range(0, m, cluster_size)]


def build_cycle_clusters(wm: str, cluster_size: int = CLUSTER_SIZE) -> list[str]:
    return split_into_clusters(wm, cluster_size)


def count_clusters(cluster_seq: list[str], target_clusters: list[str]) -> dict[str, int]:
    c = Counter(cluster_seq)
    return {cl: c.get(cl, 0) for cl in target_clusters}


def compare_counts(origin_counts: dict[str, int], pert_counts: dict[str, int]) -> dict:
    lost_per_cluster = {}
    total_origin = 0
    total_pert = 0

    for k in origin_counts:
        o = origin_counts.get(k, 0)
        p = pert_counts.get(k, 0)
        total_origin += o
        total_pert += p
        lost_per_cluster[k] = max(o - p, 0)

    missing_cluster_count = sum(1 for k, v in pert_counts.items() if v == 0)

    return {
        "origin_total_cluster_hits": total_origin,
        "perturbed_total_cluster_hits": total_pert,
        "lost_total_cluster_hits": max(total_origin - total_pert, 0),
        "lost_cluster_hit_ratio": (
            max(total_origin - total_pert, 0) / total_origin if total_origin > 0 else None
        ),
        "missing_cluster_count": missing_cluster_count,
        "lost_per_cluster": lost_per_cluster,
    }


def encode_cluster_ids(cluster_seq: list[str], target_clusters: list[str]) -> list[int]:
    cluster_to_id = {c: i for i, c in enumerate(target_clusters)}
    return [cluster_to_id[c] for c in cluster_seq if c in target_clusters]


def longest_strict_prefix_match(ids: list[int], cycle_len: int) -> int:
    if not ids:
        return 0
    matched = 1
    prev = ids[0]
    for x in ids[1:]:
        if x == (prev + 1) % cycle_len:
            matched += 1
            prev = x
        else:
            break
    return matched


def check_order_strict(cluster_seq: list[str], target_clusters: list[str]) -> dict:
    ids = encode_cluster_ids(cluster_seq, target_clusters)
    cycle_len = len(target_clusters)

    if not ids:
        return {
            "matched_cluster_ids": [],
            "cluster_order_preserved_strict": False,
            "strict_prefix_len": 0,
            "recoverable_full_cycle_strict": False,
        }

    strict_prefix_len = longest_strict_prefix_match(ids, cycle_len)
    recoverable_full_cycle_strict = strict_prefix_len >= cycle_len
    cluster_order_preserved_strict = strict_prefix_len == len(ids)

    return {
        "matched_cluster_ids": ids,
        "cluster_order_preserved_strict": cluster_order_preserved_strict,
        "strict_prefix_len": strict_prefix_len,
        "recoverable_full_cycle_strict": recoverable_full_cycle_strict,
    }


def check_order_relaxed(cluster_seq: list[str], target_clusters: list[str]) -> dict:
    ids = encode_cluster_ids(cluster_seq, target_clusters)
    cycle_len = len(target_clusters)

    if not ids:
        return {
            "matched_cluster_ids": [],
            "cluster_order_preserved_relaxed": False,
            "recoverable_full_cycle_relaxed": False,
            "seen_all_cluster_types_in_order": False,
        }

    next_required = ids[0]
    consumed = 0
    for x in ids:
        if x == next_required:
            consumed += 1
            next_required = (next_required + 1) % cycle_len

    recoverable_full_cycle_relaxed = consumed >= cycle_len
    cluster_order_preserved_relaxed = consumed >= 1
    seen_all_cluster_types_in_order = recoverable_full_cycle_relaxed

    return {
        "matched_cluster_ids": ids,
        "cluster_order_preserved_relaxed": cluster_order_preserved_relaxed,
        "recoverable_full_cycle_relaxed": recoverable_full_cycle_relaxed,
        "seen_all_cluster_types_in_order": seen_all_cluster_types_in_order,
    }


def wm_string_exact_match_from_clusters(cluster_seq: list[str], wm_clusters: list[str]) -> bool:
    n = len(wm_clusters)
    if n == 0 or len(cluster_seq) < n:
        return False
    for i in range(len(cluster_seq) - n + 1):
        if cluster_seq[i:i + n] == wm_clusters:
            return True
    return False


def count_full_string_occurrences_nonoverlap(cluster_seq: list[str], wm_clusters: list[str]) -> int:
    """
    统计 wm_clusters 在 cluster_seq 中完整出现的次数（不允许重叠）
    """
    n = len(wm_clusters)
    if n == 0 or len(cluster_seq) < n:
        return 0

    cnt = 0
    i = 0
    while i <= len(cluster_seq) - n:
        if cluster_seq[i:i + n] == wm_clusters:
            cnt += 1
            i += n
        else:
            i += 1
    return cnt


def analyze_one_half(origin_cluster_seq: list[str], pert_cluster_seq: list[str], wm: str, cluster_size: int):
    wm_clusters = build_cycle_clusters(wm, cluster_size)
    origin_counts = count_clusters(origin_cluster_seq, wm_clusters)
    pert_counts = count_clusters(pert_cluster_seq, wm_clusters)
    count_stats = compare_counts(origin_counts, pert_counts)

    origin_full_string_count = count_full_string_occurrences_nonoverlap(origin_cluster_seq, wm_clusters)
    perturbed_full_string_count = count_full_string_occurrences_nonoverlap(pert_cluster_seq, wm_clusters)

    result = {
        "wm_length_chars": len(wm),
        "wm_cluster_count": len(wm_clusters),
        "wm_clusters": wm_clusters,

        "full_string_exact_match": wm_string_exact_match_from_clusters(pert_cluster_seq, wm_clusters),

        "origin_full_string_count": origin_full_string_count,
        "perturbed_full_string_count": perturbed_full_string_count,
        "full_string_remaining_ratio": (
            perturbed_full_string_count / origin_full_string_count
            if origin_full_string_count > 0 else None
        ),

        "origin_cluster_counts": origin_counts,
        "perturbed_cluster_counts": pert_counts,
        **count_stats,
    }

    if ORDER_MODE in ("strict", "both"):
        result.update(check_order_strict(pert_cluster_seq, wm_clusters))
    if ORDER_MODE in ("relaxed", "both"):
        result.update(check_order_relaxed(pert_cluster_seq, wm_clusters))

    return result


def safe_half_split(text: str) -> tuple[str, str]:
    words = str(text).split()
    mid = len(words) // 2
    return " ".join(words[:mid]), " ".join(words[mid:])


def classify_sample_level_alteration(compare_result: dict) -> str:
    """
    以完整 watermark（wm_first + wm_second）为单位分类：

    unchanged:
        zws_exact_match == True

    full_suppression:
        altered 且 perturbed_zws_count == 0

    partial_modification:
        altered 且非 full_suppression，
        且 wm_first / wm_second 都至少可恢复一个完整 strict cycle

    altered_not_fully_recoverable:
        altered 但不属于上面两类
    """
    zws_exact_match = compare_result.get("zws_exact_match") is True
    perturbed_zws_count = compare_result.get("perturbed_zws_count", 0) or 0

    first = compare_result.get("wm_first_analysis", {})
    second = compare_result.get("wm_second_analysis", {})

    first_rec = first.get("recoverable_full_cycle_strict") is True
    second_rec = second.get("recoverable_full_cycle_strict") is True

    if zws_exact_match:
        return "unchanged"

    if perturbed_zws_count == 0:
        return "full_suppression"

    if first_rec and second_rec:
        return "partial_modification"

    return "altered_not_fully_recoverable"


def analyze_origin_vs_attack(origin_text: str, perturbed_text: str, wm_first: str, wm_second: str, zws_set: set[str]):
    origin_text = normalize_text(origin_text) or ""
    perturbed_text = normalize_text(perturbed_text) or ""

    origin_zws = extract_zws_sequence(origin_text, zws_set)
    pert_zws = extract_zws_sequence(perturbed_text, zws_set)

    overall = {
        "zws_exact_match": origin_zws == pert_zws,
        "origin_zws_count": len(origin_zws),
        "perturbed_zws_count": len(pert_zws),
        "zws_lost_count": max(len(origin_zws) - len(pert_zws), 0),
        "zws_lost_ratio": (
            max(len(origin_zws) - len(pert_zws), 0) / len(origin_zws) if len(origin_zws) > 0 else None
        ),
    }

    origin_a, origin_b = safe_half_split(origin_text)
    origin_a_zws = extract_zws_sequence(origin_a, zws_set)
    origin_b_zws = extract_zws_sequence(origin_b, zws_set)

    origin_a_clusters = split_into_clusters(origin_a_zws, CLUSTER_SIZE)
    origin_b_clusters = split_into_clusters(origin_b_zws, CLUSTER_SIZE)

    # zws完全一致时，sample级比例直接记为1，不再额外匹配 perturbed side
    if overall["zws_exact_match"]:
        wm_first_result = analyze_one_half(origin_a_clusters, origin_a_clusters, wm_first, CLUSTER_SIZE)
        wm_second_result = analyze_one_half(origin_b_clusters, origin_b_clusters, wm_second, CLUSTER_SIZE)

        origin_full_watermark_count = min(
            wm_first_result.get("origin_full_string_count", 0) or 0,
            wm_second_result.get("origin_full_string_count", 0) or 0,
        )
        perturbed_full_watermark_count = origin_full_watermark_count
        sample_full_watermark_remaining_ratio = 1.0 if origin_full_watermark_count > 0 else None

    else:
        pert_a, pert_b = safe_half_split(perturbed_text)
        pert_a_zws = extract_zws_sequence(pert_a, zws_set)
        pert_b_zws = extract_zws_sequence(pert_b, zws_set)

        pert_a_clusters = split_into_clusters(pert_a_zws, CLUSTER_SIZE)
        pert_b_clusters = split_into_clusters(pert_b_zws, CLUSTER_SIZE)

        wm_first_result = analyze_one_half(origin_a_clusters, pert_a_clusters, wm_first, CLUSTER_SIZE)
        wm_second_result = analyze_one_half(origin_b_clusters, pert_b_clusters, wm_second, CLUSTER_SIZE)

        origin_full_watermark_count = min(
            wm_first_result.get("origin_full_string_count", 0) or 0,
            wm_second_result.get("origin_full_string_count", 0) or 0,
        )
        perturbed_full_watermark_count = min(
            wm_first_result.get("perturbed_full_string_count", 0) or 0,
            wm_second_result.get("perturbed_full_string_count", 0) or 0,
        )
        sample_full_watermark_remaining_ratio = (
            perturbed_full_watermark_count / origin_full_watermark_count
            if origin_full_watermark_count > 0 else None
        )

    result = {
        **overall,
        "wm_first_analysis": wm_first_result,
        "wm_second_analysis": wm_second_result,
        "origin_full_watermark_count": origin_full_watermark_count,
        "perturbed_full_watermark_count": perturbed_full_watermark_count,
        "sample_full_watermark_remaining_ratio": sample_full_watermark_remaining_ratio,
    }

    result["sample_alteration_type"] = classify_sample_level_alteration(result)
    return result


def load_grouped_records(path: str):
    groups = defaultdict(lambda: {"origin": None, "attacks": []})
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                print(f"[WARN] line {line_no} JSON 解析失败，跳过")
                continue

            sid = item.get("_sample_id")
            if sid is None:
                print(f"[WARN] line {line_no} 缺少 _sample_id，跳过")
                continue

            if item.get("attack") is None:
                groups[sid]["origin"] = item
            else:
                groups[sid]["attacks"].append(item)
    return groups


# =========================
# 原有 summary 汇总
# =========================
def init_attack_summary():
    return {
        "num_records": 0,
        "num_ok_records": 0,

        "sum_origin_zws_count": 0,
        "sum_perturbed_zws_count": 0,
        "sum_zws_lost_count": 0,

        "num_zws_exact_match": 0,

        "num_wm_first_full_string_exact_match": 0,
        "num_wm_second_full_string_exact_match": 0,

        "num_wm_first_recoverable_full_cycle_strict": 0,
        "num_wm_second_recoverable_full_cycle_strict": 0,

        "num_wm_first_recoverable_full_cycle_relaxed": 0,
        "num_wm_second_recoverable_full_cycle_relaxed": 0,

        "num_wm_first_cluster_order_preserved_strict": 0,
        "num_wm_second_cluster_order_preserved_strict": 0,

        "num_wm_first_cluster_order_preserved_relaxed": 0,
        "num_wm_second_cluster_order_preserved_relaxed": 0,

        "sum_wm_first_origin_cluster_hits": 0,
        "sum_wm_first_perturbed_cluster_hits": 0,
        "sum_wm_first_lost_cluster_hits": 0,

        "sum_wm_second_origin_cluster_hits": 0,
        "sum_wm_second_perturbed_cluster_hits": 0,
        "sum_wm_second_lost_cluster_hits": 0,

        # 仅保留你要的 sample-wise 平均比例
        "sum_sample_full_watermark_remaining_ratio": 0.0,
        "num_sample_full_watermark_remaining_ratio": 0,
    }


def update_attack_summary(summary_dict, attack_name, compare_item):
    s = summary_dict[attack_name]
    s["num_records"] += 1

    if compare_item.get("compare_status") != "ok":
        return

    s["num_ok_records"] += 1

    s["sum_origin_zws_count"] += compare_item.get("origin_zws_count", 0) or 0
    s["sum_perturbed_zws_count"] += compare_item.get("perturbed_zws_count", 0) or 0
    s["sum_zws_lost_count"] += compare_item.get("zws_lost_count", 0) or 0

    if compare_item.get("zws_exact_match") is True:
        s["num_zws_exact_match"] += 1

    first = compare_item.get("wm_first_analysis", {})
    second = compare_item.get("wm_second_analysis", {})

    if first.get("full_string_exact_match") is True:
        s["num_wm_first_full_string_exact_match"] += 1
    if second.get("full_string_exact_match") is True:
        s["num_wm_second_full_string_exact_match"] += 1

    if first.get("recoverable_full_cycle_strict") is True:
        s["num_wm_first_recoverable_full_cycle_strict"] += 1
    if second.get("recoverable_full_cycle_strict") is True:
        s["num_wm_second_recoverable_full_cycle_strict"] += 1

    if first.get("recoverable_full_cycle_relaxed") is True:
        s["num_wm_first_recoverable_full_cycle_relaxed"] += 1
    if second.get("recoverable_full_cycle_relaxed") is True:
        s["num_wm_second_recoverable_full_cycle_relaxed"] += 1

    if first.get("cluster_order_preserved_strict") is True:
        s["num_wm_first_cluster_order_preserved_strict"] += 1
    if second.get("cluster_order_preserved_strict") is True:
        s["num_wm_second_cluster_order_preserved_strict"] += 1

    if first.get("cluster_order_preserved_relaxed") is True:
        s["num_wm_first_cluster_order_preserved_relaxed"] += 1
    if second.get("cluster_order_preserved_relaxed") is True:
        s["num_wm_second_cluster_order_preserved_relaxed"] += 1

    s["sum_wm_first_origin_cluster_hits"] += first.get("origin_total_cluster_hits", 0) or 0
    s["sum_wm_first_perturbed_cluster_hits"] += first.get("perturbed_total_cluster_hits", 0) or 0
    s["sum_wm_first_lost_cluster_hits"] += first.get("lost_total_cluster_hits", 0) or 0

    s["sum_wm_second_origin_cluster_hits"] += second.get("origin_total_cluster_hits", 0) or 0
    s["sum_wm_second_perturbed_cluster_hits"] += second.get("perturbed_total_cluster_hits", 0) or 0
    s["sum_wm_second_lost_cluster_hits"] += second.get("lost_total_cluster_hits", 0) or 0

    ratio_fw = compare_item.get("sample_full_watermark_remaining_ratio")
    if ratio_fw is not None:
        s["sum_sample_full_watermark_remaining_ratio"] += ratio_fw
        s["num_sample_full_watermark_remaining_ratio"] += 1


def safe_ratio(num, den):
    return num / den if den not in (0, None) else None


def finalize_summary_rows(summary_dict):
    rows = []
    for attack_name in sorted(summary_dict.keys()):
        s = summary_dict[attack_name]
        ok_n = s["num_ok_records"]

        row = {
            "attack": attack_name,
            "num_records": s["num_records"],
            "num_ok_records": ok_n,

            "overall_zws_exact_match_rate": safe_ratio(s["num_zws_exact_match"], ok_n),
            "overall_zws_loss_rate": safe_ratio(s["sum_zws_lost_count"], s["sum_origin_zws_count"]),
            "avg_remaining_zws_ratio": safe_ratio(s["sum_perturbed_zws_count"], s["sum_origin_zws_count"]),

            "wm_first_full_string_exact_match_rate": safe_ratio(s["num_wm_first_full_string_exact_match"], ok_n),
            "wm_second_full_string_exact_match_rate": safe_ratio(s["num_wm_second_full_string_exact_match"], ok_n),

            "wm_first_recoverable_full_cycle_strict_rate": safe_ratio(s["num_wm_first_recoverable_full_cycle_strict"], ok_n),
            "wm_second_recoverable_full_cycle_strict_rate": safe_ratio(s["num_wm_second_recoverable_full_cycle_strict"], ok_n),

            "wm_first_recoverable_full_cycle_relaxed_rate": safe_ratio(s["num_wm_first_recoverable_full_cycle_relaxed"], ok_n),
            "wm_second_recoverable_full_cycle_relaxed_rate": safe_ratio(s["num_wm_second_recoverable_full_cycle_relaxed"], ok_n),

            "wm_first_cluster_order_preserved_strict_rate": safe_ratio(s["num_wm_first_cluster_order_preserved_strict"], ok_n),
            "wm_second_cluster_order_preserved_strict_rate": safe_ratio(s["num_wm_second_cluster_order_preserved_strict"], ok_n),

            "wm_first_cluster_order_preserved_relaxed_rate": safe_ratio(s["num_wm_first_cluster_order_preserved_relaxed"], ok_n),
            "wm_second_cluster_order_preserved_relaxed_rate": safe_ratio(s["num_wm_second_cluster_order_preserved_relaxed"], ok_n),

            "wm_first_cluster_hit_loss_rate": safe_ratio(
                s["sum_wm_first_lost_cluster_hits"],
                s["sum_wm_first_origin_cluster_hits"]
            ),
            "wm_second_cluster_hit_loss_rate": safe_ratio(
                s["sum_wm_second_lost_cluster_hits"],
                s["sum_wm_second_origin_cluster_hits"]
            ),

            "wm_first_remaining_cluster_hit_ratio": safe_ratio(
                s["sum_wm_first_perturbed_cluster_hits"],
                s["sum_wm_first_origin_cluster_hits"]
            ),
            "wm_second_remaining_cluster_hit_ratio": safe_ratio(
                s["sum_wm_second_perturbed_cluster_hits"],
                s["sum_wm_second_origin_cluster_hits"]
            ),

            # 你要的sample-wise平均比例
            "avg_sample_full_watermark_remaining_ratio": safe_ratio(
                s["sum_sample_full_watermark_remaining_ratio"],
                s["num_sample_full_watermark_remaining_ratio"]
            ),
        }
        rows.append(row)
    return rows


def write_summary_csv(rows, path):
    if not rows:
        print(f"[WARN] 没有汇总行可写: {path}")
        return

    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# =========================
# 样本级完整 watermark alteration 汇总
# =========================
def init_alteration_summary():
    return {
        "num_records": 0,
        "num_ok_records": 0,

        # 一个 ok 样本对应一个 unique watermark
        "total_unique_watermarks": 0,

        "unchanged_count": 0,
        "altered_at_least_once_count": 0,
        "full_suppression_count": 0,
        "partial_modification_count": 0,
        "altered_not_fully_recoverable_count": 0,
    }


def update_alteration_summary(summary_dict, attack_name, compare_item):
    s = summary_dict[attack_name]
    s["num_records"] += 1

    if compare_item.get("compare_status") != "ok":
        return

    s["num_ok_records"] += 1
    s["total_unique_watermarks"] += 1

    state = compare_item.get("sample_alteration_type")

    if state == "unchanged":
        s["unchanged_count"] += 1
    elif state == "full_suppression":
        s["altered_at_least_once_count"] += 1
        s["full_suppression_count"] += 1
    elif state == "partial_modification":
        s["altered_at_least_once_count"] += 1
        s["partial_modification_count"] += 1
    elif state == "altered_not_fully_recoverable":
        s["altered_at_least_once_count"] += 1
        s["altered_not_fully_recoverable_count"] += 1


def finalize_alteration_rows(summary_dict):
    rows = []
    for attack_name in sorted(summary_dict.keys()):
        s = summary_dict[attack_name]
        total_n = s["total_unique_watermarks"]
        altered_n = s["altered_at_least_once_count"]
        full_sup_n = s["full_suppression_count"]
        partial_n = s["partial_modification_count"]
        altered_unrec_n = s["altered_not_fully_recoverable_count"]

        row = {
            "attack": attack_name,
            "num_records": s["num_records"],
            "num_ok_records": s["num_ok_records"],
            "total_unique_watermarks": total_n,

            "unchanged_count": s["unchanged_count"],
            "unchanged_ratio": safe_ratio(s["unchanged_count"], total_n),

            "altered_at_least_once_count": altered_n,
            "altered_at_least_once_ratio": safe_ratio(altered_n, total_n),

            "full_suppression_count": full_sup_n,
            "full_suppression_ratio": safe_ratio(full_sup_n, total_n),

            "partial_modification_count": partial_n,
            "partial_modification_ratio": safe_ratio(partial_n, total_n),

            "altered_not_fully_recoverable_count": altered_unrec_n,
            "altered_not_fully_recoverable_ratio": safe_ratio(altered_unrec_n, total_n),

            "full_suppression_share_within_altered": safe_ratio(full_sup_n, altered_n),
            "partial_modification_share_within_altered": safe_ratio(partial_n, altered_n),
            "altered_not_fully_recoverable_share_within_altered": safe_ratio(altered_unrec_n, altered_n),
        }
        rows.append(row)
    return rows


# =========================
# main
# =========================
def main():
    zws_alphabet = load_alphabet_from_txt(ALPHABET_FILE)
    zws_set = set(zws_alphabet)

    print(f"Loaded {len(zws_alphabet)} ZW chars from {ALPHABET_FILE}")
    print("First few code points:", [f"U+{ord(c):04X}" for c in zws_alphabet[:8]])

    groups = load_grouped_records(INPUT_JSONL)
    total_written = 0

    attack_summary = defaultdict(init_attack_summary)
    alteration_summary = defaultdict(init_alteration_summary)

    with open(DETAIL_OUTPUT_JSONL, "w", encoding="utf-8") as out:
        for sid in sorted(groups.keys()):
            origin = groups[sid]["origin"]
            attacks = groups[sid]["attacks"]

            if origin is None:
                rec = {
                    "_sample_id": sid,
                    "status": "missing_origin",
                    "comparisons": [],
                }
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                total_written += 1
                continue

            origin_text = origin.get("perturbed_watermarked")
            if origin_text is None:
                origin_text = origin.get("watermarked")

            wm_first = origin.get("wm_first", "")
            wm_second = origin.get("wm_second", "")

            comparisons = []
            for attack_item in attacks:
                attack_name = attack_item.get("attack")
                perturbed_text = attack_item.get("perturbed_watermarked")

                if perturbed_text is None:
                    compare_rec = {
                        "attack": attack_name,
                        "_status": attack_item.get("_status"),
                        "compare_status": "missing_perturbed_text",
                    }
                    comparisons.append(compare_rec)
                    update_attack_summary(attack_summary, attack_name, compare_rec)
                    update_alteration_summary(alteration_summary, attack_name, compare_rec)
                    continue

                result = analyze_origin_vs_attack(
                    origin_text=origin_text,
                    perturbed_text=perturbed_text,
                    wm_first=wm_first,
                    wm_second=wm_second,
                    zws_set=zws_set,
                )

                compare_rec = {
                    "attack": attack_name,
                    "_status": attack_item.get("_status"),
                    "compare_status": "ok",
                    **result,
                }
                comparisons.append(compare_rec)

                update_attack_summary(attack_summary, attack_name, compare_rec)
                update_alteration_summary(alteration_summary, attack_name, compare_rec)

            rec = {
                "_sample_id": sid,
                "status": "ok",
                "is_watermarked": origin.get("is_watermarked"),
                "user_id": origin.get("user_id"),
                "wm_first": wm_first,
                "wm_second": wm_second,
                "origin_status": origin.get("_status"),
                "num_attacks_found": len(attacks),
                "comparisons": comparisons,
            }

            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            total_written += 1

    summary_rows = finalize_summary_rows(attack_summary)
    write_summary_csv(summary_rows, SUMMARY_OUTPUT_CSV)

    alteration_rows = finalize_alteration_rows(alteration_summary)
    write_summary_csv(alteration_rows, ALTERATION_SUMMARY_CSV)

    print(f"Done. Wrote {total_written} grouped records to:")
    print(DETAIL_OUTPUT_JSONL)
    print("Summary CSV written to:")
    print(SUMMARY_OUTPUT_CSV)
    print("Alteration summary CSV written to:")
    print(ALTERATION_SUMMARY_CSV)


if __name__ == "__main__":
    main()