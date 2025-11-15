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
    # Split on periods, exclamation marks, question marks, or numbers in [brackets]
    # Preserve punctuation with the sentence, but not the numbers in [brackets]
    pattern = r"([.!?]+\s*|\[\d+\]\s*)"
    sentences = re.split(pattern, text)
    # Combine sentences with their punctuation
    result = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            result.append(sentences[i] + sentences[i + 1])
        else:
            result.append(sentences[i])
    # Remove any [numbers] from the sentences
    result = [re.sub(r"\[\d+\]", "", s.strip()) for s in result]
    # If a sentence is just a number in [brackets], remove it
    result = [s for s in result if not re.match(r"^\[\d+\]$", s.strip())]
    # Filter out empty strings
    return [s.strip() for s in result if s.strip()]
