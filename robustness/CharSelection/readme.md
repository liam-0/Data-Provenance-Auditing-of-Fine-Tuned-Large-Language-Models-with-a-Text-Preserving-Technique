Selection invisible characters for testing. All characters of the general categories Cc — Other, control and Cf — Other, format where tested.
Those that were invisible on the terminal, txt (gedit) and csv (libreoffice) were kept.

# Python scripts

## getCharList

Print all character from categories Cc and Cf with their code, name and width. Nota: width is not trustworthy.

## embed

Create the text "A" + all unicode characters appearing in finalList.txt +"B"


# Outputs

## getCharList.txt

Redirection of the output (terminal) of getCharList

## invisible_unicode_characters.csv

All the characters with their width, name and code printed as csv

# File finalList.txt

Created from getCharList.txt while removing every line where the inclusion of the character had a visible impact

# File alphabet.txt

Similar to finalList.txt from which bidi characters are further excluded:
U+061C  ARABIC LETTER MARK

U+2066 (LRI)

U+2068 (FSI)

U+2069 (PDI)

U+202A (LRE)

U+202C (PDF)

U+202D (LRO)

U+200E  LEFT-TO-RIGHT MARK 

U+200F  RIGHT-TO-LEFT MARK 

