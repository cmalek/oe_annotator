"""Unit tests for hyphenated word migration."""

import pytest
import tempfile
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from oeapp.db import Base
from oeapp.models.token import Token
from oeapp.models.project import Project
from oeapp.models.sentence import Sentence
from oeapp.models.annotation import Annotation


@pytest.fixture
def db_session():
    """Create a temporary database and session for testing."""
    temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
    temp_db.close()
    db_path = Path(temp_db.name)

    # Create engine and session
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    engine.dispose()
    os.unlink(temp_db.name)


def _run_migration(session):
    """Run the migration logic manually for testing."""
    from oeapp.models.alembic.versions.merge_hyphenated_words import (
        _find_hyphenated_words,
        _map_tokens_to_positions,
        _merge_tokens_for_hyphenated_word,
    )
    import sqlalchemy as sa

    conn = session.connection()

    # Get all sentences
    sentences_result = conn.execute(
        sa.text("SELECT id, text_oe FROM sentences ORDER BY id")
    )
    sentences = sentences_result.fetchall()

    for sentence_id, text_oe in sentences:
        # Find hyphenated words in the text
        hyphenated_words = _find_hyphenated_words(text_oe)

        if not hyphenated_words:
            continue

        # Get all tokens for this sentence
        tokens_result = conn.execute(
            sa.text("""
                SELECT id, order_index, surface
                FROM tokens
                WHERE sentence_id = :sentence_id
                ORDER BY order_index
            """),
            {"sentence_id": sentence_id}
        )
        tokens = [
            {"id": row[0], "order_index": row[1], "surface": row[2]}
            for row in tokens_result.fetchall()
        ]

        if not tokens:
            continue

        # Map tokens to positions in text
        token_positions = _map_tokens_to_positions(text_oe, tokens)

        # Track matched tokens to avoid reusing them
        matched_token_ids = set()

        # Process each hyphenated word occurrence (in order of appearance)
        for hyphenated_word, word_start, word_end in hyphenated_words:
            _merge_tokens_for_hyphenated_word(
                conn,
                sentence_id,
                hyphenated_word,
                word_start,
                word_end,
                tokens,
                token_positions,
                matched_token_ids,
            )

        # Reorder remaining tokens' order_index values to fill gaps
        tokens_result = conn.execute(
            sa.text("""
                SELECT id FROM tokens
                WHERE sentence_id = :sentence_id
                ORDER BY order_index
            """),
            {"sentence_id": sentence_id}
        )
        remaining_tokens = [row[0] for row in tokens_result.fetchall()]

        # Update order_index to be sequential (0, 1, 2, ...)
        for new_index, token_id in enumerate(remaining_tokens):
            conn.execute(
                sa.text("UPDATE tokens SET order_index = :order_index WHERE id = :token_id"),
                {"order_index": new_index, "token_id": token_id}
            )

    session.commit()


