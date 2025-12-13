"""Unit tests for Note model."""

from datetime import datetime

import pytest

from oeapp.models.note import Note
from oeapp.models.token import Token
from tests.conftest import create_test_project, create_test_sentence


class TestNote:
    """Test cases for Note model."""

    def test_create_with_all_fields(self, db_session):
        """Test model creation with all fields."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        # Use existing tokens created by Sentence.create
        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) >= 2, "Need at least 2 tokens for this test"
        start_token = tokens[0]
        end_token = tokens[1]

        note = Note(
            sentence_id=sentence.id,
            start_token=start_token.id,
            end_token=end_token.id,
            note_text_md="This is a test note",
            note_type="span",
        )
        db_session.add(note)
        db_session.commit()

        assert note.sentence_id == sentence.id
        assert note.start_token == start_token.id
        assert note.end_token == end_token.id
        assert note.note_text_md == "This is a test note"
        assert note.note_type == "span"

    def test_create_with_partial_fields(self, db_session):
        """Test model creation with None start_token/end_token."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        note = Note(
            sentence_id=sentence.id,
            start_token=None,
            end_token=None,
            note_text_md="Sentence-level note",
            note_type="sentence",
        )
        db_session.add(note)
        db_session.commit()

        assert note.start_token is None
        assert note.end_token is None
        assert note.note_type == "sentence"

    def test_get_returns_existing(self, db_session):
        """Test get() returns existing note."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        # Use existing token created by Sentence.create
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        note = Note(
            sentence_id=sentence.id,
            start_token=token.id,
            end_token=token.id,
            note_text_md="Test note",
        )
        db_session.add(note)
        db_session.commit()
        note_id = note.id

        retrieved = Note.get(db_session, note_id)
        assert retrieved is not None
        assert retrieved.id == note_id
        assert retrieved.note_text_md == "Test note"

    def test_get_returns_none_for_nonexistent(self, db_session):
        """Test get() returns None for nonexistent note."""
        result = Note.get(db_session, 99999)
        assert result is None

    def test_sanitize_foreign_keys_converts_zero_to_none(self, db_session):
        """Test _sanitize_foreign_keys() converts 0 to None."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        note = Note(
            sentence_id=sentence.id,
            start_token=0,  # Will be sanitized
            end_token=0,  # Will be sanitized
            note_text_md="Test",
        )
        # Manually call the sanitizer to test it
        note._sanitize_foreign_keys()
        assert note.start_token is None
        assert note.end_token is None

        # Also test with valid IDs
        tokens = Token.list(db_session, sentence.id)
        if tokens:
            note2 = Note(
                sentence_id=sentence.id,
                start_token=tokens[0].id,
                end_token=tokens[0].id,
                note_text_md="Test 2",
            )
            note2._sanitize_foreign_keys()
            assert note2.start_token == tokens[0].id
            assert note2.end_token == tokens[0].id

    def test_to_json_serializes_note(self, db_session):
        """Test to_json() serializes note data."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        # Use existing tokens created by Sentence.create
        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) >= 2, "Need at least 2 tokens for this test"
        start_token = tokens[0]
        end_token = tokens[1]

        note = Note(
            sentence_id=sentence.id,
            start_token=start_token.id,
            end_token=end_token.id,
            note_text_md="Test note",
            note_type="span",
        )
        db_session.add(note)
        db_session.commit()

        data = note.to_json(db_session)
        assert data["note_text_md"] == "Test note"
        assert data["note_type"] == "span"
        assert "start_token_order_index" in data
        assert data["start_token_order_index"] == start_token.order_index
        assert "end_token_order_index" in data
        assert data["end_token_order_index"] == end_token.order_index
        assert "created_at" in data
        assert "updated_at" in data

    def test_to_json_handles_none_tokens(self, db_session):
        """Test to_json() handles None start_token/end_token."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        note = Note(
            sentence_id=sentence.id,
            start_token=None,
            end_token=None,
            note_text_md="Sentence note",
        )
        db_session.add(note)
        db_session.commit()

        data = note.to_json(db_session)
        assert "start_token_order_index" not in data
        assert "end_token_order_index" not in data

    def test_from_json_creates_note(self, db_session):
        """Test from_json() creates note from data."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        # Use existing tokens created by Sentence.create
        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) >= 2, "Need at least 2 tokens for this test"
        start_token = tokens[0]
        end_token = tokens[1]

        # Create token map
        token_map = {start_token.order_index: start_token, end_token.order_index: end_token}

        note_data = {
            "note_text_md": "Test note",
            "note_type": "span",
            "start_token_order_index": start_token.order_index,
            "end_token_order_index": end_token.order_index,
        }
        note = Note.from_json(db_session, sentence.id, note_data, token_map)
        db_session.commit()

        assert note.sentence_id == sentence.id
        assert note.start_token == start_token.id
        assert note.end_token == end_token.id
        assert note.note_text_md == "Test note"

    def test_from_json_handles_missing_token_indices(self, db_session):
        """Test from_json() handles missing token order indices."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        note_data = {
            "note_text_md": "Sentence note",
            "note_type": "sentence",
        }
        token_map = {}
        note = Note.from_json(db_session, sentence.id, note_data, token_map)
        db_session.commit()

        assert note.start_token is None
        assert note.end_token is None

    def test_from_json_handles_invalid_token_indices(self, db_session):
        """Test from_json() handles invalid token order indices."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        note_data = {
            "note_text_md": "Test",
            "start_token_order_index": 999,  # Invalid index
        }
        token_map = {}
        note = Note.from_json(db_session, sentence.id, note_data, token_map)
        db_session.commit()

        assert note.start_token is None

    def test_check_constraint_rejects_invalid_note_type(self, db_session):
        """Test check constraint rejects invalid note_type values."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        note = Note(
            sentence_id=sentence.id,
            note_text_md="Test",
            note_type="invalid",
        )
        db_session.add(note)
        with pytest.raises(Exception):  # IntegrityError or similar
            db_session.commit()

    def test_created_at_set_on_creation(self, db_session):
        """Test created_at is set on creation."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        before = datetime.now()
        note = Note(sentence_id=sentence.id, note_text_md="Test")
        db_session.add(note)
        db_session.commit()
        after = datetime.now()

        assert before <= note.created_at <= after

    def test_updated_at_updates_on_change(self, db_session):
        """Test updated_at updates when note is modified."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        note = Note(sentence_id=sentence.id, note_text_md="Original")
        db_session.add(note)
        db_session.commit()
        original_updated = note.updated_at

        import time

        time.sleep(0.01)

        note.note_text_md = "Updated"
        db_session.commit()
        db_session.refresh(note)

        assert note.updated_at > original_updated

    def test_relationship_with_sentence(self, db_session):
        """Test note has relationship with sentence."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")

        note = Note(sentence_id=sentence.id, note_text_md="Test")
        db_session.add(note)
        db_session.commit()

        assert note.sentence.id == sentence.id
        assert note.sentence.text_oe == "Se cyning"

