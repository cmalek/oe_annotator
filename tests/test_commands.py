"""Unit tests for CommandManager and AnnotateTokenCommand."""

import unittest
import tempfile
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from oeapp.db import Base
from oeapp.services.commands import CommandManager, AnnotateTokenCommand
from oeapp.models.project import Project
from oeapp.models.sentence import Sentence
from oeapp.models.token import Token


class TestCommandManager(unittest.TestCase):
    """Test cases for CommandManager."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        db_path = Path(self.temp_db.name)

        # Create engine and session
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        self.session = SessionLocal()

        self.command_manager = CommandManager(self.session, max_commands=10)

        # Create test project and sentence
        project = Project(name="Test Project")
        self.session.add(project)
        self.session.flush()
        self.project_id = project.id

        sentence = Sentence.create(
            session=self.session,
            project_id=self.project_id,
            display_order=1,
            text_oe="Se cyning"
        )
        sentence.text_modern = "The king"
        self.session.add(sentence)
        self.session.commit()
        self.sentence_id = sentence.id

        tokens = Token.list(self.session, self.sentence_id)
        self.token_id = tokens[0].id

    def tearDown(self):
        """Clean up test database."""
        self.session.close()
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
            session=self.session,
            token_id=self.token_id,
            before=before,
            after=after
        )

        # Execute command
        result = self.command_manager.execute(command)
        self.assertTrue(result)

        # Verify annotation was created
        from oeapp.models.annotation import Annotation
        annotation = self.session.get(Annotation, self.token_id)
        self.assertIsNotNone(annotation)
        self.assertEqual(annotation.pos, "R")
        self.assertEqual(annotation.gender, "m")
        self.assertEqual(annotation.number, "s")
        self.assertEqual(annotation.case, "n")
        self.assertEqual(annotation.pronoun_type, "d")
        self.assertEqual(annotation.confidence, 95)

        # Undo command
        undo_result = self.command_manager.undo()
        self.assertTrue(undo_result)

        # Verify annotation was reset to before state (empty values)
        annotation = self.session.get(Annotation, self.token_id)
        # Annotation still exists (created automatically for tokens) but should be empty
        self.assertIsNotNone(annotation)
        self.assertIsNone(annotation.pos)
        self.assertIsNone(annotation.gender)
        self.assertIsNone(annotation.number)
        self.assertIsNone(annotation.case)
        self.assertIsNone(annotation.pronoun_type)
        self.assertIsNone(annotation.confidence)

    def test_execute_and_undo_update_annotation(self):
        """Test executing and undoing an annotation update."""
        # Get or create initial annotation (annotations are auto-created for tokens)
        from oeapp.models.annotation import Annotation
        annotation = self.session.get(Annotation, self.token_id)
        if annotation is None:
            annotation = Annotation(token_id=self.token_id)
            self.session.add(annotation)
        annotation.pos = "R"
        annotation.gender = "m"
        annotation.number = "s"
        annotation.case = "n"
        annotation.pronoun_type = "d"
        annotation.confidence = 80
        self.session.commit()

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
            session=self.session,
            token_id=self.token_id,
            before=before,
            after=after
        )

        # Execute command
        result = self.command_manager.execute(command)
        self.assertTrue(result)

        # Verify annotation was updated
        from oeapp.models.annotation import Annotation
        annotation = self.session.get(Annotation, self.token_id)
        self.assertIsNotNone(annotation)
        self.assertEqual(annotation.case, "a")
        self.assertEqual(annotation.uncertain, True)
        self.assertEqual(annotation.alternatives_json, "n")
        self.assertEqual(annotation.confidence, 60)

        # Undo command
        undo_result = self.command_manager.undo()
        self.assertTrue(undo_result)

        # Verify annotation was restored to before state
        annotation = self.session.get(Annotation, self.token_id)
        self.assertIsNotNone(annotation)
        self.assertEqual(annotation.case, "n")
        self.assertEqual(annotation.uncertain, False)
        self.assertIsNone(annotation.alternatives_json)
        self.assertEqual(annotation.confidence, 80)

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

        command = AnnotateTokenCommand(self.session, self.token_id, before, after)
        self.command_manager.execute(command)

        # Verify annotation exists
        from oeapp.models.annotation import Annotation
        annotation = self.session.get(Annotation, self.token_id)
        self.assertIsNotNone(annotation)

        # Undo
        self.command_manager.undo()
        annotation = self.session.get(Annotation, self.token_id)
        # Annotation still exists but should be empty
        self.assertIsNotNone(annotation)
        self.assertIsNone(annotation.pos)
        self.assertIsNone(annotation.gender)

        # Redo
        redo_result = self.command_manager.redo()
        self.assertTrue(redo_result)

        # Verify annotation is back
        annotation = self.session.get(Annotation, self.token_id)
        self.assertIsNotNone(annotation)
        self.assertEqual(annotation.pos, "N")
        self.assertEqual(annotation.gender, "m")

    def test_multiple_commands_undo_order(self):
        """Test that multiple commands are undone in reverse order."""
        # Get the second token (created automatically by Sentence.create)
        tokens = Token.list(self.session, self.sentence_id)
        if len(tokens) < 2:
            # Create second token if it doesn't exist
            token2 = Token(sentence_id=self.sentence_id, order_index=1, surface="cyning")
            self.session.add(token2)
            self.session.flush()
            token_id_2 = token2.id
        else:
            token_id_2 = tokens[1].id
        self.session.commit()

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

        command1 = AnnotateTokenCommand(self.session, self.token_id, before, after1)
        command2 = AnnotateTokenCommand(self.session, token_id_2, before, after2)

        self.command_manager.execute(command1)
        self.command_manager.execute(command2)

        # Both annotations should exist
        from oeapp.models.annotation import Annotation
        annotation1 = self.session.get(Annotation, self.token_id)
        self.assertEqual(annotation1.pos, "R")
        annotation2 = self.session.get(Annotation, token_id_2)
        self.assertEqual(annotation2.pos, "N")

        # Undo once - should undo second command
        self.command_manager.undo()
        annotation2 = self.session.get(Annotation, token_id_2)
        # Annotation still exists but should be empty
        self.assertIsNotNone(annotation2)
        self.assertIsNone(annotation2.pos)
        annotation1 = self.session.get(Annotation, self.token_id)
        self.assertEqual(annotation1.pos, "R")

        # Undo again - should undo first command
        self.command_manager.undo()
        annotation1 = self.session.get(Annotation, self.token_id)
        # Annotation still exists but should be empty
        self.assertIsNotNone(annotation1)
        self.assertIsNone(annotation1.pos)

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
        command = AnnotateTokenCommand(self.session, self.token_id, before, after)
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
