"""Unit tests for Sentence model."""

from datetime import datetime

import pytest

from oeapp.models.sentence import Sentence
from tests.conftest import create_test_project


class TestSentence:
    """Test cases for Sentence model."""

    def test_create_model(self, db_session):
        """Test model creation."""
        project = create_test_project(db_session)

        sentence = Sentence(
            project_id=project.id,
            display_order=1,
            paragraph_number=1,
            sentence_number_in_paragraph=1,
            text_oe="Se cyning",
            is_paragraph_start=False,
        )
        db_session.add(sentence)
        db_session.commit()

        assert sentence.id is not None
        assert sentence.project_id == project.id
        assert sentence.text_oe == "Se cyning"
        assert isinstance(sentence.created_at, datetime)

    def test_get_returns_existing(self, db_session):
        """Test get() returns existing sentence."""
        project = create_test_project(db_session)
        sentence = Sentence.create(
            session=db_session,
            project_id=project.id,
            display_order=1,
            text_oe="Se cyning",
        )
        db_session.commit()
        sentence_id = sentence.id

        retrieved = Sentence.get(db_session, sentence_id)
        assert retrieved is not None
        assert retrieved.id == sentence_id
        assert retrieved.text_oe == "Se cyning"

    def test_get_returns_none_for_nonexistent(self, db_session):
        """Test get() returns None for nonexistent sentence."""
        result = Sentence.get(db_session, 99999)
        assert result is None

    def test_list_returns_sentences_for_project(self, db_session):
        """Test list() returns sentences for project."""
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            session=db_session, project_id=project.id, display_order=1, text_oe="First"
        )
        sentence2 = Sentence.create(
            session=db_session, project_id=project.id, display_order=2, text_oe="Second"
        )
        db_session.commit()

        sentences = Sentence.list(db_session, project.id)
        assert len(sentences) == 2
        assert all(s.project_id == project.id for s in sentences)

    def test_list_returns_empty_when_no_sentences(self, db_session):
        """Test list() returns empty list when no sentences exist."""
        project = create_test_project(db_session)
        sentences = Sentence.list(db_session, project.id)
        assert sentences == []

    def test_get_next_sentence_returns_next(self, db_session):
        """Test get_next_sentence() returns next sentence."""
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            session=db_session, project_id=project.id, display_order=1, text_oe="First"
        )
        sentence2 = Sentence.create(
            session=db_session, project_id=project.id, display_order=2, text_oe="Second"
        )
        db_session.commit()

        next_sentence = Sentence.get_next_sentence(db_session, project.id, 2)
        assert next_sentence is not None
        assert next_sentence.id == sentence2.id

    def test_get_next_sentence_returns_none_when_no_next(self, db_session):
        """Test get_next_sentence() returns None when no next sentence."""
        project = create_test_project(db_session)
        Sentence.create(
            session=db_session, project_id=project.id, display_order=1, text_oe="First"
        )
        db_session.commit()

        result = Sentence.get_next_sentence(db_session, project.id, 2)
        assert result is None

    def test_create_creates_sentence_with_tokens(self, db_session):
        """Test create() creates sentence and tokens."""
        project = create_test_project(db_session)

        sentence = Sentence.create(
            session=db_session,
            project_id=project.id,
            display_order=1,
            text_oe="Se cyning",
        )
        db_session.commit()

        assert sentence.id is not None
        assert len(sentence.tokens) > 0
        assert all(token.sentence_id == sentence.id for token in sentence.tokens)

    def test_create_calculates_paragraph_numbers_first_sentence(self, db_session):
        """Test create() calculates paragraph numbers for first sentence."""
        project = create_test_project(db_session)

        sentence = Sentence.create(
            session=db_session,
            project_id=project.id,
            display_order=1,
            text_oe="Se cyning",
            is_paragraph_start=True,
        )
        db_session.commit()

        assert sentence.paragraph_number == 1
        assert sentence.sentence_number_in_paragraph == 1

    def test_create_calculates_paragraph_numbers_continuing_paragraph(
        self, db_session
    ):
        """Test create() calculates paragraph numbers for continuing paragraph."""
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            session=db_session,
            project_id=project.id,
            display_order=1,
            text_oe="First",
            is_paragraph_start=True,
        )
        db_session.commit()

        sentence2 = Sentence.create(
            session=db_session,
            project_id=project.id,
            display_order=2,
            text_oe="Second",
            is_paragraph_start=False,
        )
        db_session.commit()

        assert sentence2.paragraph_number == sentence1.paragraph_number
        assert sentence2.sentence_number_in_paragraph == 2

    def test_create_calculates_paragraph_numbers_new_paragraph(self, db_session):
        """Test create() calculates paragraph numbers for new paragraph."""
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            session=db_session,
            project_id=project.id,
            display_order=1,
            text_oe="First",
            is_paragraph_start=True,
        )
        db_session.commit()

        sentence2 = Sentence.create(
            session=db_session,
            project_id=project.id,
            display_order=2,
            text_oe="Second",
            is_paragraph_start=True,
        )
        db_session.commit()

        assert sentence2.paragraph_number == sentence1.paragraph_number + 1
        assert sentence2.sentence_number_in_paragraph == 1

    def test_calculate_paragraph_and_sentence_numbers_first_sentence(self, db_session):
        """Test _calculate_paragraph_and_sentence_numbers() for first sentence."""
        project = create_test_project(db_session)

        result = Sentence._calculate_paragraph_and_sentence_numbers(
            db_session, project.id, 1, True
        )

        assert result["paragraph_number"] == 1
        assert result["sentence_number_in_paragraph"] == 1

    def test_calculate_paragraph_and_sentence_numbers_continuing(self, db_session):
        """Test _calculate_paragraph_and_sentence_numbers() for continuing sentence."""
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            session=db_session,
            project_id=project.id,
            display_order=1,
            text_oe="First",
            is_paragraph_start=True,
        )
        db_session.commit()

        result = Sentence._calculate_paragraph_and_sentence_numbers(
            db_session, project.id, 2, False
        )

        assert result["paragraph_number"] == sentence1.paragraph_number
        assert result["sentence_number_in_paragraph"] == 2

    def test_update_updates_sentence_text(self, db_session):
        """Test update() updates sentence text_oe and retokenizes."""
        project = create_test_project(db_session)
        sentence = Sentence.create(
            session=db_session, project_id=project.id, display_order=1, text_oe="Original"
        )
        db_session.commit()
        original_token_count = len(sentence.tokens)

        updated = sentence.update(db_session, "Updated text")
        db_session.commit()

        assert updated is not None
        assert updated.text_oe == "Updated text"
        # Tokens should be updated
        assert len(updated.tokens) > 0

    def test_to_json_serializes_sentence(self, db_session):
        """Test to_json() serializes sentence data."""
        project = create_test_project(db_session)
        sentence = Sentence.create(
            session=db_session, project_id=project.id, display_order=1, text_oe="Se cyning"
        )
        sentence.text_modern = "The king"
        db_session.commit()

        data = sentence.to_json(db_session)
        assert data["text_oe"] == "Se cyning"
        assert data["text_modern"] == "The king"
        assert "tokens" in data
        assert "notes" in data
        assert "created_at" in data

    def test_from_json_creates_sentence(self, db_session):
        """Test from_json() creates sentence from data."""
        project = create_test_project(db_session)

        sentence_data = {
            "text_oe": "Se cyning",
            "text_modern": "The king",
            "display_order": 1,
            "is_paragraph_start": False,
        }
        sentence = Sentence.from_json(db_session, project.id, sentence_data)
        db_session.commit()

        assert sentence.project_id == project.id
        assert sentence.text_oe == "Se cyning"
        assert sentence.text_modern == "The king"

    def test_subsequent_sentences_returns_subsequent(self, db_session):
        """Test subsequent_sentences() returns subsequent sentences."""
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            session=db_session, project_id=project.id, display_order=1, text_oe="First"
        )
        sentence2 = Sentence.create(
            session=db_session, project_id=project.id, display_order=2, text_oe="Second"
        )
        sentence3 = Sentence.create(
            session=db_session, project_id=project.id, display_order=3, text_oe="Third"
        )
        db_session.commit()

        subsequent = Sentence.subsequent_sentences(db_session, project.id, 1)
        assert len(subsequent) == 2
        assert all(s.display_order > 1 for s in subsequent)
        assert sentence2 in subsequent
        assert sentence3 in subsequent

    def test_subsequent_sentences_returns_empty_when_none(self, db_session):
        """Test subsequent_sentences() returns empty when no subsequent sentences."""
        project = create_test_project(db_session)
        Sentence.create(
            session=db_session, project_id=project.id, display_order=1, text_oe="First"
        )
        db_session.commit()

        subsequent = Sentence.subsequent_sentences(db_session, project.id, 1)
        assert subsequent == []

    def test_renumber_sentences_updates_display_order(self, db_session):
        """Test renumber_sentences() updates display order."""
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            session=db_session, project_id=project.id, display_order=1, text_oe="First"
        )
        sentence2 = Sentence.create(
            session=db_session, project_id=project.id, display_order=2, text_oe="Second"
        )
        db_session.commit()

        order_mapping = {sentence1.id: 2, sentence2.id: 1}
        changes = Sentence.renumber_sentences(
            db_session, [sentence1, sentence2], order_mapping=order_mapping
        )
        db_session.commit()

        assert len(changes) == 2
        db_session.refresh(sentence1)
        db_session.refresh(sentence2)
        assert sentence1.display_order == 2
        assert sentence2.display_order == 1

    def test_renumber_sentences_raises_error_without_mapping(self, db_session):
        """Test renumber_sentences() raises ValueError without mapping."""
        project = create_test_project(db_session)
        sentence = Sentence.create(
            session=db_session, project_id=project.id, display_order=1, text_oe="First"
        )
        db_session.commit()

        with pytest.raises(ValueError, match="Either order_mapping or order_function"):
            Sentence.renumber_sentences(db_session, [sentence])

    def test_created_at_set_on_creation(self, db_session):
        """Test created_at is set on creation."""
        project = create_test_project(db_session)

        before = datetime.now()
        sentence = Sentence.create(
            session=db_session, project_id=project.id, display_order=1, text_oe="Se cyning"
        )
        db_session.commit()
        after = datetime.now()

        assert before <= sentence.created_at <= after

    def test_updated_at_updates_on_change(self, db_session):
        """Test updated_at updates when sentence is modified."""
        project = create_test_project(db_session)
        sentence = Sentence.create(
            session=db_session, project_id=project.id, display_order=1, text_oe="Original"
        )
        db_session.commit()
        original_updated = sentence.updated_at

        import time

        time.sleep(0.01)

        sentence.text_oe = "Updated"
        db_session.commit()
        db_session.refresh(sentence)

        assert sentence.updated_at > original_updated

    def test_relationship_with_project(self, db_session):
        """Test sentence has relationship with project."""
        project = create_test_project(db_session)
        sentence = Sentence.create(
            session=db_session, project_id=project.id, display_order=1, text_oe="Se cyning"
        )
        db_session.commit()

        assert sentence.project.id == project.id
        assert sentence.project.name == project.name

    def test_relationship_with_tokens(self, db_session):
        """Test sentence has relationship with tokens."""
        project = create_test_project(db_session)
        sentence = Sentence.create(
            session=db_session, project_id=project.id, display_order=1, text_oe="Se cyning"
        )
        db_session.commit()

        assert len(sentence.tokens) > 0
        assert all(token.sentence_id == sentence.id for token in sentence.tokens)

