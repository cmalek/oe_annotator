"""Unit tests for sentence card selection with hyphenated words."""

import pytest
from unittest.mock import Mock, MagicMock

from oeapp.models.token import Token
from oeapp.models.sentence import Sentence
from oeapp.mixins import TokenOccurrenceMixin


class MockSentenceCard(TokenOccurrenceMixin):
    """Mock sentence card for testing selection logic."""

    def __init__(self, tokens, sentence_text):
        self.tokens = tokens
        self.sentence_text = sentence_text

    def _find_token_at_position(self, text: str, position: int) -> int | None:
        """
        Find the token index that contains the given character position.
        """
        if not self.tokens:
            return None

        # Build a mapping of token positions in the text
        token_positions: list[tuple[int, int, int]] = []  # (start, end, token_index)

        for token_idx, token in enumerate(self.tokens):
            surface = token.surface
            if not surface:
                continue

            token_start = self._find_token_occurrence(text, token, self.tokens)
            if token_start is None:
                continue

            token_end = token_start + len(surface)
            token_positions.append((token_start, token_end, token_idx))

        # Find which token contains the position
        for start, end, token_idx in token_positions:
            if start <= position < end:
                return token_idx

        return None


class TestSentenceCardSelection:
    """Test cases for sentence card selection with hyphenated words."""

    def test_select_hyphenated_word_by_prefix(self):
        """Test clicking prefix selects entire token."""
        # Create mock tokens
        token = Mock()
        token.surface = "ġe-wāt"
        token.order_index = 0
        tokens = [token]

        sentence_card = MockSentenceCard(tokens, "ġe-wāt")

        # Click on prefix part (position 0-2: "ġe")
        result = sentence_card._find_token_at_position("ġe-wāt", 1)
        assert result == 0

    def test_select_hyphenated_word_by_hyphen(self):
        """Test clicking hyphen selects entire token."""
        token = Mock()
        token.surface = "ġe-wāt"
        token.order_index = 0
        tokens = [token]

        sentence_card = MockSentenceCard(tokens, "ġe-wāt")

        # Click on hyphen (position 2)
        result = sentence_card._find_token_at_position("ġe-wāt", 2)
        assert result == 0

    def test_select_hyphenated_word_by_main_word(self):
        """Test clicking main word selects entire token."""
        token = Mock()
        token.surface = "ġe-wāt"
        token.order_index = 0
        tokens = [token]

        sentence_card = MockSentenceCard(tokens, "ġe-wāt")

        # Click on main word part (position 3-6: "wāt")
        result = sentence_card._find_token_at_position("ġe-wāt", 4)
        assert result == 0

    def test_highlight_hyphenated_token(self):
        """Test highlighting works for hyphenated tokens."""
        token = Mock()
        token.surface = "ġe-wāt"
        token.order_index = 0
        tokens = [token]

        sentence_card = MockSentenceCard(tokens, "Se ġe-wāt cyning")

        # Find token occurrence
        pos = sentence_card._find_token_occurrence("Se ġe-wāt cyning", token, tokens)
        assert pos == 3  # Position after "Se "

        # Verify clicking anywhere in hyphenated word selects it
        result = sentence_card._find_token_at_position("Se ġe-wāt cyning", 4)  # In "ġe"
        assert result == 0
        result = sentence_card._find_token_at_position("Se ġe-wāt cyning", 6)  # On hyphen
        assert result == 0
        result = sentence_card._find_token_at_position("Se ġe-wāt cyning", 8)  # In "wāt"
        assert result == 0

    def test_find_token_at_position_hyphenated(self):
        """Test _find_token_at_position with hyphenated words."""
        token1 = Mock()
        token1.surface = "Se"
        token1.order_index = 0

        token2 = Mock()
        token2.surface = "ġe-wāt"
        token2.order_index = 1

        token3 = Mock()
        token3.surface = "cyning"
        token3.order_index = 2

        tokens = [token1, token2, token3]
        sentence_card = MockSentenceCard(tokens, "Se ġe-wāt cyning")

        # Test clicking on each token
        assert sentence_card._find_token_at_position("Se ġe-wāt cyning", 0) == 0  # "Se"
        assert sentence_card._find_token_at_position("Se ġe-wāt cyning", 4) == 1  # "ġe" part
        assert sentence_card._find_token_at_position("Se ġe-wāt cyning", 6) == 1  # hyphen
        assert sentence_card._find_token_at_position("Se ġe-wāt cyning", 8) == 1  # "wāt" part
        assert sentence_card._find_token_at_position("Se ġe-wāt cyning", 10) == 2  # "cyning"

    def test_multiple_hyphenated_words_selection(self):
        """Test selection with multiple hyphenated words."""
        token1 = Mock()
        token1.surface = "ġe-wāt"
        token1.order_index = 0

        token2 = Mock()
        token2.surface = "be-bode"
        token2.order_index = 1

        tokens = [token1, token2]
        sentence_card = MockSentenceCard(tokens, "ġe-wāt be-bode")

        # Test clicking on first hyphenated word
        assert sentence_card._find_token_at_position("ġe-wāt be-bode", 1) == 0  # In "ġe"
        assert sentence_card._find_token_at_position("ġe-wāt be-bode", 5) == 0  # In "wāt"

        # Test clicking on second hyphenated word
        assert sentence_card._find_token_at_position("ġe-wāt be-bode", 8) == 1  # In "be"
        assert sentence_card._find_token_at_position("ġe-wāt be-bode", 13) == 1  # In "bode"
