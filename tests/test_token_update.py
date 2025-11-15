"""Unit tests for Token.update_from_sentence and related methods."""

import pytest
import tempfile
import os
from pathlib import Path

from oeapp.models.token import Token
from oeapp.services.db import Database


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
    temp_db.close()
    database = Database(temp_db.name)
    yield database
    database.close()
    os.unlink(temp_db.name)


@pytest.fixture
def project_and_sentence(db):
    """Create a test project and sentence."""
    cursor = db.conn.cursor()
    cursor.execute("INSERT INTO projects (name) VALUES (?)", ("Test Project",))
    project_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO sentences (project_id, display_order, text_oe) VALUES (?, ?, ?)",
        (project_id, 1, "Se cyning")
    )
    sentence_id = cursor.lastrowid
    db.conn.commit()
    return project_id, sentence_id


class TestFindMatchedTokenIds:
    """Test cases for Token._find_matched_token_ids."""

    def test_perfect_match_at_same_position(self, db, project_and_sentence):
        """Test matching tokens at the same position with same surface."""
        _, sentence_id = project_and_sentence

        # Create tokens
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        existing_tokens = Token.list(db, sentence_id)
        token_strings = ["Se", "cyning"]

        matched_ids, matched_positions = Token._find_matched_token_ids(existing_tokens, token_strings)

        assert len(matched_ids) == 2
        assert len(matched_positions) == 2
        assert 0 in matched_positions
        assert 1 in matched_positions
        assert matched_positions[0].surface == "Se"
        assert matched_positions[1].surface == "cyning"

    def test_no_match_when_surface_differs(self, db, project_and_sentence):
        """Test that tokens at same position but different surface don't match."""
        _, sentence_id = project_and_sentence

        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()

        existing_tokens = Token.list(db, sentence_id)
        token_strings = ["Þā"]

        matched_ids, matched_positions = Token._find_matched_token_ids(existing_tokens, token_strings)

        assert len(matched_ids) == 0
        assert len(matched_positions) == 0

    def test_no_match_when_position_differs(self, db, project_and_sentence):
        """Test that tokens at different positions don't match even with same surface."""
        _, sentence_id = project_and_sentence

        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()

        existing_tokens = Token.list(db, sentence_id)
        token_strings = ["cyning", "Se"]  # "Se" moved to position 1

        matched_ids, matched_positions = Token._find_matched_token_ids(existing_tokens, token_strings)

        assert len(matched_ids) == 0
        assert len(matched_positions) == 0


class TestProcessUnmatchedTokens:
    """Test cases for Token._process_unmatched_tokens."""

    def test_match_unmatched_token_by_surface(self, db, project_and_sentence):
        """Test matching an unmatched token by surface form."""
        _, sentence_id = project_and_sentence

        # Create token at position 0
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()

        existing_tokens = Token.list(db, sentence_id)
        matched_token_ids = set()
        matched_positions = {}
        token_strings = ["cyning", "Se"]  # "Se" moved to position 1

        Token._process_unmatched_tokens(
            db, existing_tokens, matched_token_ids, matched_positions,
            token_strings, sentence_id
        )

        # Should have matched "Se" and created "cyning"
        assert len(matched_positions) == 2
        assert 0 in matched_positions
        assert 1 in matched_positions
        # Position 0 should have new token "cyning"
        assert matched_positions[0].surface == "cyning"
        # Position 1 should have matched token "Se"
        assert matched_positions[1].surface == "Se"
        assert matched_positions[1].id == token1.id

    def test_create_new_token_when_no_match(self, db, project_and_sentence):
        """Test creating a new token when no match is found."""
        _, sentence_id = project_and_sentence

        existing_tokens = Token.list(db, sentence_id)
        matched_token_ids = set()
        matched_positions = {}
        token_strings = ["Se", "cyning"]

        Token._process_unmatched_tokens(
            db, existing_tokens, matched_token_ids, matched_positions,
            token_strings, sentence_id
        )

        assert len(matched_positions) == 2
        assert 0 in matched_positions
        assert 1 in matched_positions
        assert matched_positions[0].surface == "Se"
        assert matched_positions[1].surface == "cyning"
        # Both should be new tokens
        assert matched_positions[0].id is not None
        assert matched_positions[1].id is not None

    def test_handles_duplicate_tokens(self, db, project_and_sentence):
        """Test handling duplicate tokens correctly."""
        _, sentence_id = project_and_sentence

        # Create two tokens with same surface
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="þā")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="þā")
        token2.save()

        existing_tokens = Token.list(db, sentence_id)
        matched_token_ids = set()
        matched_positions = {}
        token_strings = ["þā", "cyning", "þā"]  # Reordered with new token

        Token._process_unmatched_tokens(
            db, existing_tokens, matched_token_ids, matched_positions,
            token_strings, sentence_id
        )

        # Should match two "þā" tokens and create one "cyning"
        assert len(matched_positions) == 3
        assert matched_positions[0].surface == "þā"
        assert matched_positions[1].surface == "cyning"
        assert matched_positions[2].surface == "þā"
        # Should have matched existing tokens
        assert matched_positions[0].id in [token1.id, token2.id]
        assert matched_positions[2].id in [token1.id, token2.id]
        assert matched_positions[0].id != matched_positions[2].id


