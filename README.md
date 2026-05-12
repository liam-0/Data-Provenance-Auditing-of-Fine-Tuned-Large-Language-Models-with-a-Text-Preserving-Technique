# Invisible-Watermark

This is the **code repository** for the paper:

> **Data Provenance Auditing of Fine-Tuned Large Language Models with a Text-Preserving Technique**

The repository contains all code and scripts used in the paper, including:
- the **main experimental pipeline**,
- the **baseline evaluation code**,
- robustness tests across **different data processing pipelines**,
- robustness tests on **non-adversarial transformations** (tokenizers, LLM APIs, web interfaces, PDF conversion, etc.).
- and robustness tests on **adversarial text transformations**.

## Entry points

Core watermarking method implementation:
- `src/watermark.py`

Training: `src/train_fast_full.py`  
Detection / evaluation: `src/probe_watermarks_batch_fast.py`

## Result analysis and plotting (our method)

Scripts in `src/result-analysis/` are used to generate the figures reported for our method:

- Experiment 4.2 (Figure 2): `src/result-analysis/plot_xp1.py`  
  

- Experiment 4.3 (Figure 2): `src/result-analysis/plot_xp2.py`  

- Experiment 4.4 (Figures 4 and 6): `src/result-analysis/plot_xp3.py`  

- Seed stability: `src/result-analysis/summary_seed_stability.py`  
  This script aggregates results across different random seeds and produces
  a CSV file for statistical analysis. The averaged values reported in
  **Table 1** and **Table 2** (and also each Figure) are computed using this script. Detailed results
  for each individual experiment can be found in the corresponding
  experiment-specific output files.
  

## Baseline (Experiment 4.6, Figures 5) analysis and plotting

Baseline experiments follow the same training and evaluation pipeline as our method,
with only the watermarking mechanism replaced.

In particular:

- `baseline/src/watermark.py`  
  Generates the baseline-style watermarked dataset using homoglyph perturbations.

- `baseline/src/score_unicode_properties.py`  
  Probes the baseline watermarked texts and computes detection scores.

Scripts in `baseline/src/result-analysis/` are used to generate baseline figures:

- Baseline plots (Experiment 4.6, Figures 5): `baseline/src/result-analysis/plot_unicode_properties.py`  

- Baseline summary: `baseline/src/result-analysis/summarize_unicode_properties_pa.py`  
  This script aggregates baseline results and produces CSV files for comparison.

## Robustness under different data pipelines (TestPipeline)

The `TestPipeline/` directory contains experiments evaluating the robustness of
our watermarking method under different real-world data processing pipelines.

Each notebook simulates a commonly used large-scale text cleaning or filtering
pipeline:

- `C4_cleaning_wrapper.ipynb` — C4-style data cleaning.
- `CCNet_cleaning.ipynb` — CCNet-based filtering and deduplication.
- `fineweb_cleaning.ipynb` — FineWeb-style preprocessing.
- `redpajama_cleaning.ipynb` — RedPajama-V2 data pipeline.
- `the_pile_cleaning.ipynb` — The Pile data preparation pipeline.

The files:
- `final_selective_replace.jsonl`
- `final_uniform_replace.jsonl`

contain watermarked texts processed by these pipelines and are used for
downstream robustness evaluation.

A detailed description of the experimental setup is provided in:
- `TestPipeline/Description and Technical Details of the Data Preparation Pipeline Experiments.pdf`

## Robustness on non-adversarial transformations (robustness, details in robustness/readme.md)

The `robustness/` directory evaluates the robustness of our watermarking method
under non-adversarial, real-world transformations that may occur during normal
text usage and dissemination.

These experiments include:

- `tokenizer/` — Robustness under different tokenizers.
- `TestsAPI/` — Robustness under different LLM APIs.
- `web/` — Robustness under web interfaces (copy/paste, HTML rendering).
- `toPdf/` — Robustness under PDF conversion.
- `CharSelection/` — Analysis of different invisible character selections.

The script:
- `robustness/comparChar.py`  
  Counts overlapping invisible characters across different character sets
  and outputs the results to `common_characters.csv`.

contains sample texts used for robustness testing.

## Robustness on non-adversarial transformations (details in robustness/readme.md)
Robustness analysis based on paper "MARKMYWORDS: Analyzing and Evaluating Language Model Watermarks" for both our methods and baseline.
Further details in robustness/readme.md.

## Repository structure

```
Invisible-Watermark/
├── src/                     # Main experiments (our proposed method)
│   ├── train_fast_full.py
│   ├── probe_watermarks_batch_fast.py
│   ├── watermark.py
│   ├── alphabet.txt
│   └── result-analysis/
│       ├── plot_xp1.py      # Figure 2
│       ├── plot_xp2.py      # Figure 3
│       ├── plot_xp3.py      # Figure 4 and Figure 6
│       ├── summary_seed_stability.py  # Aggregates multiple seeds into CSV
│       └── README.md
├── baseline/                # Baseline (homoglyph) evaluation
│   ├── src/                 # Baseline implementation
│   │   ├── train_fast_full.py
│   │   ├── score_unicode_properties.py
│   │   ├── watermark.py
│   │   ├── alphabet.txt
│   │   └── result-analysis/
│   │       ├── plot_unicode_properties.py   # Figure 5 (baseline plots)
│   │       ├── summarize_unicode_properties_pa.py  # Baseline summary (CSV)
│   │       └── README.md
│   ├── perturb_modified.py  # Modified perturbation script
│   └── README.md
├── TestPipeline/            # Robustness under different data pipelines
│   ├── C4_cleaning_wrapper.ipynb
│   ├── CCNet_cleaning.ipynb
│   ├── fineweb_cleaning.ipynb
│   ├── redpajama_cleaning.ipynb
│   ├── the_pile_cleaning.ipynb
│   ├── final_selective_replace.jsonl
│   ├── final_uniform_replace.jsonl
│   ├── myText.txt
│   ├── Description and Technical Details of the Data Preparation Pipeline Experiments.pdf
│   └── README.md
├── RobustnessTextTransformations/... # Robustness on text transformation (details in RobustnessTextTransformations/readme.md)
└── robustness/...              # Robustness on non-adversarial transformations (details in robustness/readme.md)
```

## Datasets

Datasets are available at:  
https://osf.io/rbdup/overview?view_only=5bd2e2c9180343009d1bf765fe3adef0
