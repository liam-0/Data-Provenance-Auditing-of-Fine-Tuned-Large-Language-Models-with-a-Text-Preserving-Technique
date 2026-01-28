Test with pdf conversion, extraction of characters is done through python extraction.

Takeaway: export/print preservation depends on font. 2 or 4 preservation with the 2 tested.

Edition is a failure, except with draw where "\uFE00\uFE0F\u034F" are preserved.

Generating the pdf directly is pretty good, only     "\u061C\u2066\u2069" is lost

## Txt files

invisible_text.txt, the one generated previously
invisible_text_font.odt, same but in Deja Vu Sans

## Python scripts

### extract_inv
Extract text from pdf, test for invisible characters (name are hardcoded)

### test_pdf
Create the invisible text in txt and as pdf

### test_creat_pdf
Create pdf with a "good" font

## PDF files

### Invisible text 

Created from python directly (test_pdf) with helvetica
Only U+200C and U+200D are preserved

### Invisible chars
Created from python (test_create_pdf) with another font
- 13 : all characters, preserve all but "\u061C\u2066\u2069"  that appear in pdf furthermore
- 10 : without "\u061C\u2066\u2069", preserve all, fully invisible



## invisible LO-Export.pdf

Created by exporting Invisible Text to pdf using libreoffice.
Only U+200C and U+200D are preserved

## invisible_text_font_exportLO

Created by exporting Invisible text font to pdf using libreoffice

## invisible LO-print.pdf

Created by printing invisible text in a document using libreoffice.
Only U+200C and U+200D are preserved

## invisible text edited inkscape/LO draw

invisible text pdf edited with inkscape and LO draw

## pdf2txt

Contains output from copy/paste of invisible char 10 from various pdf viewer


