"""Unit tests for sentence splitting functionality."""

import pytest

from oeapp.models.project import Project


class TestSplitSentences:
    """Test cases for split_sentences function."""

    def test_simple_sentence(self):
        """Test splitting a simple sentence."""
        result = Project.split_sentences("Se cyning wæs.")
        assert result == [("Se cyning wæs.", True)]

    def test_multiple_sentences(self):
        """Test splitting multiple sentences."""
        result = Project.split_sentences("Se cyning wæs. Hē wæs gōd.")
        assert result == [("Se cyning wæs.", True), ("Hē wæs gōd.", False)]

    def test_sentence_with_exclamation(self):
        """Test sentence ending with exclamation mark."""
        result = Project.split_sentences("Hwæt! Se cyning wæs.")
        assert result == [("Hwæt!", True), ("Se cyning wæs.", False)]

    def test_sentence_with_question_mark(self):
        """Test sentence ending with question mark."""
        result = Project.split_sentences("Hwæt sceal iċ singan? Se cyning wæs.")
        assert result == [("Hwæt sceal iċ singan?", True), ("Se cyning wæs.", False)]

    def test_quoted_text_with_final_punctuation(self):
        """Test quoted text with final punctuation inside quotes."""
        text = 'Þā cwæð hē: "Hwæt sceal iċ singan?"'
        result = Project.split_sentences(text)
        # Should keep ?" with the sentence, not split on the ?
        assert len(result) == 1
        assert result[0] == ('Þā cwæð hē: "Hwæt sceal iċ singan?"', True)

    def test_quoted_text_with_period(self):
        """Test quoted text with period inside quotes."""
        text = 'Hē cwæð: "Se cyning wæs gōd."'
        result = Project.split_sentences(text)
        # Should keep ." with the sentence
        assert len(result) == 1
        assert result[0] == ('Hē cwæð: "Se cyning wæs gōd."', True)

    def test_quoted_text_with_exclamation(self):
        """Test quoted text with exclamation inside quotes."""
        text = 'Hē cwæð: "Hwæt!"'
        result = Project.split_sentences(text)
        # Should keep !" with the sentence
        assert len(result) == 1
        assert result[0] == ('Hē cwæð: "Hwæt!"', True)

    def test_multiple_quotes(self):
        """Test text with multiple quoted sections."""
        text = 'Þā cwæð hē: "Hwæt sceal iċ singan?" And hē sang. "Se cyning wæs gōd."'
        result = Project.split_sentences(text)
        assert len(result) == 3
        assert result[0] == ('Þā cwæð hē: "Hwæt sceal iċ singan?"', True)
        assert result[1] == ("And hē sang.", False)
        assert result[2] == ('"Se cyning wæs gōd."', False)

    def test_nested_quotes(self):
        """Test nested quotes (single quotes inside double quotes)."""
        text = 'Hē cwæð: "Se cyning said \'Hwæt!\' and sang."'
        result = Project.split_sentences(text)
        # Should not split on ! inside the nested quotes
        assert len(result) == 1
        assert result[0] == ('Hē cwæð: "Se cyning said \'Hwæt!\' and sang."', True)

    def test_sentence_preserves_closing_punctuation(self):
        """Test that sentences always keep their closing punctuation."""
        result = Project.split_sentences("Se cyning wæs. Hē wæs gōd!")
        assert result == [("Se cyning wæs.", True), ("Hē wæs gōd!", False)]
        # Verify punctuation is preserved
        assert result[0][0].endswith(".")
        assert result[1][0].endswith("!")

    def test_empty_string(self):
        """Test splitting empty string."""
        result = Project.split_sentences("")
        assert result == []

    def test_whitespace_only(self):
        """Test splitting whitespace-only string."""
        result = Project.split_sentences("   ")
        assert result == []

    def test_sentence_with_brackets(self):
        """Test sentence with [number] markers."""
        result = Project.split_sentences("Se cyning[1] wæs. Hē[2] sang.")
        # [number] markers should be removed
        assert result == [("Se cyning wæs.", True), ("Hē sang.", False)]

    def test_complex_quoted_sentence(self):
        """Test complex sentence with quotes and punctuation."""
        text = 'Þā cwæð hē: "Hwæt sceal iċ singan?" And hē sang "Se cyning wæs gōd."'
        result = Project.split_sentences(text)
        assert len(result) == 2
        assert result[0] == ('Þā cwæð hē: "Hwæt sceal iċ singan?"', True)
        assert result[1] == ('And hē sang "Se cyning wæs gōd."', False)

    def test_quoted_text_followed_by_sentence(self):
        """Test quoted text followed by another sentence."""
        text = '"Hwæt sceal iċ singan?" Se cyning wæs gōd.'
        result = Project.split_sentences(text)
        assert len(result) == 2
        assert result[0] == ('"Hwæt sceal iċ singan?"', True)
        assert result[1] == ("Se cyning wæs gōd.", False)

    def test_single_quote_text(self):
        """Test text with single quotes."""
        text = "Hē cwæð: 'Hwæt sceal iċ singan?'"
        result = Project.split_sentences(text)
        assert len(result) == 1
        assert result[0] == ("Hē cwæð: 'Hwæt sceal iċ singan?'", True)

    def test_punctuation_without_space(self):
        """Test punctuation followed immediately by uppercase letter."""
        result = Project.split_sentences("Se cyning wæs.Hē sang.")
        assert len(result) == 2
        assert result[0] == ("Se cyning wæs.", True)
        assert result[1] == ("Hē sang.", False)

    def test_punctuation_with_space(self):
        """Test punctuation followed by space and uppercase letter."""
        result = Project.split_sentences("Se cyning wæs. Hē sang.")
        assert len(result) == 2
        assert result[0] == ("Se cyning wæs.", True)
        assert result[1] == ("Hē sang.", False)

    def test_lowercase_after_punctuation(self):
        """Test that lowercase after punctuation doesn't split."""
        result = Project.split_sentences("Se cyning wæs. etc. Hē sang.")
        # Should not split on . before etc (lowercase)
        assert len(result) == 2
        assert "etc." in result[0][0] or "etc." in result[1][0]

    def test_multiple_punctuation_marks(self):
        """Test multiple punctuation marks."""
        result = Project.split_sentences("Hwæt!! Se cyning wæs???")
        assert len(result) == 2
        assert result[0] == ("Hwæt!!", True)
        assert result[1] == ("Se cyning wæs???", False)

    def test_quoted_text_with_multiple_punctuation(self):
        """Test quoted text with multiple punctuation marks."""
        text = 'Hē cwæð: "Hwæt!!!"'
        result = Project.split_sentences(text)
        assert len(result) == 1
        assert result[0] == ('Hē cwæð: "Hwæt!!!"', True)

