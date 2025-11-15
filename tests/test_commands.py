"""Unit tests for CommandManager and AnnotateTokenCommand."""

import unittest
import tempfile
import os
from pathlib import Path

from oeapp.services.db import Database
from oeapp.services.commands import CommandManager, AnnotateTokenCommand


class TestCommandManager(unittest.TestCase):
    """Test cases for CommandManager."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db = Database(self.temp_db.name)
        self.command_manager = CommandManager(self.db, max_commands=10)

        # Create test project and sentence
        cursor = self.db.conn.cursor()
        cursor.execute("INSERT INTO projects (name) VALUES (?)", ("Test Project",))
        self.project_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO sentences (project_id, display_order, text_oe, text_modern) VALUES (?, ?, ?, ?)",
            (self.project_id, 1, "Se cyning", "The king")
        )
        self.sentence_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface, lemma) VALUES (?, ?, ?, ?)",
            (self.sentence_id, 0, "Se", "se")
        )
        self.token_id = cursor.lastrowid
        self.db.conn.commit()

    def tearDown(self):
        """Clean up test database."""
        self.db.close()
        os.unlink(self.temp_db.name)

    def test_execute_and_undo_new_annotation(self):
        """Test executing and undoing a new annotation."""
        # Create command to add new annotation
        before = {
            "pos": None,
            "gender": None,
            "number": None,
            "case": None,
            "declension": None,
            "pronoun_type": None,
            "verb_class": None,
            "verb_tense": None,
            "verb_person": None,
            "verb_mood": None,
            "verb_aspect": None,
            "verb_form": None,
            "prep_case": None,
            "uncertain": False,
            "alternatives_json": None,
            "confidence": None,
        }
        after = {
            "pos": "R",
            "gender": "m",
            "number": "s",
            "case": "n",
            "declension": None,
            "pronoun_type": "d",
            "verb_class": None,
            "verb_tense": None,
            "verb_person": None,
            "verb_mood": None,
            "verb_aspect": None,
            "verb_form": None,
            "prep_case": None,
            "uncertain": False,
            "alternatives_json": None,
            "confidence": 95,
        }

        command = AnnotateTokenCommand(
            db=self.db,
            token_id=self.token_id,
            before=before,
            after=after
        )

        # Execute command
        result = self.command_manager.execute(command)
        self.assertTrue(result)

        # Verify annotation was created
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM annotations WHERE token_id = ?", (self.token_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["pos"], "R")
        self.assertEqual(row["gender"], "m")
        self.assertEqual(row["number"], "s")
        self.assertEqual(row["case"], "n")
        self.assertEqual(row["pronoun_type"], "d")
        self.assertEqual(row["confidence"], 95)

        # Undo command
        undo_result = self.command_manager.undo()
        self.assertTrue(undo_result)

        # Verify annotation was deleted (since before state was empty)
        cursor.execute("SELECT * FROM annotations WHERE token_id = ?", (self.token_id,))
        row = cursor.fetchone()
        self.assertIsNone(row)

    def test_execute_and_undo_update_annotation(self):
        """Test executing and undoing an annotation update."""
        # Create initial annotation
        cursor = self.db.conn.cursor()
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, gender, number, "case", pronoun_type, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (self.token_id, "R", "m", "s", "n", "d", 80)
        )
        self.db.conn.commit()

        # Create command to update annotation
        before = {
            "pos": "R",
            "gender": "m",
            "number": "s",
            "case": "n",
            "declension": None,
            "pronoun_type": "d",
            "verb_class": None,
            "verb_tense": None,
            "verb_person": None,
            "verb_mood": None,
            "verb_aspect": None,
            "verb_form": None,
            "prep_case": None,
            "uncertain": False,
            "alternatives_json": None,
            "confidence": 80,
        }
        after = {
            "pos": "R",
            "gender": "m",
            "number": "s",
            "case": "a",  # Changed from nominative to accusative
            "declension": None,
            "pronoun_type": "d",
            "verb_class": None,
            "verb_tense": None,
            "verb_person": None,
            "verb_mood": None,
            "verb_aspect": None,
            "verb_form": None,
            "prep_case": None,
            "uncertain": True,  # Now marked as uncertain
            "alternatives_json": "n",
            "confidence": 60,  # Lower confidence
        }

        command = AnnotateTokenCommand(
            db=self.db,
            token_id=self.token_id,
            before=before,
            after=after
        )

        # Execute command
        result = self.command_manager.execute(command)
        self.assertTrue(result)

        # Verify annotation was updated
        cursor.execute("SELECT * FROM annotations WHERE token_id = ?", (self.token_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["case"], "a")
        self.assertEqual(row["uncertain"], 1)
        self.assertEqual(row["alternatives_json"], "n")
        self.assertEqual(row["confidence"], 60)

        # Undo command
        undo_result = self.command_manager.undo()
        self.assertTrue(undo_result)

        # Verify annotation was restored to before state
        cursor.execute("SELECT * FROM annotations WHERE token_id = ?", (self.token_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["case"], "n")
        self.assertEqual(row["uncertain"], 0)
        self.assertIsNone(row["alternatives_json"])
        self.assertEqual(row["confidence"], 80)

    def test_redo_after_undo(self):
        """Test redo functionality after undo."""
        # Create and execute a command
        before = {"pos": None, "gender": None, "number": None, "case": None,
                  "declension": None, "pronoun_type": None, "verb_class": None,
                  "verb_tense": None, "verb_person": None, "verb_mood": None,
                  "verb_aspect": None, "verb_form": None, "prep_case": None,
                  "uncertain": False, "alternatives_json": None, "confidence": None}
        after = {"pos": "N", "gender": "m", "number": "s", "case": "n",
                 "declension": "strong", "pronoun_type": None, "verb_class": None,
                 "verb_tense": None, "verb_person": None, "verb_mood": None,
                 "verb_aspect": None, "verb_form": None, "prep_case": None,
                 "uncertain": False, "alternatives_json": None, "confidence": 100}

        command = AnnotateTokenCommand(self.db, self.token_id, before, after)
        self.command_manager.execute(command)

        # Verify annotation exists
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM annotations WHERE token_id = ?", (self.token_id,))
        self.assertIsNotNone(cursor.fetchone())

        # Undo
        self.command_manager.undo()
        cursor.execute("SELECT * FROM annotations WHERE token_id = ?", (self.token_id,))
        self.assertIsNone(cursor.fetchone())

        # Redo
        redo_result = self.command_manager.redo()
        self.assertTrue(redo_result)

        # Verify annotation is back
        cursor.execute("SELECT * FROM annotations WHERE token_id = ?", (self.token_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["pos"], "N")
        self.assertEqual(row["gender"], "m")

    def test_multiple_commands_undo_order(self):
        """Test that multiple commands are undone in reverse order."""
        # Create two tokens
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (self.sentence_id, 1, "cyning")
        )
        token_id_2 = cursor.lastrowid
        self.db.conn.commit()

        # Execute two commands
        before = {"pos": None, "gender": None, "number": None, "case": None,
                  "declension": None, "pronoun_type": None, "verb_class": None,
                  "verb_tense": None, "verb_person": None, "verb_mood": None,
                  "verb_aspect": None, "verb_form": None, "prep_case": None,
                  "uncertain": False, "alternatives_json": None, "confidence": None}

        after1 = {"pos": "R", "gender": "m", "number": "s", "case": "n",
                  "declension": None, "pronoun_type": "d", "verb_class": None,
                  "verb_tense": None, "verb_person": None, "verb_mood": None,
                  "verb_aspect": None, "verb_form": None, "prep_case": None,
                  "uncertain": False, "alternatives_json": None, "confidence": 100}

        after2 = {"pos": "N", "gender": "m", "number": "s", "case": "n",
                  "declension": "strong", "pronoun_type": None, "verb_class": None,
                  "verb_tense": None, "verb_person": None, "verb_mood": None,
                  "verb_aspect": None, "verb_form": None, "prep_case": None,
                  "uncertain": False, "alternatives_json": None, "confidence": 100}

        command1 = AnnotateTokenCommand(self.db, self.token_id, before, after1)
        command2 = AnnotateTokenCommand(self.db, token_id_2, before, after2)

        self.command_manager.execute(command1)
        self.command_manager.execute(command2)

        # Both annotations should exist
        cursor.execute("SELECT pos FROM annotations WHERE token_id = ?", (self.token_id,))
        self.assertEqual(cursor.fetchone()["pos"], "R")
        cursor.execute("SELECT pos FROM annotations WHERE token_id = ?", (token_id_2,))
        self.assertEqual(cursor.fetchone()["pos"], "N")

        # Undo once - should undo second command
        self.command_manager.undo()
        cursor.execute("SELECT * FROM annotations WHERE token_id = ?", (token_id_2,))
        self.assertIsNone(cursor.fetchone())
        cursor.execute("SELECT pos FROM annotations WHERE token_id = ?", (self.token_id,))
        self.assertEqual(cursor.fetchone()["pos"], "R")

        # Undo again - should undo first command
        self.command_manager.undo()
        cursor.execute("SELECT * FROM annotations WHERE token_id = ?", (self.token_id,))
        self.assertIsNone(cursor.fetchone())

    def test_can_undo_can_redo(self):
        """Test can_undo and can_redo state tracking."""
        self.assertFalse(self.command_manager.can_undo())
        self.assertFalse(self.command_manager.can_redo())

        # Execute a command
        before = {"pos": None, "gender": None, "number": None, "case": None,
                  "declension": None, "pronoun_type": None, "verb_class": None,
                  "verb_tense": None, "verb_person": None, "verb_mood": None,
                  "verb_aspect": None, "verb_form": None, "prep_case": None,
                  "uncertain": False, "alternatives_json": None, "confidence": None}
        after = {"pos": "N", "gender": "m", "number": "s", "case": "n",
                 "declension": None, "pronoun_type": None, "verb_class": None,
                 "verb_tense": None, "verb_person": None, "verb_mood": None,
                 "verb_aspect": None, "verb_form": None, "prep_case": None,
                 "uncertain": False, "alternatives_json": None, "confidence": 100}
        command = AnnotateTokenCommand(self.db, self.token_id, before, after)
        self.command_manager.execute(command)

        self.assertTrue(self.command_manager.can_undo())
        self.assertFalse(self.command_manager.can_redo())

        # Undo
        self.command_manager.undo()
        self.assertFalse(self.command_manager.can_undo())
        self.assertTrue(self.command_manager.can_redo())

        # Redo
        self.command_manager.redo()
        self.assertTrue(self.command_manager.can_undo())
        self.assertFalse(self.command_manager.can_redo())


if __name__ == '__main__':
    unittest.main()
