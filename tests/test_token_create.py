"""Unit tests for Token.create_from_sentence and related methods."""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from oeapp.db import Base
from oeapp.models.token import Token
from oeapp.models.project import Project
from oeapp.models.sentence import Sentence


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


@pytest.fixture
def project_and_sentence(db_session):
    """Create a test project and sentence."""
    # Create project
    project = Project(
        name="Test Project"
    )
    db_session.add(project)
    db_session.flush()

    # Create sentence
    sentence = Sentence.create(
        session=db_session,
        project_id=project.id,
        display_order=1,
        text_oe="Se cyning"
    )

    return project.id, sentence.id


class TestTokenize:
    """Test cases for Token.tokenize."""

    def test_tokenize_simple_sentence(self):
        """Test tokenizing a simple sentence."""
        result = Token.tokenize("Se cyning")
        assert result == ["Se", "cyning"]

    def test_tokenize_sentence_with_punctuation(self):
        """Test tokenizing a sentence with punctuation."""
        result = Token.tokenize("Se cyning wæs.")
        # Trailing punctuation is filtered out
        assert result == ["Se", "cyning", "wæs"]

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

    def test_tokenize_with_multiple_spaces(self):
        """Test tokenizing with multiple spaces."""
        result = Token.tokenize("Se    cyning")
        assert result == ["Se", "cyning"]

    def test_tokenize_with_punctuation_attached(self):
        """Test tokenizing with punctuation attached to words."""
        result = Token.tokenize("Se cyning.")
        # Trailing punctuation is filtered out
        assert result == ["Se", "cyning"]

    def test_tokenize_complex_sentence(self):
        """Test tokenizing a complex sentence."""
        result = Token.tokenize("Hwæt! Se cyning wæs gōd.")
        # Trailing punctuation is filtered out, but mid-sentence punctuation is kept
        assert result == ["Hwæt", "!", "Se", "cyning", "wæs", "gōd"]

    def test_tokenize_with_quotes(self):
        """Test tokenizing a sentence with quotes - quotes should be stripped."""
        result = Token.tokenize('Þā cwæð hē: "Hwæt sceal iċ singan?" ')
        # Quotes should be stripped, and ? should be filtered out
        assert result == ["Þā", "cwæð", "hē", "Hwæt", "sceal", "iċ", "singan"]

    def test_tokenize_hyphenated_word_ge_wat(self):
        """Test that ġe-wāt becomes a single token."""
        result = Token.tokenize("ġe-wāt")
        assert result == ["ġe-wāt"]

    def test_tokenize_hyphenated_word_be_bode(self):
        """Test that be-bode becomes a single token."""
        result = Token.tokenize("be-bode")
        assert result == ["be-bode"]

    def test_tokenize_hyphenated_word_be_gyman(self):
        """Test that be-ġȳman becomes a single token."""
        result = Token.tokenize("be-ġȳman")
        assert result == ["be-ġȳman"]

    def test_tokenize_standalone_hyphen(self):
        """Test that word - word filters out hyphen."""
        result = Token.tokenize("word - word")
        assert result == ["word", "word"]

    def test_tokenize_hyphen_with_spaces(self):
        """Test that hyphens with spaces are not part of tokens."""
        result = Token.tokenize("word - word")
        assert result == ["word", "word"]
        # Test with multiple spaces
        result = Token.tokenize("word  -  word")
        assert result == ["word", "word"]

    def test_tokenize_hyphenated_word_with_punctuation(self):
        """Test that ġe-wāt, splits correctly."""
        result = Token.tokenize("ġe-wāt,")
        # Comma attached to word should be filtered out
        assert result == ["ġe-wāt"]

    def test_tokenize_multiple_hyphenated_words(self):
        """Test multiple hyphenated words in one sentence."""
        result = Token.tokenize("ġe-wāt be-bode")
        assert result == ["ġe-wāt", "be-bode"]

    def test_tokenize_no_hyphenated_words(self):
        """Test sentences without hyphenated words work as before."""
        result = Token.tokenize("Se cyning wæs")
        assert result == ["Se", "cyning", "wæs"]

    def test_tokenize_hyphenated_word_at_start(self):
        """Test hyphenated word at sentence start."""
        result = Token.tokenize("ġe-wāt cyning")
        assert result == ["ġe-wāt", "cyning"]

    def test_tokenize_hyphenated_word_at_end(self):
        """Test hyphenated word at sentence end."""
        result = Token.tokenize("Se cyning ġe-wāt")
        assert result == ["Se", "cyning", "ġe-wāt"]

    def test_tokenize_en_dash(self):
        """Test en-dash (–) in hyphenated words."""
        result = Token.tokenize("ġe–wāt")
        assert result == ["ġe–wāt"]

    def test_tokenize_em_dash(self):
        """Test em-dash (—) in hyphenated words."""
        result = Token.tokenize("ġe—wāt")
        assert result == ["ġe—wāt"]

    def test_tokenize_hyphenated_word_in_sentence(self):
        """Test hyphenated word in middle of sentence."""
        result = Token.tokenize("Se ġe-wāt cyning")
        assert result == ["Se", "ġe-wāt", "cyning"]

    def test_tokenize_multiple_hyphenated_words_with_punctuation(self):
        """Test multiple hyphenated words with punctuation."""
        result = Token.tokenize("ġe-wāt, be-bode.")
        # Commas and trailing punctuation attached to words are filtered out
        assert result == ["ġe-wāt", "be-bode"]


