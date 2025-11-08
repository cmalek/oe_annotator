"""Sentence and token splitter service."""

import re


def split_sentences(text: str) -> list[str]:
    """
    Split text into sentences.

    Args:
        text: Input Old English text

    Returns:
        List of sentence strings

    """
    # Simple regex-based sentence splitting
    # Split on periods, exclamation marks, question marks
    # Preserve punctuation with the sentence
    pattern = r"([.!?]+\s*)"
    sentences = re.split(pattern, text)
    # Combine sentences with their punctuation
    result = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            result.append(sentences[i] + sentences[i + 1])
        else:
            result.append(sentences[i])
    # Filter out empty strings
    return [s.strip() for s in result if s.strip()]


def tokenize(sentence: str) -> list[str]:
    """
    Tokenize a sentence into words.

    Args:
        sentence: Input sentence text

    Returns:
        List of token strings (words and punctuation)

    """
    # Split on whitespace, but preserve punctuation as separate tokens
    # This handles Old English characters like þ, ð, æ, etc.
    tokens = []
    # Use regex to split on whitespace while preserving punctuation
    words = re.split(r"\s+", sentence.strip())
    for word in words:
        if not word:
            continue
        # Split punctuation from words
        # Match word characters (including Old English chars) and punctuation separately
        parts = re.findall(r"[\wþðæȝġ]+|[.,;:!?\-—]+", word)
        tokens.extend(parts)
    return tokens
