Scripts and outputs for tokenizer tests

# Scripts

## tokenize all

Test all tokenizers on invisible characters and emojis.
Outputs emoji_tokenization_analysis and invisible_char_token_counts

## aggregate tokenization

Aggregate the results obtained from tokenize all:
- aggregate char: histogram per char
- aggregate tokenizer: histogram per tokenizer

## plot*

Plot a comparison of emojis and invible characters, the histogram per tokenizers, or an analysis for the most robust characters


# Files

## emoji_tokenization_analysis and invisible_char_token_counts

Outputs of tokenize all, number of token per tokenizer and character (invisible or emoji).
Count both the tokens created from tokenizing the character and the increase in token number when inserting in between two normalized characters.


