"""Comprehensive unit tests for Token model."""

from datetime import datetime

import pytest

from oeapp.models.annotation import Annotation
from oeapp.models.token import Token
from tests.conftest import create_test_project, create_test_sentence


class TestToken:
    """Test cases for Token model."""

    def test_create_model(self, db_session):
        """Test model creation."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        # Use existing token created by Sentence.create
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        assert token.id is not None
        assert token.sentence_id == sentence.id
        assert token.surface in ["Se", "cyning"]  # Could be either
        assert isinstance(token.created_at, datetime)

    def test_get_returns_existing(self, db_session):
        """Test get() returns existing token."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token_id = tokens[0].id

        retrieved = Token.get(db_session, token_id)
        assert retrieved is not None
        assert retrieved.id == token_id
        assert retrieved.surface == tokens[0].surface

    def test_get_returns_none_for_nonexistent(self, db_session):
        """Test get() returns None for nonexistent token."""
        result = Token.get(db_session, 99999)
        assert result is None

    def test_list_returns_tokens_for_sentence(self, db_session):
        """Test list() returns tokens for sentence ordered by order_index."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning wæs")

        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) >= 3
        assert all(t.sentence_id == sentence.id for t in tokens)
        # Check ordering
        for i in range(len(tokens) - 1):
            assert tokens[i].order_index < tokens[i + 1].order_index

    def test_list_returns_empty_when_no_tokens(self, db_session):
        """Test list() returns empty list when no tokens exist."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "")
        # Empty sentence should have no tokens
        tokens = Token.list(db_session, sentence.id)
        assert tokens == []

    def test_create_from_sentence_creates_tokens(self, db_session):
        """Test create_from_sentence() creates tokens from text."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        # Clear existing tokens
        existing = Token.list(db_session, sentence.id)
        for token in existing:
            db_session.delete(token)
        db_session.commit()

        tokens = Token.create_from_sentence(db_session, sentence.id, "Se cyning")
        db_session.commit()

        assert len(tokens) == 2
        assert tokens[0].surface == "Se"
        assert tokens[0].order_index == 0
        assert tokens[1].surface == "cyning"
        assert tokens[1].order_index == 1

    def test_create_from_sentence_creates_annotations(self, db_session):
        """Test create_from_sentence() creates empty annotations."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        # Clear existing tokens
        existing = Token.list(db_session, sentence.id)
        for token in existing:
            db_session.delete(token)
        db_session.commit()

        tokens = Token.create_from_sentence(db_session, sentence.id, "Se cyning")
        db_session.commit()

        # Check that annotations were created
        for token in tokens:
            assert token.id is not None
            annotation = Annotation.get(db_session, token.id)
            assert annotation is not None

    def test_to_json_serializes_token(self, db_session):
        """Test to_json() serializes token data."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        data = token.to_json()
        assert data["order_index"] == token.order_index
        assert data["surface"] == token.surface
        assert data["lemma"] == token.lemma
        assert "created_at" in data
        assert "updated_at" in data

    def test_to_json_includes_annotation(self, db_session):
        """Test to_json() includes annotation if present."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Add annotation
        annotation = Annotation.get(db_session, token.id)
        if annotation:
            annotation.pos = "N"
            annotation.gender = "m"
            db_session.commit()

        data = token.to_json()
        assert "annotation" in data
        assert data["annotation"]["pos"] == "N"
        assert data["annotation"]["gender"] == "m"

    def test_to_json_excludes_annotation_when_none(self, db_session):
        """Test to_json() excludes annotation when None."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Ensure no annotation
        annotation = Annotation.get(db_session, token.id)
        if annotation:
            db_session.delete(annotation)
            db_session.commit()

        data = token.to_json()
        # Annotation key should not be present or should be None
        if "annotation" in data:
            assert data["annotation"] is None

    def test_from_json_creates_token(self, db_session):
        """Test from_json() creates token from data."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        token_data = {
            "order_index": 2,
            "surface": "wæs",
            "lemma": "wesan",
            "created_at": "2024-01-15T10:30:45+00:00",
            "updated_at": "2024-01-15T10:30:45+00:00",
        }
        token = Token.from_json(db_session, sentence.id, token_data)
        db_session.commit()

        assert token.sentence_id == sentence.id
        assert token.order_index == 2
        assert token.surface == "wæs"
        assert token.lemma == "wesan"

    def test_from_json_creates_annotation(self, db_session):
        """Test from_json() creates annotation if present in data."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        token_data = {
            "order_index": 2,
            "surface": "wæs",
            "annotation": {
                "pos": "V",
                "verb_tense": "p",
            },
        }
        token = Token.from_json(db_session, sentence.id, token_data)
        db_session.commit()

        annotation = Annotation.get(db_session, token.id)
        assert annotation is not None
        assert annotation.pos == "V"
        assert annotation.verb_tense == "p"

    def test_from_json_handles_missing_annotation(self, db_session):
        """Test from_json() handles missing annotation in data."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        token_data = {
            "order_index": 2,
            "surface": "wæs",
        }
        token = Token.from_json(db_session, sentence.id, token_data)
        db_session.commit()

        # Should still create token
        assert token.surface == "wæs"

    def test_delete_removes_token(self, db_session):
        """Test deleting token removes it."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token_id = tokens[0].id

        # Delete token directly
        token = Token.get(db_session, token_id)
        db_session.delete(token)
        db_session.commit()

        assert Token.get(db_session, token_id) is None

    def test_delete_cascades_to_annotation(self, db_session):
        """Test deleting token cascades to annotation."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Ensure annotation exists
        annotation = Annotation.get(db_session, token.id)
        assert annotation is not None

        db_session.delete(token)
        db_session.commit()

        # Annotation should be deleted via cascade
        annotation_after = Annotation.get(db_session, token.id)
        assert annotation_after is None

    def test_unique_constraint_prevents_duplicate_order(self, db_session):
        """Test unique constraint prevents duplicate order_index per sentence."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        # Try to create token with duplicate order_index
        token1 = Token(sentence_id=sentence.id, order_index=0, surface="first")
        token2 = Token(sentence_id=sentence.id, order_index=0, surface="second")
        db_session.add(token1)
        db_session.add(token2)

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_created_at_set_on_creation(self, db_session):
        """Test created_at is set on creation."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        before = datetime.now()
        token = Token(sentence_id=sentence.id, order_index=10, surface="test")
        db_session.add(token)
        db_session.commit()
        after = datetime.now()

        assert before <= token.created_at <= after

    def test_updated_at_updates_on_change(self, db_session):
        """Test updated_at updates when token is modified."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]
        original_updated = token.updated_at

        import time

        time.sleep(0.01)

        token.surface = "updated"
        db_session.commit()
        db_session.refresh(token)

        assert token.updated_at > original_updated

    def test_relationship_with_sentence(self, db_session):
        """Test token has relationship with sentence."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        assert token.sentence.id == sentence.id
        assert token.sentence.text_oe == "Se cyning"

    def test_relationship_with_annotation(self, db_session):
        """Test token has relationship with annotation."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Annotation should exist (created by create_from_sentence)
        assert token.annotation is not None
        assert token.annotation.token_id == token.id


class TestTokenize:
    """Test cases for Token.tokenize() static method."""

    def test_tokenize_simple_sentence(self):
        """Test tokenizing a simple sentence."""
        result = Token.tokenize("Se cyning")
        assert result == ["Se", "cyning"]

    def test_tokenize_empty_string(self):
        """Test tokenizing an empty string."""
        result = Token.tokenize("")
        assert result == []

    def test_tokenize_whitespace_only(self):
        """Test tokenizing whitespace-only string."""
        result = Token.tokenize("   ")
        assert result == []

    def test_tokenize_old_english_characters(self):
        """Test tokenizing Old English characters."""
        result = Token.tokenize("þā ðæt")
        assert result == ["þā", "ðæt"]

    def test_tokenize_with_punctuation(self):
        """Test tokenizing with punctuation."""
        result = Token.tokenize("Se cyning wæs.")
        # Trailing punctuation is filtered out
        assert "Se" in result
        assert "cyning" in result
        assert "wæs" in result

