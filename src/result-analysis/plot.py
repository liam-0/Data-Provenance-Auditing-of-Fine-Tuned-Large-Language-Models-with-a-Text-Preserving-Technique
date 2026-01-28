#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import glob
import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =========================
# Matplotlib style (paper-friendly)
# =========================
import matplotlib as mpl
mpl.rcParams["pdf.fonttype"] = 42  # TrueType in PDF
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

try:
    from scipy.stats import t as student_t
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False


# =========================
# Parsers
# =========================
def parse_T(config: str):
    """Extract T from config like: T1000_U1_P40 -> 1000"""
    m = re.search(r"(?:^|_)T(\d+)(?:_|$)", str(config))
    return int(m.group(1)) if m else np.nan


def normalize_model_name(model_raw: str) -> str:
    """Map raw model strings into {mistral, llama, gpt-oss}."""
    s = str(model_raw).lower()
    if "gpt-oss" in s:
        return "gpt-oss"
    if "mistral" in s:
        return "mistral"
    if "llama" in s:
        return "llama"
    return str(model_raw)


def normalize_dataset_name(ds_raw: str) -> str:
    """Map raw dataset strings into {blog1k, poems, cnn_dailymail}."""
    s = str(ds_raw).lower()
    if s in {"blog1k", "blog_1k", "blog"}:
        return "blog1k"
    if s in {"poems", "poetry"}:
        return "poems"
    if s in {"cnn_dailymail", "cnn", "cnn_news", "cnn-dailymail"}:
        return "cnn_dailymail"
    return str(ds_raw)


