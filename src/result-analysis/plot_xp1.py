#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import glob
import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib as mpl

# =========================
# Matplotlib style (paper-friendly)
# =========================
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42
mpl.rcParams.update({
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "legend.fontsize": 8,
    "legend.title_fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "lines.linewidth": 1.6,
    "lines.markersize": 4.5,
})

try:
    from scipy.stats import t as student_t
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False


# =========================
# Display-name mappings
# =========================
MODEL_DISPLAY = {
    "mistral": "Mistral",
    "llama": "LLaMA",
}

DATASET_DISPLAY = {
    "blog1k": "Blog1k",
    "poems": "Poems",
    "cnn_dailymail": "News",
}


# =========================
# Helpers
# =========================
def parse_P(config):
    m = re.search(r"_P(\d+)", str(config))
    return int(m.group(1)) if m else np.nan


def parse_user_from_filename(path):
    m = re.search(r"_1_(\d+)\.csv$", os.path.basename(path))
    return int(m.group(1)) if m else None


def normalize_model_name(s: str) -> str:
    s = s.lower()
    if "mistral" in s:
        return "mistral"
    if "llama" in s:
        return "llama"
    if "gpt-oss" in s:
        return "gpt-oss"
    return s


def normalize_dataset_name(s: str) -> str:
    s = s.lower()
    if s in {"blog1k", "blog_1k", "blog"}:
        return "blog1k"
    if s in {"poems", "poetry"}:
        return "poems"
    if s in {"cnn_dailymail", "cnn", "cnn_news", "cnn-dailymail"}:
        return "cnn_dailymail"
    return s


def tcrit(conf, dof):
    if dof <= 0:
        return np.nan
    if _HAVE_SCIPY:
        return float(student_t.ppf(1 - (1 - conf) / 2, dof))
    return 1.96


def ensure_dir(p):
    os.makedirs(p, exist_ok=True)


# =========================
# Main
# =========================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input_dir", default=".")
    ap.add_argument("--pattern", default="GLOBAL_user_seed_second_match_summary_1_*.csv")
    ap.add_argument("--out_dir", default="analysis_out")
    ap.add_argument("--min_users", type=int, default=2)
    ap.add_argument("--ci", type=float, default=0.95)
    ap.add_argument("--png_dpi", type=int, default=600)

    ap.add_argument("--exclude_gpt_oss", action="store_true")
    ap.add_argument("--ci_cap", type=float, default=None)
    ap.add_argument("--ci_cap_to_P", action="store_true")
    ap.add_argument(
        "--y_mode",
        choices=["count", "rate"],
        default="count",
        help="Y-axis mode: count or rate.",
    )

    args = ap.parse_args()

    plot_dir = os.path.join(args.out_dir, "plots_combined")
    ensure_dir(plot_dir)

    # ---------- load data ----------
    frames = []
    for p in sorted(glob.glob(os.path.join(args.input_dir, args.pattern))):
        user = parse_user_from_filename(p)
        if user is None:
            continue
        df = pd.read_csv(p)
        df["user"] = user
        df["P"] = df["config"].apply(parse_P)
        df["mean_second_match"] = pd.to_numeric(df["mean_second_match"], errors="coerce")
        df["model"] = df["model"].apply(normalize_model_name)
        df["dataset"] = df["dataset"].apply(normalize_dataset_name)
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["P", "mean_second_match"])

    if args.exclude_gpt_oss:
        df = df[df["model"] != "gpt-oss"]

    model_order = ["mistral", "llama"]
    dataset_order = ["blog1k", "poems", "cnn_dailymail"]

    # ---------- aggregate + CI ----------
    g = df.groupby(["dataset", "model", "P"])
    agg = g["mean_second_match"].agg(
        n="count",
        mean="mean",
        std=lambda x: np.std(x, ddof=1) if len(x) >= 2 else 0.0
    ).reset_index()

    agg = agg[agg["n"] >= args.min_users]
    tvals = np.array([tcrit(args.ci, n - 1) for n in agg["n"]])

    if args.y_mode == "count":
        agg["y"] = agg["mean"] * agg["P"]
        half = tvals * (agg["std"] / np.sqrt(agg["n"])) * agg["P"]
        agg["ci_low"] = np.maximum(0, agg["y"] - half)
        agg["ci_high"] = agg["y"] + half
        if args.ci_cap_to_P:
            agg["ci_high"] = np.minimum(agg["ci_high"], agg["P"])
        if args.ci_cap is not None:
            agg["ci_high"] = np.minimum(agg["ci_high"], args.ci_cap)
    else:
        agg["y"] = agg["mean"]
        half = tvals * (agg["std"] / np.sqrt(agg["n"]))
        agg["ci_low"] = np.maximum(0.0, agg["y"] - half)
        agg["ci_high"] = np.minimum(1.0, agg["y"] + half)

    # ---------- plot ----------
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    model_color = {"mistral": colors[0], "llama": colors[1]}
    line_style = {"blog1k": "-", "poems": "--", "cnn_dailymail": "-."}
    marker = {"blog1k": "o", "poems": "s", "cnn_dailymail": "^"}

    for model in model_order:
        for ds in dataset_order:
            d = agg[(agg["model"] == model) & (agg["dataset"] == ds)]
            if d.empty:
                continue
            d = d.sort_values("P")
            ax.plot(
                d["P"], d["y"],
                color=model_color[model],
                linestyle=line_style[ds],
                marker=marker[ds],
            )
            ax.fill_between(
                d["P"], d["ci_low"], d["ci_high"],
                color=model_color[model],
                alpha=0.12,
                linewidth=0
            )

    ax.set_xlabel("Number of watermarked documents")
    ax.set_ylabel("Regurgitation rate" if args.y_mode == "rate"
                  else "Number of regurgitated replies")
    ax.grid(True, alpha=0.25)

    # legends
    model_handles = [
        Line2D([0], [0], color=model_color[m], lw=2, label=MODEL_DISPLAY[m])
        for m in model_order
    ]
    leg1 = ax.legend(handles=model_handles, title="Model",
                     loc="upper left", frameon=False)
    ax.add_artist(leg1)

    dataset_handles = [
        Line2D([0], [0], color="0.4", lw=1.8,
               linestyle=line_style[d], marker=marker[d],
               label=DATASET_DISPLAY[d])
        for d in dataset_order
    ]
    ax.legend(handles=dataset_handles, title="Dataset",
              loc="lower right", frameon=False)

    fig.tight_layout(pad=0.2)

    suffix = "count" if args.y_mode == "count" else "rate"
    out_png = os.path.join(plot_dir, f"singlecol_CI95_{suffix}.png")
    out_pdf = os.path.join(plot_dir, f"singlecol_CI95_{suffix}.pdf")

    fig.savefig(out_png, dpi=args.png_dpi, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)

    print("Saved:")
    print(" -", out_png)
    print(" -", out_pdf)


if __name__ == "__main__":
    main()