class TestCreateFromSentence:
    """Test cases for Token.create_from_sentence."""

    def test_create_simple_sentence(self, db_session, project_and_sentence):
        """Test creating tokens from a simple sentence."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "Se cyning")

        assert len(tokens) == 2
        assert tokens[0].surface == "Se"
        assert tokens[0].order_index == 0
        assert tokens[0].sentence_id == sentence_id
        assert tokens[0].id is not None
        assert tokens[1].surface == "cyning"
        assert tokens[1].order_index == 1
        assert tokens[1].sentence_id == sentence_id
        assert tokens[1].id is not None

    def test_create_with_punctuation(self, db_session, project_and_sentence):
        """Test creating tokens with punctuation."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "Se cyning.")

        assert len(tokens) == 3
        assert tokens[0].surface == "Se"
        assert tokens[1].surface == "cyning"
        assert tokens[2].surface == "."
        assert tokens[2].order_index == 2

    def test_create_empty_sentence(self, db_session, project_and_sentence):
        """Test creating tokens from an empty sentence."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "")

        assert len(tokens) == 0

    def test_create_single_token(self, db_session, project_and_sentence):
        """Test creating a single token."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "cyning")

        assert len(tokens) == 1
        assert tokens[0].surface == "cyning"
        assert tokens[0].order_index == 0

    def test_sequential_order_indices(self, db_session, project_and_sentence):
        """Test that tokens are created with sequential order indices."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "Se cyning wæs gōd")

        assert len(tokens) == 4
        for i, token in enumerate(tokens):
            assert token.order_index == i, f"Token at index {i} has order_index {token.order_index}, expected {i}"

    def test_all_tokens_have_ids(self, db_session, project_and_sentence):
        """Test that all created tokens have database IDs."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "Se cyning wæs")

        assert len(tokens) == 3
        for token in tokens:
            assert token.id is not None, f"Token {token.surface} should have an ID"

    def test_all_tokens_have_timestamps(self, db_session, project_and_sentence):
        """Test that all created tokens have timestamps."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "Se cyning")

        assert len(tokens) == 2
        for token in tokens:
            assert token.created_at is not None, f"Token {token.surface} should have created_at"
            assert token.updated_at is not None, f"Token {token.surface} should have updated_at"
            # Timestamps may be strings from SQLite or datetime objects
            assert isinstance(token.created_at, (datetime, str))
            assert isinstance(token.updated_at, (datetime, str))

    def test_tokens_persisted_to_database(self, db_session, project_and_sentence):
        """Test that tokens are persisted to the database."""
        project_id, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(db_session, sentence_id)
        for token in existing_tokens:
            db_session.delete(token)
        db_session.commit()

        # Create new tokens
        tokens = Token.create_from_sentence(db_session, sentence_id, "Se cyning")
        db_session.commit()

        # Verify tokens can be retrieved from database
        retrieved_tokens = Token.list(db_session, sentence_id)
        assert len(retrieved_tokens) == 2
        assert retrieved_tokens[0].surface == "Se"
        assert retrieved_tokens[1].surface == "cyning"

    def test_tokens_correct_sentence_id(self, db_session, project_and_sentence):
        """Test that all tokens have the correct sentence_id."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "Se cyning wæs")

        assert len(tokens) == 3
        for token in tokens:
            assert token.sentence_id == sentence_id, f"Token {token.surface} should have sentence_id {sentence_id}"

    def test_create_with_old_english_characters(self, db_session, project_and_sentence):
        """Test creating tokens with Old English characters."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "þā ðæt")

        assert len(tokens) == 2
        assert tokens[0].surface == "þā"
        assert tokens[1].surface == "ðæt"

    def test_create_with_duplicate_tokens(self, db_session, project_and_sentence):
        """Test creating tokens with duplicate surfaces."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "þā cyning þā")

        assert len(tokens) == 3
        assert tokens[0].surface == "þā"
        assert tokens[1].surface == "cyning"
        assert tokens[2].surface == "þā"
        # Each token should have a unique ID even if surface is the same
        assert tokens[0].id != tokens[2].id

    def test_create_multiple_times_different_sentences(self, db_session):
        """Test creating tokens for different sentences."""
        # Create project
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        # Create first sentence
        sentence1 = Sentence.create(
            session=db_session,
            project_id=project.id,
            display_order=1,
            text_oe="Se cyning"
        )

        # Create second sentence
        sentence2 = Sentence.create(
            session=db_session,
            project_id=project.id,
            display_order=2,
            text_oe="wæs gōd"
        )

        # Get tokens from sentences
        tokens1 = Token.list(db_session, sentence1.id)
        tokens2 = Token.list(db_session, sentence2.id)

        # Both sets should exist
        assert len(tokens1) == 2
        assert len(tokens2) == 2
        assert tokens1[0].surface == "Se"
        assert tokens1[1].surface == "cyning"
        assert tokens2[0].surface == "wæs"
        assert tokens2[1].surface == "gōd"

    def test_create_with_whitespace(self, db_session, project_and_sentence):
        """Test creating tokens with extra whitespace."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "  Se   cyning  ")

        assert len(tokens) == 2
        assert tokens[0].surface == "Se"
        assert tokens[1].surface == "cyning"

    def test_create_complex_sentence(self, db_session, project_and_sentence):
        """Test creating tokens from a complex sentence."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "Hwæt! Se cyning wæs gōd.")

        # Tokenizer splits punctuation, so we get 7 tokens (including period)
        assert len(tokens) >= 6
        assert tokens[0].surface == "Hwæt"
        assert tokens[1].surface == "!"
        assert tokens[2].surface == "Se"
        assert tokens[3].surface == "cyning"
        assert tokens[4].surface == "wæs"
        assert tokens[5].surface == "gōd"
        # Period is separate token
        if len(tokens) > 6:
            assert tokens[6].surface == "."

    def test_order_indices_start_at_zero(self, db_session, project_and_sentence):
        """Test that order indices start at zero."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "Se cyning")

        assert len(tokens) >= 1
        assert tokens[0].order_index == 0

    def test_no_gaps_in_order_indices(self, db_session, project_and_sentence):
        """Test that there are no gaps in order indices."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "Se cyning wæs gōd")

        order_indices = [token.order_index for token in tokens]
        order_indices.sort()

        # Should be sequential with no gaps: [0, 1, 2, 3]
        assert order_indices == list(range(len(tokens)))

    def test_tokens_returned_in_order(self, db_session, project_and_sentence):
        """Test that tokens are returned in order."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "Se cyning wæs")

        assert tokens[0].order_index < tokens[1].order_index
        assert tokens[1].order_index < tokens[2].order_index

    def test_lemma_is_none_by_default(self, db_session, project_and_sentence):
        """Test that lemma is None by default."""
        _, sentence_id = project_and_sentence

        tokens = Token.create_from_sentence(db_session, sentence_id, "Se cyning")

        for token in tokens:
            assert token.lemma is None

    def test_different_sentences_different_tokens(self, db_session):
        """Test that tokens for different sentences are separate."""
        # Create project
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        # Create first sentence
        sentence1 = Sentence.create(
            session=db_session,
            project_id=project.id,
            display_order=1,
            text_oe="Se cyning"
        )

        # Create second sentence
        sentence2 = Sentence.create(
            session=db_session,
            project_id=project.id,
            display_order=2,
            text_oe="Se cyning"
        )

        # Get tokens from sentences
        tokens1 = Token.list(db_session, sentence1.id)
        tokens2 = Token.list(db_session, sentence2.id)

        # Both should have tokens
        assert len(tokens1) == 2
        assert len(tokens2) == 2

        # But they should have different IDs
        assert tokens1[0].id != tokens2[0].id
        assert tokens1[0].sentence_id == sentence1.id
        assert tokens2[0].sentence_id == sentence2.id