# =========================
# CI helper
# =========================
def tcrit_two_sided(conf_level: float, dof: int) -> float:
    """Two-sided t critical value: t_{1-alpha/2, dof}"""
    if dof <= 0:
        return np.nan
    alpha = 1.0 - conf_level
    if _HAVE_SCIPY:
        return float(student_t.ppf(1.0 - alpha / 2.0, dof))

    # Fallback normal approx
    if abs(alpha - 0.05) < 1e-12:
        return 1.96
    if abs(alpha - 0.10) < 1e-12:
        return 1.645
    if abs(alpha - 0.01) < 1e-12:
        return 2.576
    return 1.96


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--input_dir", default=".")
    ap.add_argument(
        "--pattern",
        default="GLOBAL_user_seed_second_match_summary_1_*.csv",
        help="Glob pattern for per-user CSV files.",
    )
    ap.add_argument("--out_dir", default="analysis_out")
    ap.add_argument("--min_users", type=int, default=2)
    ap.add_argument("--ci", type=float, default=0.95, help="e.g. 0.95 for 95%% CI.")

    # Single-column export settings
    ap.add_argument("--fig_width_in", type=float, default=3.25)
    ap.add_argument("--dpi", type=int, default=300)

    args = ap.parse_args()
    if not (0.0 < args.ci < 1.0):
        raise SystemExit("--ci must be in (0,1), e.g. 0.95")

    plot_dir = os.path.join(args.out_dir, "plots")
    os.makedirs(plot_dir, exist_ok=True)
    os.makedirs(args.out_dir, exist_ok=True)

    # ----- display names -----
    MODEL_DISPLAY = {
        "llama": "LLaMA",
        "mistral": "Mistral",
        "gpt-oss": "gpt-oss",
    }
    DATASET_DISPLAY = {
        "cnn_dailymail": "News",
        "blog1k": "Blog1k",
        "poems": "Poems",
    }

    # ---------- load data ----------
    paths = sorted(glob.glob(os.path.join(args.input_dir, args.pattern)))
    if not paths:
        raise SystemExit(f"No files found: {os.path.join(args.input_dir, args.pattern)}")

    frames = []
    for p in paths:
        df = pd.read_csv(p).copy()

        need = {
            "dataset",
            "model",
            "config",
            "user_id",
            "n_seeds",
            "mean_second_match",
            "var_second_match",
        }
        missing = need - set(df.columns)
        if missing:
            raise ValueError(f"[{p}] missing columns: {missing}")

        df["T"] = df["config"].apply(parse_T)
        df["mean_second_match"] = pd.to_numeric(df["mean_second_match"], errors="coerce")

        df["model"] = df["model"].apply(normalize_model_name)
        df["dataset"] = df["dataset"].apply(normalize_dataset_name)

        frames.append(df)

    df_all = pd.concat(frames, ignore_index=True)
    df_all = df_all.dropna(subset=["dataset", "model", "T", "user_id", "mean_second_match"])

    model_order = ["mistral", "llama", "gpt-oss"]
    dataset_order = ["blog1k", "poems", "cnn_dailymail"]

    df_all = df_all[df_all["model"].isin(model_order) & df_all["dataset"].isin(dataset_order)].copy()

    # ---------- aggregate across users at each (dataset, model, T) ----------
    g = df_all.groupby(["dataset", "model", "T"], dropna=False)

    def std_ddof1(a: np.ndarray) -> float:
        return float(np.std(a, ddof=1)) if len(a) >= 2 else 0.0

    agg = g.agg(
        n_users=("user_id", "count"),
        mean_ratio=("mean_second_match", "mean"),
        std_ratio=("mean_second_match", lambda s: std_ddof1(s.to_numpy())),
    ).reset_index()

    agg = agg[agg["n_users"] >= args.min_users].copy()

    # y-axis = rate
    agg["y"] = agg["mean_ratio"]

    # t-based CI on rate
    n = agg["n_users"].to_numpy()
    dof = n - 1
    tcrit = np.array([tcrit_two_sided(args.ci, int(d)) for d in dof], dtype=float)
    se = agg["std_ratio"].to_numpy() / np.sqrt(n)
    half = tcrit * se
    agg["ci_low"] = (agg["y"] - half).clip(lower=0.0)
    agg["ci_high"] = (agg["y"] + half).clip(upper=1.0)

    out_csv = os.path.join(args.out_dir, "agg_by_dataset_model_T_user_CI_rate.csv")
    agg.to_csv(out_csv, index=False)

    # ---------- plotting: single-column, 1x3 horizontal (independent x) ----------
    width = args.fig_width_in
    height = 2.2
    fig, axes = plt.subplots(
        1, len(dataset_order),
        figsize=(width, height),
        sharex=False,
        sharey=True,
    )

    if len(dataset_order) == 1:
        axes = [axes]

    color_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    model_colors = {
        "mistral": color_cycle[0 % len(color_cycle)],
        "llama":   color_cycle[1 % len(color_cycle)],
        "gpt-oss": color_cycle[2 % len(color_cycle)],
    }

    for ax, dataset in zip(axes, dataset_order):
        # dataset-specific T ticks
        Ts = sorted(agg.loc[agg["dataset"] == dataset, "T"].unique().tolist())
        if Ts:
            MAX_TICKS = {
                "blog1k": 4,
                "poems": 5,
                "cnn_dailymail": 5,
            }
            max_ticks = MAX_TICKS.get(dataset, 4)

            if len(Ts) <= max_ticks:
                show_Ts = Ts
            else:
                idx = np.linspace(0, len(Ts) - 1, max_ticks).astype(int)
                show_Ts = [Ts[i] for i in idx]

            ax.set_xticks(show_Ts)

            def fmt_k(t):
                return f"{t/1000:g}k" if t >= 1000 else str(int(t))

            ax.set_xticklabels([fmt_k(t) for t in show_Ts])

        for model in model_order:
            df_md = agg[(agg["model"] == model) & (agg["dataset"] == dataset)]
            if df_md.empty:
                continue

            df_md = df_md.sort_values("T")
            x = df_md["T"].to_numpy()
            y = df_md["y"].to_numpy()
            lo = df_md["ci_low"].to_numpy()
            hi = df_md["ci_high"].to_numpy()

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

        # Put legend on the last panel only
        if dataset == dataset_order[-1]:
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                ax.legend(
                    handles,
                    labels,
                    loc="lower right",
                    frameon=True,
                    fontsize=7.0,
                    handlelength=1.4,
                    borderpad=0.25,
                    labelspacing=0.2,
                    framealpha=0.85,
                    facecolor="white",
                )

        ax.set_title(DATASET_DISPLAY.get(dataset, dataset), pad=1.5)
        ax.grid(True, alpha=0.25)

    axes[0].set_ylabel("Regurgitation rate")

    fig.tight_layout(rect=[0, 0.13, 1, 0.88])

    tag = f"CI{int(args.ci*100)}"
    out_png = os.path.join(plot_dir, f"singlecol_1x3_indepx_{tag}_rate.png")
    out_pdf = os.path.join(plot_dir, f"singlecol_1x3_indepx_{tag}_rate.pdf")

    fig.supxlabel("Training set size", y=0.09)

    fig.savefig(out_png, dpi=args.dpi, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)

    print("Saved:")
    print(" -", out_png)
    print(" -", out_pdf)
    print(" -", out_csv)
    if not _HAVE_SCIPY:
        print("Note: scipy not found; used normal-approx critical values for CI.")


if __name__ == "__main__":
    main()
