#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Single-column main figure + appendix figures.

Main figure:
- 1×3 subplots for datasets
- Models encoded by color
- X axis: number of unique watermarks (U), equally spaced globally
- Y axis: mean across users' mean_second_match
- Shading: confidence intervals across users (t-based), per (dataset, model, U)

Appendix figures:
- One figure per (dataset, model)
- No CI, no user-averaging: plot user curves directly
- User is encoded by distinct styling (color + linestyle/marker)

Input CSV columns:
dataset, model, config, user_id, mean_second_match (n_seeds optional)

Example:
python plot_xp3.py \
  --input_csv GLOBAL_user_probeSeedInJson_chunkLevel_second_match_summary.csv \
  --T 5000 --P 40 \
  --out_dir analysis_out
"""

import argparse
import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib as mpl

try:
    from scipy.stats import t as student_t
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False

# =========================
# Single-column friendly style
# =========================
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42
mpl.rcParams.update({
    "font.size": 8.0,
    "axes.labelsize": 8.0,
    "axes.titlesize": 8.5,
    "legend.fontsize": 7.5,
    "legend.title_fontsize": 7.5,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "lines.linewidth": 1.2,
    "lines.markersize": 3.2,
})

# -------------------------
# Parsers: T/U/P from config like T5000_U50_P40
# -------------------------
def parse_T(config: str):
    m = re.search(r"(?:^|_)T(\d+)(?:_|$)", str(config))
    return int(m.group(1)) if m else np.nan

def parse_U(config: str):
    m = re.search(r"(?:^|_)U(\d+)(?:_|$)", str(config))
    return int(m.group(1)) if m else np.nan

def parse_P(config: str):
    m = re.search(r"(?:^|_)P(\d+)(?:_|$)", str(config))
    return int(m.group(1)) if m else np.nan

def normalize_model_name(model_raw: str) -> str:
    s = str(model_raw).lower()
    if "mistral" in s:
        return "mistral"
    if "llama" in s:
        return "llama"
    if "gpt-oss" in s:
        return "gpt-oss"
    return str(model_raw)

def normalize_dataset_name(ds_raw: str) -> str:
    s = str(ds_raw).lower()
    if s in {"blog1k", "blog_1k", "blog"}:
        return "blog1k"
    if s in {"poems", "poetry"}:
        return "poems"
    if s in {"cnn_dailymail", "cnn", "cnn_news", "cnn-dailymail"}:
        return "cnn_dailymail"
    return str(ds_raw)

def tcrit_two_sided(conf_level: float, dof: int) -> float:
    if dof <= 0:
        return np.nan
    alpha = 1.0 - conf_level
    if _HAVE_SCIPY:
        return float(student_t.ppf(1.0 - alpha / 2.0, dof))
    # fallback normal approx
    if abs(alpha - 0.05) < 1e-12:
        return 1.96
    if abs(alpha - 0.10) < 1e-12:
        return 1.645
    if abs(alpha - 0.01) < 1e-12:
        return 2.576
    return 1.96

def std_ddof1(a: np.ndarray) -> float:
    return float(np.std(a, ddof=1)) if len(a) >= 2 else np.nan

def compute_agg_with_ci(df: pd.DataFrame, ci: float, min_users: int) -> pd.DataFrame:
    """Main fig aggregation across users + CI."""
    agg = (
        df.groupby(["dataset", "model", "U"], as_index=False)
          .agg(
              n_users=("user_id", "nunique"),
              mean_y=("mean_second_match", "mean"),
              std_y=("mean_second_match", lambda s: std_ddof1(s.to_numpy())),
          )
    )

    n = agg["n_users"].to_numpy(dtype=float)
    dof = (n - 1).astype(int)
    tcrit = np.array([tcrit_two_sided(ci, int(d)) for d in dof], dtype=float)
    se = agg["std_y"].to_numpy(dtype=float) / np.sqrt(n)
    half = tcrit * se
    half = np.where(agg["n_users"].to_numpy() >= min_users, half, 0.0)

    agg["ci_low"] = np.clip(agg["mean_y"].to_numpy() - half, 0.0, 1.0)
    agg["ci_high"] = np.clip(agg["mean_y"].to_numpy() + half, 0.0, 1.0)
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input_csv", required=True)
    ap.add_argument("--out_dir", default="analysis_out")
    ap.add_argument("--dpi", type=int, default=300)

    # main (single-col 1x3)
    ap.add_argument("--fig_width_in", type=float, default=3.25)
    ap.add_argument("--fig_height_in", type=float, default=2.2)

    # appendix (single panel)
    ap.add_argument("--app_width_in", type=float, default=3.25)
    ap.add_argument("--app_height_in", type=float, default=2.1)

    ap.add_argument("--T", type=int, default=None)
    ap.add_argument("--P", type=int, default=None)
    ap.add_argument("--datasets", default="blog1k,poems,cnn_dailymail")
    ap.add_argument("--models", default="mistral,llama")

    ap.add_argument("--ci", type=float, default=0.95)
    ap.add_argument("--min_users", type=int, default=2)
    ap.add_argument("--users", default="user_0001,user_0002,user_0003,user_0004,user_0005")

    args = ap.parse_args()
    if not (0.0 < args.ci < 1.0):
        raise SystemExit("--ci must be in (0,1)")

    os.makedirs(args.out_dir, exist_ok=True)
    plot_dir = os.path.join(args.out_dir, "plots")
    os.makedirs(plot_dir, exist_ok=True)

    MODEL_DISPLAY = {"llama": "LLaMA", "mistral": "Mistral"}
    DATASET_DISPLAY = {"cnn_dailymail": "News", "blog1k": "Blog1k", "poems": "Poems"}

    dataset_order = [x.strip() for x in args.datasets.split(",") if x.strip()]
    model_order = [x.strip() for x in args.models.split(",") if x.strip()]
    users_keep = [x.strip() for x in args.users.split(",") if x.strip()]

    # ---- user styles for appendix ----
    user_styles = {
        "user_0001": ("-",  "o"),
        "user_0002": ("--", "s"),
        "user_0003": (":",  "^"),
        "user_0004": ("-.", "D"),
        "user_0005": ("-",  "v"),
    }

    # ---- user display names ----
    USER_DISPLAY = {
        "user_0001": "Watermark 1",
        "user_0002": "Watermark 2",
        "user_0003": "Watermark 3",
        "user_0004": "Watermark 4",
        "user_0005": "Watermark 5",
    }

    # ---- user colors for appendix ----
    user_color_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    user_colors = {
        u: user_color_cycle[i % len(user_color_cycle)]
        for i, u in enumerate(users_keep)
    }

    df = pd.read_csv(args.input_csv).copy()
    need = {"dataset", "model", "config", "user_id", "mean_second_match"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {args.input_csv}: {missing}")

    df["dataset"] = df["dataset"].apply(normalize_dataset_name)
    df["model"] = df["model"].apply(normalize_model_name)
    df["T"] = df["config"].apply(parse_T)
    df["U"] = df["config"].apply(parse_U)
    df["P"] = df["config"].apply(parse_P)
    df["mean_second_match"] = pd.to_numeric(df["mean_second_match"], errors="coerce")

    df = df.dropna(subset=["dataset", "model", "T", "U", "P", "user_id", "mean_second_match"])
    df = df[df["dataset"].isin(dataset_order) & df["model"].isin(model_order)].copy()
    df = df[df["user_id"].isin(users_keep)].copy()

    # auto-pick T/P if unique
    if args.T is None:
        Ts = sorted(df["T"].dropna().unique().tolist())
        if len(Ts) == 1:
            args.T = int(Ts[0])
    if args.P is None:
        Ps = sorted(df["P"].dropna().unique().tolist())
        if len(Ps) == 1:
            args.P = int(Ps[0])

    if args.T is not None:
        df = df[df["T"] == args.T].copy()
    if args.P is not None:
        df = df[df["P"] == args.P].copy()

    if df.empty:
        raise SystemExit("No data left after filtering. Check --T/--P/--models/--datasets/--users.")

    # ---- GLOBAL U positions (shared) ----
    U_vals = sorted(df["U"].dropna().astype(int).unique().tolist())
    U_to_pos = {u: i for i, u in enumerate(U_vals)}
    x_ticks = [U_to_pos[u] for u in U_vals]
    x_ticklabels = [str(u) for u in U_vals]

    # ---- model colors for MAIN figure only ----
    color_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    model_colors = {m: color_cycle[i % len(color_cycle)] for i, m in enumerate(model_order)}

    # ======================
    # MAIN FIGURE (mean + CI)
    # ======================
    agg = compute_agg_with_ci(df, ci=args.ci, min_users=args.min_users)

    fig, axes = plt.subplots(
        1, len(dataset_order),
        figsize=(args.fig_width_in, args.fig_height_in),
        sharex=False,
        sharey=True,
    )
    if len(dataset_order) == 1:
        axes = [axes]

    for ax, dataset in zip(axes, dataset_order):
        d_ds = agg[agg["dataset"] == dataset].copy()

        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_ticklabels)

        if d_ds.empty:
            ax.set_title(DATASET_DISPLAY.get(dataset, dataset), pad=1.5)
            ax.grid(True, alpha=0.25)
            ax.set_ylim(0.0, 1.0)
            continue

        for model in model_order:
            d_m = d_ds[d_ds["model"] == model].copy()
            if d_m.empty:
                continue
            d_m = d_m.sort_values("U")

            x = np.array([U_to_pos[int(u)] for u in d_m["U"].astype(int).tolist()], dtype=float)
            y = d_m["mean_y"].to_numpy()
            lo = d_m["ci_low"].to_numpy()
            hi = d_m["ci_high"].to_numpy()

            ax.plot(
                x, y,
                marker="o",
                linewidth=1.1,
                markersize=3.0,
                color=model_colors[model],
                label=MODEL_DISPLAY.get(model, model),
            )
            ax.fill_between(
                x, lo, hi,
                color=model_colors[model],
                alpha=0.18,
                linewidth=0,
            )

        ax.set_title(DATASET_DISPLAY.get(dataset, dataset), pad=1.5)
        ax.grid(True, alpha=0.25)
        ax.set_ylim(0.0, 1.0)

    axes[0].set_ylabel("Regurgitation rate")
    fig.supxlabel("Number of unique watermarks", y=0.2)

    model_handles = [
        Line2D([0],[0], color=model_colors[m], lw=1.2, marker="o",
               label=MODEL_DISPLAY.get(m, m))
        for m in model_order
    ]
    axes[-1].legend(
        handles=model_handles,
        title="Model",
        loc="lower right",
        frameon=True,
        fontsize=7.0,
        handlelength=1.4,
        borderpad=0.25,
        labelspacing=0.2,
        framealpha=0.85,
        facecolor="white",
    )

    fig.tight_layout(rect=[0, 0.13, 1, 0.92])

    T_show = args.T if args.T is not None else "T?"
    P_show = args.P if args.P is not None else "P?"
    tag = f"T{T_show}_P{P_show}_usersMean_CI{int(args.ci*100)}_singlecol"

    out_png = os.path.join(plot_dir, f"main_1x3_usersMean_withCI_{tag}.png")
    out_pdf = os.path.join(plot_dir, f"main_1x3_usersMean_withCI_{tag}.pdf")

    fig.savefig(out_png, dpi=args.dpi, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)

    print("Saved main:")
    print(" -", out_png)
    print(" -", out_pdf)

    # ======================
    # APPENDIX FIGURES (per user, no CI)
    # ======================
    app_dir = os.path.join(plot_dir, "appendix")
    os.makedirs(app_dir, exist_ok=True)

    for dataset in dataset_order:
        for model in model_order:
            d0 = df[(df["dataset"] == dataset) & (df["model"] == model)].copy()
            if d0.empty:
                continue

            fig = plt.figure(figsize=(args.app_width_in, args.app_height_in))
            ax = plt.gca()

            ax.set_xticks(x_ticks)
            ax.set_xticklabels(x_ticklabels)

            for user in users_keep:
                du = d0[d0["user_id"] == user].copy()
                if du.empty:
                    continue

                du = (
                    du.groupby("U", as_index=False)
                      .agg(y=("mean_second_match", "mean"))
                      .sort_values("U")
                )

                x = np.array([U_to_pos[int(u)] for u in du["U"].astype(int).tolist()], dtype=float)
                y = du["y"].to_numpy()

                ls, mk = user_styles.get(user, ("-", "o"))
                ax.plot(
                    x, y,
                    linestyle=ls,
                    marker=mk,
                    markersize=3.0,
                    linewidth=1.0,
                    color=user_colors.get(user, "black"),
                    alpha=0.95,
                )

            title = f"{DATASET_DISPLAY.get(dataset, dataset)} / {MODEL_DISPLAY.get(model, model)}"
            ax.set_title(title, pad=1.5)
            ax.set_ylabel("Regurgitation rate")
            ax.set_xlabel("Number of different watermarks")
            ax.grid(True, alpha=0.25)
            ax.set_ylim(0.0, 1.0)

            user_handles = []
            for u in users_keep:
                ls, mk = user_styles.get(u, ("-", "o"))
                user_handles.append(
                    Line2D([0],[0],
                           color=user_colors.get(u, "black"),
                           lw=1.0,
                           linestyle=ls,
                           marker=mk,
                           label=USER_DISPLAY.get(u, u))
                )
            ax.legend(
                handles=user_handles,
                title="User",
                loc="lower right",
                frameon=True,
                fontsize=7.0,
                handlelength=1.4,
                borderpad=0.25,
                labelspacing=0.2,
                framealpha=0.85,
                facecolor="white",
            )

            fig.tight_layout()

            tag2 = f"T{T_show}_P{P_show}_usersRaw_singlecol"
            out_png2 = os.path.join(app_dir, f"appendix_{dataset}_{model}_{tag2}.png")
            out_pdf2 = os.path.join(app_dir, f"appendix_{dataset}_{model}_{tag2}.pdf")

            fig.savefig(out_png2, dpi=args.dpi, bbox_inches="tight")
            fig.savefig(out_pdf2, bbox_inches="tight")
            plt.close(fig)

            print("Saved appendix:", os.path.basename(out_pdf2))

    if not _HAVE_SCIPY:
        print("Note: scipy not found; used normal-approx critical values for CI in main figure.")


if __name__ == "__main__":
    main()