class TestUpdateFromSentence:
    """Test cases for Token.update_from_sentence."""

    def test_no_changes(self, db, project_and_sentence):
        """Test updating with no changes to tokens."""
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        # Update with same text
        Token.update_from_sentence(db, "Se cyning", sentence_id)

        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 2
        assert tokens[0].surface == "Se"
        assert tokens[0].order_index == 0
        assert tokens[1].surface == "cyning"
        assert tokens[1].order_index == 1

    def test_add_new_tokens(self, db, project_and_sentence):
        """Test adding new tokens to sentence."""
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        # Add a new token
        Token.update_from_sentence(db, "Se cyning wæs", sentence_id)

        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 3
        assert tokens[0].surface == "Se"
        assert tokens[1].surface == "cyning"
        assert tokens[2].surface == "wæs"
        # Verify sequential numbering
        for i, token in enumerate(tokens):
            assert token.order_index == i

    def test_remove_tokens(self, db, project_and_sentence):
        """Test removing tokens from sentence."""
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()
        token3 = Token(db=db, id=None, sentence_id=sentence_id, order_index=2, surface="wæs")
        token3.save()

        # Remove a token
        Token.update_from_sentence(db, "Se cyning", sentence_id)

        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 2
        assert tokens[0].surface == "Se"
        assert tokens[1].surface == "cyning"
        # Verify sequential numbering
        for i, token in enumerate(tokens):
            assert token.order_index == i

    def test_reorder_tokens(self, db, project_and_sentence):
        """Test reordering tokens."""
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        # Reorder tokens
        Token.update_from_sentence(db, "cyning Se", sentence_id)

        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 2
        assert tokens[0].surface == "cyning"
        assert tokens[0].order_index == 0
        assert tokens[1].surface == "Se"
        assert tokens[1].order_index == 1

    def test_update_token_surface(self, db, project_and_sentence):
        """Test updating token surface form.

        When surface form changes, a new token is created because the algorithm
        matches by surface form. The old token is deleted if it doesn't match
        any position in the new sentence.
        """
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()
        original_token_id = token1.id

        # Update surface form - "Se" changes to "Þā"
        Token.update_from_sentence(db, "Þā cyning", sentence_id)

        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 2
        # First token should be new (surface changed, so no match)
        assert tokens[0].surface == "Þā"
        # Second token should be preserved (same surface)
        assert tokens[1].surface == "cyning"
        assert tokens[1].id == token2.id
        # Old "Se" token should be deleted (no longer in sentence)
        assert original_token_id not in [t.id for t in tokens]

    def test_complex_reordering_with_duplicates(self, db, project_and_sentence):
        """Test complex reordering with duplicate tokens."""
        _, sentence_id = project_and_sentence

        # Create tokens with duplicates manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="þā")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()
        token3 = Token(db=db, id=None, sentence_id=sentence_id, order_index=2, surface="þā")
        token3.save()
        token4 = Token(db=db, id=None, sentence_id=sentence_id, order_index=3, surface="wæs")
        token4.save()

        # Reorder and change
        Token.update_from_sentence(db, "þā wæs cyning þā", sentence_id)

        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 4
        assert tokens[0].surface == "þā"
        assert tokens[1].surface == "wæs"
        assert tokens[2].surface == "cyning"
        assert tokens[3].surface == "þā"
        # Verify sequential numbering
        for i, token in enumerate(tokens):
            assert token.order_index == i

    def test_preserve_annotations(self, db, project_and_sentence):
        """Test that token annotations are preserved when tokens are matched."""
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()
        original_token_id = token1.id

        # Add annotation
        cursor = db.conn.cursor()
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, gender, number, "case")
               VALUES (?, ?, ?, ?, ?)""",
            (token1.id, "R", "m", "s", "n")
        )
        db.conn.commit()

        # Update sentence (reorder)
        Token.update_from_sentence(db, "cyning Se", sentence_id)

        # Verify annotation still exists on the matched token
        tokens = Token.list(db, sentence_id)
        token_with_annotation = None
        for t in tokens:
            if t.id == original_token_id:
                token_with_annotation = t
                break

        assert token_with_annotation is not None
        cursor.execute(
            "SELECT pos, gender, number FROM annotations WHERE token_id = ?",
            (original_token_id,)
        )
        annotation = cursor.fetchone()
        assert annotation is not None
        assert annotation["pos"] == "R"
        assert annotation["gender"] == "m"

    def test_sequential_numbering_after_insertion(self, db, project_and_sentence):
        """Test that tokens are numbered sequentially after insertion."""
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        # Insert token in middle
        Token.update_from_sentence(db, "Se wæs cyning", sentence_id)

        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 3
        # Verify sequential numbering (0, 1, 2)
        for i, token in enumerate(tokens):
            assert token.order_index == i, f"Token at index {i} has order_index {token.order_index}, expected {i}"

    def test_sequential_numbering_after_deletion(self, db, project_and_sentence):
        """Test that tokens are numbered sequentially after deletion."""
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()
        token3 = Token(db=db, id=None, sentence_id=sentence_id, order_index=2, surface="wæs")
        token3.save()

        # Delete middle token
        Token.update_from_sentence(db, "Se wæs", sentence_id)

        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 2
        # Verify sequential numbering (0, 1)
        for i, token in enumerate(tokens):
            assert token.order_index == i, f"Token at index {i} has order_index {token.order_index}, expected {i}"

    def test_sequential_numbering_after_reorder(self, db, project_and_sentence):
        """Test that tokens are numbered sequentially after reordering."""
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()
        token3 = Token(db=db, id=None, sentence_id=sentence_id, order_index=2, surface="wæs")
        token3.save()

        # Complete reorder
        Token.update_from_sentence(db, "wæs Se cyning", sentence_id)

        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 3
        # Verify sequential numbering
        for i, token in enumerate(tokens):
            assert token.order_index == i, f"Token at index {i} has order_index {token.order_index}, expected {i}"

    def test_no_gaps_in_numbering(self, db, project_and_sentence):
        """Test that there are no gaps in token numbering."""
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()
        token3 = Token(db=db, id=None, sentence_id=sentence_id, order_index=2, surface="wæs")
        token3.save()

        # Make various changes
        Token.update_from_sentence(db, "Þā cyning", sentence_id)

        tokens = Token.list(db, sentence_id)
        order_indices = [token.order_index for token in tokens]
        order_indices.sort()

        # Should be sequential with no gaps
        assert order_indices == list(range(len(tokens)))

    def test_all_positions_filled(self, db, project_and_sentence):
        """Test that all positions are filled after update."""
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        Token.update_from_sentence(db, "Se cyning wæs þā", sentence_id)

        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 4

        # Check that we have tokens at positions 0, 1, 2, 3
        positions = {token.order_index for token in tokens}
        assert positions == {0, 1, 2, 3}

    def test_handles_empty_sentence(self, db, project_and_sentence):
        """Test updating to an empty sentence."""
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        Token.update_from_sentence(db, "", sentence_id)

        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 0

    def test_handles_single_token(self, db, project_and_sentence):
        """Test updating with a single token."""
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        Token.update_from_sentence(db, "cyning", sentence_id)

        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 1
        assert tokens[0].surface == "cyning"
        assert tokens[0].order_index == 0

    def test_multiple_updates_preserve_numbering(self, db, project_and_sentence):
        """Test that multiple sequential updates maintain proper numbering."""
        _, sentence_id = project_and_sentence

        # Create tokens manually
        token1 = Token(db=db, id=None, sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save()
        token2 = Token(db=db, id=None, sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        # First update
        Token.update_from_sentence(db, "Se cyning wæs", sentence_id)
        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 3
        for i, token in enumerate(tokens):
            assert token.order_index == i

        # Second update
        Token.update_from_sentence(db, "Þā Se cyning", sentence_id)
        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 3
        for i, token in enumerate(tokens):
            assert token.order_index == i

        # Third update
        Token.update_from_sentence(db, "Se", sentence_id)
        tokens = Token.list(db, sentence_id)
        assert len(tokens) == 1
        assert tokens[0].order_index == 0

