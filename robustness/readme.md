
Scripts, Utils & results for robustness to passive transformation evaluation.

# Takeaway

All control and format unicode char were tested for invisibility, 130 were selected for testing.

## PDF

### Creation and recovery through python
20 of them can be embedded in a pdf.
Those are recovered with a python script.

### Creation from txt doc, recovery through python

2 of them are preserved when converting from txt to pdf.

### PDF to Text

Trying to copy/paste characters from pdf viewer rather than through python script.
Highly depends on the viewer, up to 20 preserved

## Public APIs
ChatGPT regurgitates 32 of them when given as input or reading from a txt.
Le Chat regurgitates all 130 when given as input, repeat all of them defanged from a txt 
DeepSeek regurgitates all 130 when given as input or reading from a txt, 0 from pdf.


## Web

130 are preserved on git, wikipedia and linkedin. The code source may show them in html or defanged.


# Scripts

## comparChar.py

Load a text given in input, compare the common invisible characters between the given text and myText. Count them and provide the list in common_characters.csv

# Files 

## myText.txt 

Used for recognition/preservation tests. Contains the 130 tested characters, between "A" and "B".

## alphabet.txt

The alphabet used in Paper Section 4.

# Folders

## CharSelection

Scripts and output of all format/control unicode characters, list of final characters

## Test API
Contains tests with chatbot GUI

## toPdf

Test with pdf conversion and recovery

## Web

Test recovery on website

## tokenizer

Test tokenizers behavior