class TestHyphenatedWordMigration:
    """Test cases for hyphenated word migration."""

    def test_migration_simple_hyphenated_word(self, db_session):
        """Test merging ġe + wāt → ġe-wāt."""
        # Create project and sentence with split tokens
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        sentence = Sentence(
            project_id=project.id,
            display_order=1,
            text_oe="ġe-wāt",
            paragraph_number=1,
            sentence_number_in_paragraph=1
        )
        db_session.add(sentence)
        db_session.flush()

        # Create tokens as if they were split (old behavior)
        token1 = Token(
            sentence_id=sentence.id,
            order_index=0,
            surface="ġe"
        )
        db_session.add(token1)
        token2 = Token(
            sentence_id=sentence.id,
            order_index=1,
            surface="wāt"
        )
        db_session.add(token2)
        db_session.commit()

        # Run migration
        _run_migration(db_session)

        # Verify tokens were merged
        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) == 1
        assert tokens[0].surface == "ġe-wāt"
        assert tokens[0].order_index == 0

    def test_migration_multiple_identical_hyphenated_words(self, db_session):
        """Test multiple occurrences of same hyphenated word."""
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        sentence = Sentence(
            project_id=project.id,
            display_order=1,
            text_oe="ġe-wāt and ġe-wāt",
            paragraph_number=1,
            sentence_number_in_paragraph=1
        )
        db_session.add(sentence)
        db_session.flush()

        # Create split tokens
        tokens_data = [
            (0, "ġe"), (1, "wāt"), (2, "and"), (3, "ġe"), (4, "wāt")
        ]
        for order_index, surface in tokens_data:
            token = Token(
                sentence_id=sentence.id,
                order_index=order_index,
                surface=surface
            )
            db_session.add(token)
        db_session.commit()

        # Run migration
        _run_migration(db_session)

        # Verify both hyphenated words were merged
        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) == 3
        assert tokens[0].surface == "ġe-wāt"
        assert tokens[1].surface == "and"
        assert tokens[2].surface == "ġe-wāt"

    def test_migration_no_hyphenated_words(self, db_session):
        """Test sentences with no hyphenated words (should skip)."""
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        sentence = Sentence.create(
            session=db_session,
            project_id=project.id,
            display_order=1,
            text_oe="Se cyning wæs"
        )

        original_tokens = Token.list(db_session, sentence.id)
        original_count = len(original_tokens)

        # Run migration
        _run_migration(db_session)

        # Verify tokens unchanged
        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) == original_count
        assert tokens[0].surface == "Se"
        assert tokens[1].surface == "cyning"
        assert tokens[2].surface == "wæs"

    def test_migration_preserves_main_token_annotation(self, db_session):
        """Test annotation preserved on main word."""
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        sentence = Sentence(
            project_id=project.id,
            display_order=1,
            text_oe="ġe-wāt",
            paragraph_number=1,
            sentence_number_in_paragraph=1
        )
        db_session.add(sentence)
        db_session.flush()

        # Create tokens with annotation on main word
        token1 = Token(
            sentence_id=sentence.id,
            order_index=0,
            surface="ġe"
        )
        db_session.add(token1)
        db_session.flush()

        token2 = Token(
            sentence_id=sentence.id,
            order_index=1,
            surface="wāt"
        )
        db_session.add(token2)
        db_session.flush()

        # Add annotation to main word token
        annotation = Annotation(
            token_id=token2.id,
            pos="V"
        )
        db_session.add(annotation)
        db_session.commit()

        # Run migration
        _run_migration(db_session)

        # Verify annotation is preserved
        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) == 1
        assert tokens[0].annotation is not None
        assert tokens[0].annotation.pos == "V"

    def test_migration_discards_prefix_annotation(self, db_session):
        """Test prefix annotation is discarded."""
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        sentence = Sentence(
            project_id=project.id,
            display_order=1,
            text_oe="ġe-wāt",
            paragraph_number=1,
            sentence_number_in_paragraph=1
        )
        db_session.add(sentence)
        db_session.flush()

        # Create tokens with annotation on prefix
        token1 = Token(
            sentence_id=sentence.id,
            order_index=0,
            surface="ġe"
        )
        db_session.add(token1)
        db_session.flush()

        token2 = Token(
            sentence_id=sentence.id,
            order_index=1,
            surface="wāt"
        )
        db_session.add(token2)
        db_session.flush()

        # Add annotation to prefix token (should be discarded)
        annotation = Annotation(
            token_id=token1.id,
            pos="N"  # Use valid POS value
        )
        db_session.add(annotation)
        db_session.commit()

        # Run migration
        _run_migration(db_session)

        # Verify prefix token and its annotation are gone
        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) == 1
        # Annotation should not exist (was on deleted token)
        assert tokens[0].annotation is None

    def test_migration_reorders_token_indices(self, db_session):
        """Test order_index values are correctly reordered."""
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        sentence = Sentence(
            project_id=project.id,
            display_order=1,
            text_oe="Se ġe-wāt cyning",
            paragraph_number=1,
            sentence_number_in_paragraph=1
        )
        db_session.add(sentence)
        db_session.flush()

        # Create tokens: Se, ġe, wāt, cyning
        tokens_data = [
            (0, "Se"), (1, "ġe"), (2, "wāt"), (3, "cyning")
        ]
        for order_index, surface in tokens_data:
            token = Token(
                sentence_id=sentence.id,
                order_index=order_index,
                surface=surface
            )
            db_session.add(token)
        db_session.commit()

        # Run migration
        _run_migration(db_session)

        # Verify order_index is sequential
        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) == 3
        for i, token in enumerate(tokens):
            assert token.order_index == i

    def test_migration_multiple_hyphenated_words_in_sentence(self, db_session):
        """Test multiple different hyphenated words."""
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        sentence = Sentence(
            project_id=project.id,
            display_order=1,
            text_oe="ġe-wāt be-bode",
            paragraph_number=1,
            sentence_number_in_paragraph=1
        )
        db_session.add(sentence)
        db_session.flush()

        # Create split tokens
        tokens_data = [
            (0, "ġe"), (1, "wāt"), (2, "be"), (3, "bode")
        ]
        for order_index, surface in tokens_data:
            token = Token(
                sentence_id=sentence.id,
                order_index=order_index,
                surface=surface
            )
            db_session.add(token)
        db_session.commit()

        # Run migration
        _run_migration(db_session)

        # Verify both hyphenated words were merged
        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) == 2
        assert tokens[0].surface == "ġe-wāt"
        assert tokens[1].surface == "be-bode"

    def test_migration_hyphenated_word_at_start(self, db_session):
        """Test hyphenated word at sentence start."""
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        sentence = Sentence(
            project_id=project.id,
            display_order=1,
            text_oe="ġe-wāt cyning",
            paragraph_number=1,
            sentence_number_in_paragraph=1
        )
        db_session.add(sentence)
        db_session.flush()

        tokens_data = [(0, "ġe"), (1, "wāt"), (2, "cyning")]
        for order_index, surface in tokens_data:
            token = Token(
                sentence_id=sentence.id,
                order_index=order_index,
                surface=surface
            )
            db_session.add(token)
        db_session.commit()

        _run_migration(db_session)

        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) == 2
        assert tokens[0].surface == "ġe-wāt"
        assert tokens[1].surface == "cyning"

    def test_migration_hyphenated_word_at_end(self, db_session):
        """Test hyphenated word at sentence end."""
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        sentence = Sentence(
            project_id=project.id,
            display_order=1,
            text_oe="Se cyning ġe-wāt",
            paragraph_number=1,
            sentence_number_in_paragraph=1
        )
        db_session.add(sentence)
        db_session.flush()

        tokens_data = [(0, "Se"), (1, "cyning"), (2, "ġe"), (3, "wāt")]
        for order_index, surface in tokens_data:
            token = Token(
                sentence_id=sentence.id,
                order_index=order_index,
                surface=surface
            )
            db_session.add(token)
        db_session.commit()

        _run_migration(db_session)

        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) == 3
        assert tokens[0].surface == "Se"
        assert tokens[1].surface == "cyning"
        assert tokens[2].surface == "ġe-wāt"

    def test_migration_with_en_dash(self, db_session):
        """Test en-dash (–) handling."""
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        sentence = Sentence(
            project_id=project.id,
            display_order=1,
            text_oe="ġe–wāt",
            paragraph_number=1,
            sentence_number_in_paragraph=1
        )
        db_session.add(sentence)
        db_session.flush()

        tokens_data = [(0, "ġe"), (1, "wāt")]
        for order_index, surface in tokens_data:
            token = Token(
                sentence_id=sentence.id,
                order_index=order_index,
                surface=surface
            )
            db_session.add(token)
        db_session.commit()

        _run_migration(db_session)

        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) == 1
        assert tokens[0].surface == "ġe–wāt"

    def test_migration_with_em_dash(self, db_session):
        """Test em-dash (—) handling."""
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        sentence = Sentence(
            project_id=project.id,
            display_order=1,
            text_oe="ġe—wāt",
            paragraph_number=1,
            sentence_number_in_paragraph=1
        )
        db_session.add(sentence)
        db_session.flush()

        tokens_data = [(0, "ġe"), (1, "wāt")]
        for order_index, surface in tokens_data:
            token = Token(
                sentence_id=sentence.id,
                order_index=order_index,
                surface=surface
            )
            db_session.add(token)
        db_session.commit()

        _run_migration(db_session)

        tokens = Token.list(db_session, sentence.id)
        assert len(tokens) == 1
        assert tokens[0].surface == "ġe—wāt"
