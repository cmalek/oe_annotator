"""Unit tests for mixin classes."""

import pytest

from oeapp.mixins import AnnotationTextualMixin, TokenOccurrenceMixin
from oeapp.models.annotation import Annotation
from oeapp.models.token import Token
from tests.conftest import create_test_project, create_test_sentence


class TestTokenOccurrenceMixin:
    """Test cases for TokenOccurrenceMixin."""

    def test_find_token_occurrence_simple(self, db_session):
        """Test finding token occurrence in simple text."""
        mixin = TokenOccurrenceMixin()
        text = "Se cyning"
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, text)
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]  # "Se"
        result = mixin._find_token_occurrence(text, token, tokens)
        assert result == 0

    def test_find_token_occurrence_multiple_occurrences(self, db_session):
        """Test finding correct occurrence when token appears multiple times."""
        mixin = TokenOccurrenceMixin()
        text = "cyning cyning cyning"
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, text)
        tokens = Token.list(db_session, sentence.id)
        # Find "cyning" tokens - should have 3
        cyning_tokens = [t for t in tokens if t.surface == "cyning"]
        assert len(cyning_tokens) >= 2, f"Expected at least 2 'cyning' tokens, got {len(cyning_tokens)}"
        token1 = cyning_tokens[0]  # First "cyning"
        token2 = cyning_tokens[1]  # Second "cyning"
        # Should find first occurrence
        result1 = mixin._find_token_occurrence(text, token1, tokens)
        assert result1 == 0
        # Should find second occurrence (after first "cyning ")
        result2 = mixin._find_token_occurrence(text, token2, tokens)
        assert result2 > 0  # After first "cyning "

    def test_find_token_occurrence_not_found(self, db_session):
        """Test returns None when token not found in text."""
        mixin = TokenOccurrenceMixin()
        text = "Se cyning"
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, text)
        tokens = Token.list(db_session, sentence.id)
        # Create a token that doesn't exist in text
        fake_token = Token(surface="missing", order_index=999)
        result = mixin._find_token_occurrence(text, fake_token, tokens)
        assert result is None

    def test_find_token_occurrence_empty_text(self, db_session):
        """Test handles empty text."""
        mixin = TokenOccurrenceMixin()
        text = ""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, text)
        tokens = Token.list(db_session, sentence.id)
        if tokens:
            token = tokens[0]
            result = mixin._find_token_occurrence(text, token, tokens)
            assert result is None

    def test_find_token_occurrence_empty_surface(self, db_session):
        """Test handles empty surface."""
        mixin = TokenOccurrenceMixin()
        text = "Se cyning"
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, text)
        tokens = Token.list(db_session, sentence.id)
        # Create token with empty surface
        # Note: Python's str.find("") returns 0 (empty string found at start)
        # So the method will return 0, not None. This is technically correct
        # but not very useful. The test accepts this behavior.
        empty_token = Token(surface="", order_index=999)
        result = mixin._find_token_occurrence(text, empty_token, tokens)
        # Empty string.find("") returns 0, so result will be 0
        assert result == 0


