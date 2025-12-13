"""Unit tests for Annotation model."""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from oeapp.models.annotation import Annotation
from oeapp.models.token import Token
from tests.conftest import create_test_project, create_test_sentence


class TestAnnotation:
    """Test cases for Annotation model."""

    def test_create_with_all_fields(self, db_session):
        """Test model creation with all fields."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        # Sentence.create already creates tokens, so get the first one
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]  # Use existing token instead of creating new one

        # Delete existing annotation created by Sentence.create
        existing_ann = Annotation.get(db_session, token.id)
        if existing_ann:
            db_session.delete(existing_ann)
            db_session.commit()

        annotation = Annotation(
            token_id=token.id,
            pos="N",
            gender="m",
            number="s",
            case="n",
            declension="s",
            verb_class="w1",
            verb_tense="p",
            verb_mood="i",
            verb_person=3,
            verb_aspect="p",
            verb_form="f",
            prep_case="d",
            adjective_inflection="s",
            adjective_degree="p",
            adverb_degree="p",
            conjunction_type="c",
            pronoun_type="p",
            pronoun_number="s",
            article_type="d",
            uncertain=True,
            alternatives_json="w2 / s3",
            confidence=75,
            modern_english_meaning="king",
            root="cyning",
        )
        db_session.add(annotation)
        db_session.commit()

        assert annotation.token_id == token.id
        assert annotation.pos == "N"
        assert annotation.gender == "m"
        assert annotation.number == "s"
        assert annotation.case == "n"
        assert annotation.uncertain is True
        assert annotation.confidence == 75

    def test_create_with_partial_fields(self, db_session):
        """Test model creation with partial fields (None values)."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        # Sentence.create already creates tokens, so get the first one
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]  # Use existing token instead of creating new one

        # Delete existing annotation created by Sentence.create
        existing_ann = Annotation.get(db_session, token.id)
        if existing_ann:
            db_session.delete(existing_ann)
            db_session.commit()

        annotation = Annotation(token_id=token.id, pos="N", gender="m")
        db_session.add(annotation)
        db_session.commit()

        assert annotation.pos == "N"
        assert annotation.gender == "m"
        assert annotation.number is None
        assert annotation.case is None

    def test_get_returns_existing(self, db_session):
        """Test get() returns existing annotation."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Get existing annotation and update it
        annotation = Annotation.get(db_session, token.id)
        assert annotation is not None
        annotation.pos = "N"
        annotation.gender = "m"
        db_session.commit()
        annotation_id = annotation.token_id

        retrieved = Annotation.get(db_session, annotation_id)
        assert retrieved is not None
        assert retrieved.token_id == annotation_id
        assert retrieved.pos == "N"

    def test_get_returns_none_for_nonexistent(self, db_session):
        """Test get() returns None for nonexistent annotation."""
        result = Annotation.get(db_session, 99999)
        assert result is None

    def test_exists_returns_true_when_exists(self, db_session):
        """Test exists() returns True when annotation exists."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Annotation already exists from Sentence.create
        assert Annotation.exists(db_session, token.id) is True

    def test_exists_returns_false_when_not_exists(self, db_session):
        """Test exists() returns False when annotation doesn't exist."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Delete existing annotation
        existing_ann = Annotation.get(db_session, token.id)
        if existing_ann:
            db_session.delete(existing_ann)
            db_session.commit()

        assert Annotation.exists(db_session, token.id) is False

    def test_to_json_serializes_all_fields(self, db_session):
        """Test to_json() serializes all fields."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Get existing annotation and update it
        annotation = Annotation.get(db_session, token.id)
        assert annotation is not None
        annotation.pos = "N"
        annotation.gender = "m"
        annotation.number = "s"
        annotation.case = "n"
        annotation.modern_english_meaning = "king"
        annotation.root = "cyning"
        annotation.confidence = 75
        annotation.uncertain = True
        db_session.commit()

        data = annotation.to_json()
        assert data["pos"] == "N"
        assert data["gender"] == "m"
        assert data["number"] == "s"
        assert data["case"] == "n"
        assert data["modern_english_meaning"] == "king"
        assert data["root"] == "cyning"
        assert data["confidence"] == 75
        assert data["uncertain"] is True
        assert "updated_at" in data

    def test_from_json_creates_annotation(self, db_session):
        """Test from_json() creates annotation from data."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Delete existing annotation created by Sentence.create
        existing_ann = Annotation.get(db_session, token.id)
        if existing_ann:
            db_session.delete(existing_ann)
            db_session.commit()

        ann_data = {
            "pos": "N",
            "gender": "m",
            "number": "s",
            "case": "n",
            "modern_english_meaning": "king",
            "root": "cyning",
        }
        annotation = Annotation.from_json(db_session, token.id, ann_data)
        db_session.commit()

        assert annotation.token_id == token.id
        assert annotation.pos == "N"
        assert annotation.gender == "m"
        assert annotation.number == "s"
        assert annotation.case == "n"

    def test_from_json_handles_partial_data(self, db_session):
        """Test from_json() handles partial data."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Delete existing annotation created by Sentence.create
        existing_ann = Annotation.get(db_session, token.id)
        if existing_ann:
            db_session.delete(existing_ann)
            db_session.commit()

        ann_data = {"pos": "N"}
        annotation = Annotation.from_json(db_session, token.id, ann_data)
        db_session.commit()

        assert annotation.pos == "N"
        assert annotation.gender is None

    def test_check_constraint_rejects_invalid_pos(self, db_session):
        """Test check constraint rejects invalid POS values."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Delete existing annotation
        existing_ann = Annotation.get(db_session, token.id)
        if existing_ann:
            db_session.delete(existing_ann)
            db_session.commit()

        annotation = Annotation(token_id=token.id, pos="X")
        db_session.add(annotation)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_check_constraint_rejects_invalid_gender(self, db_session):
        """Test check constraint rejects invalid gender values."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Delete existing annotation
        existing_ann = Annotation.get(db_session, token.id)
        if existing_ann:
            db_session.delete(existing_ann)
            db_session.commit()

        annotation = Annotation(token_id=token.id, pos="N", gender="x")
        db_session.add(annotation)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_check_constraint_rejects_invalid_number(self, db_session):
        """Test check constraint rejects invalid number values."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Delete existing annotation
        existing_ann = Annotation.get(db_session, token.id)
        if existing_ann:
            db_session.delete(existing_ann)
            db_session.commit()

        annotation = Annotation(token_id=token.id, pos="N", number="x")
        db_session.add(annotation)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_check_constraint_rejects_invalid_case(self, db_session):
        """Test check constraint rejects invalid case values."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Delete existing annotation
        existing_ann = Annotation.get(db_session, token.id)
        if existing_ann:
            db_session.delete(existing_ann)
            db_session.commit()

        annotation = Annotation(token_id=token.id, pos="N", case="x")
        db_session.add(annotation)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_check_constraint_rejects_invalid_confidence(self, db_session):
        """Test check constraint rejects invalid confidence values."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Delete existing annotation
        existing_ann = Annotation.get(db_session, token.id)
        if existing_ann:
            db_session.delete(existing_ann)
            db_session.commit()

        # Confidence > 100
        annotation = Annotation(token_id=token.id, pos="N", confidence=101)
        db_session.add(annotation)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Confidence < 0
        annotation2 = Annotation(token_id=token.id, pos="N", confidence=-1)
        db_session.add(annotation2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_updated_at_set_on_creation(self, db_session):
        """Test updated_at is set on creation."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Get existing annotation and update it
        annotation = Annotation.get(db_session, token.id)
        assert annotation is not None
        before = datetime.now()
        annotation.pos = "N"
        db_session.commit()
        after = datetime.now()

        assert before <= annotation.updated_at <= after

    def test_updated_at_updates_on_change(self, db_session):
        """Test updated_at updates when annotation is modified."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Get existing annotation
        annotation = Annotation.get(db_session, token.id)
        assert annotation is not None
        annotation.pos = "N"
        db_session.commit()
        db_session.refresh(annotation)
        original_updated = annotation.updated_at

        import time

        time.sleep(0.01)  # Small delay to ensure timestamp difference

        annotation.pos = "V"
        db_session.commit()
        db_session.refresh(annotation)

        assert annotation.updated_at > original_updated

    def test_relationship_with_token(self, db_session):
        """Test annotation has relationship with token."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(db_session, sentence.id)
        token = tokens[0]

        # Get existing annotation
        annotation = Annotation.get(db_session, token.id)
        assert annotation is not None
        annotation.pos = "N"
        db_session.commit()

        assert annotation.token.id == token.id
        assert annotation.token.surface in ["Se", "cyning"]  # Could be either token

