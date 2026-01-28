# Invisible-Watermark

This is the **anonymous code repository** for the paper:

> **Data Provenance Auditing of Fine-Tuned Large Language Models with a Text-Preserving Technique**

The repository contains all code and scripts used in the paper, including:
- the **main experimental pipeline**,
- the **baseline evaluation code**,
- robustness tests across **different data processing pipelines**,
- and robustness tests on **non-adversarial transformations** (tokenizers, LLM APIs, web interfaces, PDF conversion, etc.).

## Entry points

Core watermarking method implementation:
- `src/watermark.py`

Training: `src/train_fast_full.py`  
Detection / evaluation: `src/probe_watermarks_batch_fast.py`

## Result analysis and plotting (our method)

Scripts in `src/result-analysis/` are used to generate the figures reported for our method:

- Experiment 1: `src/result-analysis/plot_xp1.py`  
  (Figure 2)

- Experiment 2: `src/result-analysis/plot_xp2.py`  
  (Figure 3)

- Experiment 3: `src/result-analysis/plot_xp3.py`  
  (Figures 4 and 6)

- Seed stability: `src/result-analysis/summary_seed_stability.py`  
  This script aggregates results across different random seeds and produces
  a CSV file for statistical analysis.

## Baseline analysis and plotting

Baseline experiments follow the same training and evaluation pipeline as our method,
with only the watermarking mechanism replaced.

In particular:

- `baseline/src/watermark.py`  
  Generates the baseline-style watermarked dataset using homoglyph perturbations.

- `baseline/src/score_unicode_properties.py`  
  Probes the baseline watermarked texts and computes detection scores.

Scripts in `baseline/src/result-analysis/` are used to generate baseline figures:

- Baseline plots: `baseline/src/result-analysis/plot_unicode_properties.py`  
  (Figure 5)

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

## Robustness on non-adversarial transformations (robustness)

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

### Character selection

The `robustness/CharSelection/` directory documents the selection process for
invisible Unicode characters used in the experiments.

Candidate characters are collected from Unicode categories **Cc** (Control) and
**Cf** (Format), and filtered by visual inspection across multiple environments
(terminal, text editor, CSV viewer).

The final character set used in all experiments is provided in:
- `robustness/CharSelection/alphabet.txt`

Main scripts:
- `getCharList.py` — Enumerates candidate characters from Cc and Cf.
- `embed.py` — Generates reference texts for invisibility testing.

### LLM API robustness

The `robustness/TestsAPI/` directory evaluates whether invisible watermarks are
preserved when texts are processed through different LLM APIs.

- `DeepSeek/` — Tests robustness under the DeepSeek API.
- `LeChatAPI/` — Tests robustness under the LeChat API.
- `chatGPTAPI/` — Tests robustness under the ChatGPT API.

For each API, experiments include:
- `*FromTxt` — Sending watermarked texts directly to the API.
- `*repetition` — Testing repeated API interactions.

### PDF conversion robustness

The `robustness/toPdf/` directory evaluates the preservation of invisible Unicode
characters under PDF generation and text extraction.

Experiments include:
- Direct PDF generation using Python.
- Text extraction using Python-based PDF parsers.
- Manual copy/paste from different PDF viewers.

Results show that preservation strongly depends on the font and PDF generation
method, with direct Python-based PDF generation providing the best overall
preservation.


### Tokenizer robustness

The `robustness/tokenizer/` directory analyzes how invisible Unicode characters
are tokenized by different tokenizers.

- `tokenize_all.py` — Runs tokenization for all tested tokenizers.
- `aggregate_tokenization.py` — Aggregates tokenization statistics into CSV files.
- `plot_*.py` — Generates figures comparing tokenization behaviors.
- `*.csv` / `*.png` — Aggregated results and visualization outputs.

### Web interface robustness

The `robustness/web/` directory evaluates whether invisible Unicode characters
are preserved under common web platforms through typical user actions
(copy/paste and HTML rendering).

- `gitCopyPaste/` — Tests copy/paste behavior from GitHub.
- `linkedinCopyPaste/` — Tests copy/paste behavior from LinkedIn.
- `redditCopyPaste/` — Tests copy/paste behavior from Reddit.
- `wikiCopyPaste/` — Tests copy/paste behavior from Wikipedia.
- `redditSrcCode/` — Inspects invisible characters in Reddit HTML source.
- `wikiSrcCode/` — Inspects invisible characters in Wikipedia HTML source.

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
└── robustness/              # Robustness on non-adversarial transformations
    ├── CharSelection/
    │   ├── alphabet.txt
    │   ├── embed.py
    │   ├── finalList.txt
    │   ├── getCharList.py
    │   ├── getCharList.txt
    │   ├── invisible_unicode_characters.csv
    │   └── readme.md
    ├── TestsAPI/
    │   ├── DeepSeek/
    │   │   ├── DSFromTxt
    │   │   ├── DSrepeat
    │   │   └── readme.md
    │   ├── LeChatAPI/
    │   │   ├── LeChatFromTxt
    │   │   ├── LeChatrepetition
    │   │   └── readme.md
    │   ├── chatGPTAPI/
    │   │   ├── ChatGPTfromTxt
    │   │   ├── ChatGPTrepetition
    │   │   └── readme.md
    │   └── README.md
    ├── toPdf/
    │   ├── create_pdf20.py
    │   ├── test_create_pdf.py
    │   ├── pdf2txt.py
    │   ├── pdf2txt/
    │   │   ├── CopyPasteAcrobat/
    │   │   ├── CopyPasteChrome/
    │   │   ├── CopyPasteEvince/
    │   │   ├── CopyPasteFirefox/
    │   │   ├── CopyPasteFirefoxWindows/
    │   │   ├── CopyPasteGmail/
    │   │   └── readme.md
    │   ├── char_all.pdf
    │   ├── char_all.txt
    │   ├── char_select.pdf
    │   ├── char_select.txt
    │   ├── char_select_lo.pdf
    │   ├── char_select_lo.txt
    │   └── readme.md
    ├── tokenizer/
    │   ├── Bert/
    │   │   ├── test_bert.py
    │   │   ├── bert_emoji.csv
    │   │   └── bert_invisible_char.csv
    │   ├── tokenize_all.py
    │   ├── aggregate_tokenization.py
    │   ├── plot_comparison.py
    │   ├── plot_per_tokenizer.py
    │   ├── plot_robust.py
    │   ├── plot_robust_tokenizer.py
    │   ├── aggregate_char.csv
    │   ├── aggregate_tokenizer.csv
    │   ├── invisible_char_token_counts_merged.csv
    │   ├── emoji_tokenization_analysis_merged.csv
    │   ├── emojisVsInvisTokens.png
    │   ├── tokenizers.png
    │   ├── robustTokenizers.png
    │   ├── env.example
    │   └── readme.md
    │
    ├── web/
    │   ├── gitCopyPaste/
    │   ├── linkedinCopyPaste/
    │   ├── redditCopyPaste/
    │   ├── redditSrcCode/
    │   ├── wikiCopyPaste/
    │   ├── wikiSrcCode/
    │   └── readme.md
    ├── comparChar.py        # Counts overlapping characters → common_characters.csv
    ├── myText.txt
    └── readme.md


```

## Datasets

Datasets are available at:  
https://osf.io/rbdup/overview?view_only=5bd2e2c9180343009d1bf765fe3adef0