class TestAnnotationTextualMixin:
    """Test cases for AnnotationTextualMixin."""

    def test_format_pos_noun(self, db_session):
        """Test format_pos for noun."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "N"
        annotation.declension = "s"
        db_session.commit()
        result = mixin.format_pos(annotation)
        assert result == "n:strong"

    def test_format_pos_noun_no_declension(self, db_session):
        """Test format_pos for noun without declension."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "N"
        annotation.declension = None
        db_session.commit()
        result = mixin.format_pos(annotation)
        assert result == "n"

    def test_format_pos_verb(self, db_session):
        """Test format_pos for verb."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning wæs")
        tokens = Token.list(db_session, sentence.id)
        verb_token = [t for t in tokens if t.surface == "wæs"][0]
        annotation = Annotation.get(db_session, verb_token.id)
        annotation.pos = "V"
        annotation.verb_class = "w1"
        db_session.commit()
        result = mixin.format_pos(annotation)
        assert result == "v:weak1"

    def test_format_pos_verb_no_class(self, db_session):
        """Test format_pos for verb without class."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning wæs")
        tokens = Token.list(db_session, sentence.id)
        verb_token = [t for t in tokens if t.surface == "wæs"][0]
        annotation = Annotation.get(db_session, verb_token.id)
        annotation.pos = "V"
        annotation.verb_class = None
        db_session.commit()
        result = mixin.format_pos(annotation)
        assert result == "v"

    def test_format_pos_adjective(self, db_session):
        """Test format_pos for adjective."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "A"
        annotation.adjective_inflection = "s"
        annotation.adjective_degree = "p"
        db_session.commit()
        result = mixin.format_pos(annotation)
        assert result == "adj:strong:pos"

    def test_format_pos_pronoun(self, db_session):
        """Test format_pos for pronoun."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "R"
        annotation.pronoun_type = "p"
        db_session.commit()
        result = mixin.format_pos(annotation)
        assert result == "pron:pers"

    def test_format_pos_article(self, db_session):
        """Test format_pos for article/determiner."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "D"
        annotation.article_type = "d"
        db_session.commit()
        result = mixin.format_pos(annotation)
        assert result == "det:def"

    def test_format_pos_adverb(self, db_session):
        """Test format_pos for adverb."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "B"
        annotation.adverb_degree = "p"
        db_session.commit()
        result = mixin.format_pos(annotation)
        assert result == "adv:pos"

    def test_format_pos_conjunction(self, db_session):
        """Test format_pos for conjunction."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "C"
        annotation.conjunction_type = "c"
        db_session.commit()
        result = mixin.format_pos(annotation)
        assert result == "conj:coord"

    def test_format_pos_preposition(self, db_session):
        """Test format_pos for preposition."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "E"
        db_session.commit()
        result = mixin.format_pos(annotation)
        assert result == "prep"

    def test_format_pos_interjection(self, db_session):
        """Test format_pos for interjection."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "I"
        db_session.commit()
        result = mixin.format_pos(annotation)
        assert result == "int"

    def test_format_pos_none(self, db_session):
        """Test format_pos returns empty string when pos is None."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = None
        db_session.commit()
        result = mixin.format_pos(annotation)
        assert result == ""

    def test_format_gender_noun(self, db_session):
        """Test format_gender for noun."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "N"
        annotation.gender = "m"
        db_session.commit()
        result = mixin.format_gender(annotation)
        assert result == "m"

    def test_format_gender_no_gender(self, db_session):
        """Test format_gender returns empty when no gender."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "N"
        annotation.gender = None
        db_session.commit()
        result = mixin.format_gender(annotation)
        assert result == ""

    def test_format_gender_wrong_pos(self, db_session):
        """Test format_gender returns empty for POS that doesn't have gender."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "B"  # Adverb
        annotation.gender = "m"
        db_session.commit()
        result = mixin.format_gender(annotation)
        assert result == ""

    def test_format_context_noun(self, db_session):
        """Test format_context for noun."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "N"
        annotation.case = "n"
        annotation.number = "s"
        db_session.commit()
        result = mixin.format_context(annotation)
        assert result == "nom1"

    def test_format_context_verb(self, db_session):
        """Test format_context for verb."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning wæs")
        tokens = Token.list(db_session, sentence.id)
        verb_token = [t for t in tokens if t.surface == "wæs"][0]
        annotation = Annotation.get(db_session, verb_token.id)
        annotation.pos = "V"
        annotation.verb_tense = "p"
        annotation.verb_mood = "i"
        annotation.verb_person = "3"
        annotation.number = "s"
        db_session.commit()
        result = mixin.format_context(annotation)
        # Format is: tense:mood:person:number = "pai3s"
        assert result == "pai3s"

    def test_format_context_preposition(self, db_session):
        """Test format_context for preposition."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = "E"
        annotation.prep_case = "d"
        db_session.commit()
        result = mixin.format_context(annotation)
        assert result == "dat"

    def test_format_context_none_pos(self, db_session):
        """Test format_context returns empty when pos is None."""
        mixin = AnnotationTextualMixin()
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        annotation = Annotation.get(db_session, token.id)
        annotation.pos = None
        db_session.commit()
        result = mixin.format_context(annotation)
        assert result == ""

