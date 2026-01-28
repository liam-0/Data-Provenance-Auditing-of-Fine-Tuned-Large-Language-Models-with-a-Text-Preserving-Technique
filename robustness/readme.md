# Robustness to Passive Transformations
Scripts, utilities, and experimental results.

This directory contains scripts, utilities, and results for evaluating the robustness of invisible Unicode characters under passive transformations, including document format conversion, public APIs, and web platforms.

## Key Takeaways

All Unicode format and control characters were systematically evaluated for invisibility.  
A total of 130 characters were selected for downstream experiments.

## PDF Experiments

### PDF creation and recovery via Python

Out of the 130 selected characters, 20 can be embedded into PDF files and subsequently recovered using a Python-based extraction script.

### PDF creation from plain text and recovery via Python

When converting from a plain text (.txt) document to PDF, 2 characters are preserved and can be recovered through Python-based extraction.

### PDF to text (copy–paste)

This experiment evaluates recovery via manual copy–paste from a PDF viewer rather than programmatic extraction.  
The preservation rate is highly dependent on the PDF viewer used, with up to 20 characters preserved in the best case.

## Public APIs

We evaluated character preservation when interacting with publicly available language model APIs:

- ChatGPT regurgitates 32 characters when provided as direct input or when reading from a text file.
- Le Chat regurgitates all 130 characters when provided as direct input, and preserves all of them when reading from a defanged text file.
- DeepSeek regurgitates all 130 characters when provided as direct input or when reading from a text file, but none when the source is a PDF.

## Web Platforms

All 130 characters are preserved on common web platforms, including GitHub, Wikipedia, and LinkedIn.  
Depending on the platform, the characters may appear either directly in the rendered HTML or in a defanged representation within the source code.

## Scripts

### comparChar.py

Loads an input text file and compares invisible Unicode characters against a reference text (myText.txt).  
The script counts overlapping characters and outputs the results to common_characters.csv.

## Files

### myText.txt

Reference text used for recognition and preservation experiments.  
Contains the 130 tested Unicode characters inserted between the characters “A” and “B”.

### alphabet.txt

Defines the Unicode alphabet used in Section 4 of the paper.

## Folders

### CharSelection

Scripts and outputs related to the enumeration of Unicode format and control characters, including the final selected character set.

### Test_API

Experiments conducted using chatbot graphical user interfaces.

### toPdf

Experiments involving PDF generation and character recovery.

### Web

Experiments evaluating character preservation on web platforms.

### tokenizer

Experiments analyzing tokenizer behavior with invisible Unicode characters.
