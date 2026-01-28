#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import re
import glob
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


# =========================
# Utils
# =========================

def parse_dataset_model(path: str):
    """
    Expect filename like: paper_summary_<dataset>_<model>.csv
    Example: paper_summary_blog1k_llama.csv
    Returns (dataset, model). If fail, returns (stem, "unknown")
    """
    base = os.path.basename(path)
    stem = os.path.splitext(base)[0]
    m = re.match(r"paper_summary_([^_]+)_(.+)$", stem)
    if m:
        return m.group(1), m.group(2)
    return stem, "unknown"


def normalize_model_name(m: str) -> str:
    mm = m.lower()
    if "llama" in mm:
        return "LLaMA"
    if "mistral" in mm:
        return "Mistral"
    return m


def load_one(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # accept both schemas
    if "z_score" in df.columns:
        zcol = "z_score"
    elif "z_mean_w_vs_null" in df.columns:
        zcol = "z_mean_w_vs_null"
    else:
        raise ValueError(f"{path}: need z_score or z_mean_w_vs_null. got={list(df.columns)}")

    if "file" not in df.columns:
        raise ValueError(f"{path}: need 'file' column. got={list(df.columns)}")

    # extract anonymous user ids
    df["user_id"] = df["file"].astype(str).str.extract(r"(user_\d{4})", expand=False)
    df = df.dropna(subset=["user_id"]).copy()

    dataset, model = parse_dataset_model(path)
    df = df[["user_id", zcol]].rename(columns={zcol: "z"}).copy()
    df["dataset"] = dataset
    df["model"] = normalize_model_name(model)
    df["source_path"] = path
    return df


def stable_unique(seq):
    seen = set()
    out = []
    for x in seq:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


# =========================
# Main
# =========================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input_glob", required=True,
                    help='Glob for summary CSVs, e.g. "./paper_summary_*.csv"')
    ap.add_argument("--out_pdf", default="fig_unicode_properties.pdf")
    ap.add_argument("--out_png", default=None)
    ap.add_argument("--z_threshold", type=float, default=-2.0)

    # ICML single-column size
    ap.add_argument("--fig_width_in", type=float, default=3.25)
    ap.add_argument("--fig_height_in", type=float, default=2.6)
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()

    paths = sorted(glob.glob(args.input_glob))
    if not paths:
        raise FileNotFoundError(f"No files matched: {args.input_glob}")

    df = pd.concat([load_one(p) for p in paths], ignore_index=True)

    datasets = stable_unique(df["dataset"].tolist())
    models = stable_unique(df["model"].tolist())
    users = sorted(df["user_id"].unique())

    # =========================
    # Watermark display names
    # =========================
    user_display = {u: f"Watermark {i+1}" for i, u in enumerate(users)}

    # =========================
    # Fixed jitter per watermark
    # =========================
    if len(users) == 1:
        offsets = {users[0]: 0.0}
    else:
        spread = 0.28
        step = (2 * spread) / (len(users) - 1)
        offsets = {u: (-spread + i * step) for i, u in enumerate(users)}

    x_index = {d: i for i, d in enumerate(datasets)}

    # =========================
    # Colors per watermark
    # =========================
    default_colors = plt.rcParams["axes.prop_cycle"].by_key().get("color", [])
    if not default_colors:
        default_colors = ["C0", "C1", "C2", "C3", "C4"]
    user_color = {u: default_colors[i % len(default_colors)] for i, u in enumerate(users)}

    # =========================
    # Markers per model
    # =========================
    model_marker = {
        "LLaMA": "o",
        "Mistral": "^",
    }

    def marker_for(m):
        return model_marker.get(m, "o")

    # =========================
    # ICML-like style
    # =========================
    plt.rcParams.update({
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 7,
    })

    # =========================
    # Plot
    # =========================
    fig, ax = plt.subplots(1, 1, figsize=(args.fig_width_in, args.fig_height_in))

    # Scatter: color = watermark, marker = model
    for model in models:
        subm = df[df["model"] == model]
        for u in users:
            su = subm[subm["user_id"] == u]
            if su.empty:
                continue
            xs = [x_index[d] + offsets[u] for d in su["dataset"]]
            ys = su["z"].tolist()
            ax.scatter(
                xs, ys,
                s=14,
                c=user_color[u],
                marker=marker_for(model),
                linewidths=0.0,
            )

    # Threshold & grid
    ax.axhline(args.z_threshold, linestyle="--", linewidth=1.0)
    ax.grid(True, axis="y", linestyle=":", linewidth=0.8)

    ax.set_ylabel("z-score")
    ax.set_xlabel("Dataset")
    ax.set_xticks(range(len(datasets)))
    ax.set_xticklabels(datasets)

    # =========================
    # Legends
    # =========================

    # Watermark legend (colors)
    wm_handles = [
        Line2D([0], [0], marker='o', linestyle='',
               markerfacecolor=user_color[u],
               markeredgecolor=user_color[u],
               markersize=5,
               label=user_display[u])
        for u in users
    ]

    # Model legend (markers)
    model_handles = [
        Line2D([0], [0],
               marker=marker_for(m),
               linestyle='',
               color='black',
               markerfacecolor='black',
               markersize=5,
               label=m)
        for m in models
    ]

    # Threshold handle
    threshold_handle = Line2D(
        [0], [0],
        linestyle="--",
        color="black",
        linewidth=1.0,
        label="Threshold: z = -2"
    )
    model_handles.append(threshold_handle)

    # Upper legend: Watermark
    leg1 = ax.legend(
        handles=wm_handles,
        title="Watermark",
        loc="upper center",
        bbox_to_anchor=(0.5, 0.62),
        ncol=2,
        frameon=True,
    )
    ax.add_artist(leg1)

    # Lower legend: Model + threshold
    ax.legend(
        handles=model_handles,
        title="Model / Threshold",
        loc="upper center",
        bbox_to_anchor=(0.5, 0.32),
        ncol=2,
        frameon=True,
    )

    fig.tight_layout(pad=0.3)

    # =========================
    # Save
    # =========================
    out_dir = os.path.dirname(os.path.abspath(args.out_pdf))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    fig.savefig(args.out_pdf, bbox_inches="tight")
    print("Saved:", args.out_pdf)

    if args.out_png:
        out_dir = os.path.dirname(os.path.abspath(args.out_png))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        fig.savefig(args.out_png, dpi=args.dpi, bbox_inches="tight")
        print("Saved:", args.out_png)


if __name__ == "__main__":
    main()
