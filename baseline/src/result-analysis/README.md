# Baseline Visualization (Unicode Properties)

This folder contains scripts used to **summarize and visualize the baseline
experiments** based on the outputs of a unicode-properties scorer.

The baseline analysis does **not** involve any learned watermark
detector. Instead, it relies purely on token-level loss statistics.

------------------------------------------------------------------------

## Overview

Upstream scoring produces one or more files of the form:

    *_scores.csv

Each file corresponds to one experimental setting and contains:

-   **Row 0:** an integer `k` (possibly quoted), indicating how many
    documents belong to the *watermarked* group.
-   **Rows 1..:** one document per row, represented as a variable-length
    list of per-token loss values.

Two scripts are provided:

1.  `summarize_unicode_properties.py` --- statistical summarization.
2.  `plot_unicode_properties.py` --- visualization of z-scores across
    datasets, models, and watermarks **(fig.5 in the paper)**.

------------------------------------------------------------------------

## 1. summarize_unicode_properties.py

### Purpose

For each `*_scores.csv` file, this script computes:

-   **Document statistic:** mean token loss per document (optionally
    restricted to last `N` tokens).
-   **Groups:**
    -   `W`: first `k` documents (watermarked)
    -   `N`: remaining documents (null)
-   **Descriptive z-score:**

```{=html}
<!-- -->
```
    z = (mean_w - mean_null) / std_null

-   **Empirical one-sided p-value:**
    -   If `direction=lower`: `p = mean(null_losses <= mean_w)`
    -   If `direction=higher`: `p = mean(null_losses >= mean_w)`

No trimming, no two-sided tests, and no thresholds are applied.

### Input

Directory containing:

    *_scores.csv

### Output

A single CSV file (default: `paper_summary.csv`) with columns:

-   `file`
-   `k`
-   `n_total`
-   `n_null`
-   `last_n`
-   `direction`
-   `mean_w`
-   `mean_null`
-   `std_null`
-   `z_score`
-   `empirical_p_value`

### Usage

``` bash
python summarize_unicode_properties.py   --input_dir ./scores   --output_csv paper_summary.csv   --last_n 0   --direction lower
```

------------------------------------------------------------------------

## 2. plot_unicode_properties.py

**(fig.5)**

### Purpose

Visualizes the summarized baseline results by plotting **z-scores**:

-   x-axis: dataset
-   y-axis: z-score
-   color: watermark identity
-   marker: model identity

A horizontal threshold line (default `z = -2`) is shown for reference.

### Input

One or more CSV files produced by the previous script, matching:

    paper_summary_<dataset>_<model>.csv

Each file must contain at least:

-   `file`
-   `z_score`

User IDs are extracted from filenames using pattern:

    user_0001, user_0002, ...

### Output

A single scatter plot:

-   PDF (required)
-   PNG (optional)

### Usage

``` bash
python plot_unicode_properties.py   --input_glob "./paper_summary_*.csv"   --out_pdf fig_unicode_properties.pdf   --out_png fig_unicode_properties.png   --z_threshold -2.0
```

### Key options

  Argument            Meaning                      Default
  ------------------- ---------------------------- ------------------------------
  `--input_glob`      Glob for summary CSV files   (required)
  `--out_pdf`         Output PDF path              `fig_unicode_properties.pdf`
  `--out_png`         Output PNG path              None
  `--z_threshold`     Horizontal reference line    `-2.0`
  `--fig_width_in`    Figure width (inches)        `3.25`
  `--fig_height_in`   Figure height (inches)       `2.6`
  `--dpi`             PNG resolution               `300`

------------------------------------------------------------------------

## Typical workflow

``` bash
# Step 1: run unicode-properties scorer (outside this folder)

# Step 2: summarize
python summarize_unicode_properties.py --input_dir ./scores

# Step 3: visualize
python plot_unicode_properties.py --input_glob "./paper_summary_*.csv"
```

------------------------------------------------------------------------

## Requirements

-   Python ≥ 3.8
-   numpy
-   pandas
-   matplotlib
