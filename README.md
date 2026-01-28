# Invisible-Watermark

This is the **anonymous code repository** for the paper:

> **Text-preserving data provenance auditing of fine-tuned LLMs**

The repository contains all code and scripts used in the paper, including:
- the **main experimental pipeline**,
- the **baseline evaluation code**,
- robustness tests across **different data processing pipelines**,
- and robustness tests on **non-adversarial transformations** which include tokenizer test, different LLM APIs test, web interface test, pdf conversion test, etc.

The codebase is organized into four main components.

Repository structure:

Invisible-Watermark/
- src/            # Main experiments (our proposed method)
- baseline/       # Baseline (homoglyph) evaluation
- TestPipeline/   # Robustness under different data pipelines
- robustness/      # Robustness on non-adversarial transformations
- dataset/raw     # The raw dataset for experiments
