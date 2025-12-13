"""Unit tests for CommandManager and AnnotateTokenCommand."""

import unittest
import tempfile
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from oeapp.db import Base
from oeapp.services.commands import (
    AddNoteCommand,
    CommandManager,
    AnnotateTokenCommand,
    UpdateNoteCommand,
    DeleteNoteCommand,
    ToggleParagraphStartCommand,
)
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


class TestAddNoteCommand(unittest.TestCase):
    """Test cases for AddNoteCommand."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        db_path = Path(self.temp_db.name)

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        self.session = SessionLocal()

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
        self.session.commit()
        self.sentence_id = sentence.id

        tokens = Token.list(self.session, self.sentence_id)
        self.start_token_id = tokens[0].id
        self.end_token_id = tokens[1].id if len(tokens) > 1 else tokens[0].id

    def tearDown(self):
        """Clean up test database."""
        self.session.close()
        os.unlink(self.temp_db.name)

    def test_execute_creates_note(self):
        """Test execute() creates note."""
        command = AddNoteCommand(
            session=self.session,
            sentence_id=self.sentence_id,
            start_token_id=self.start_token_id,
            end_token_id=self.end_token_id,
            note_text="Test note"
        )

        result = command.execute()

        self.assertTrue(result)
        self.assertIsNotNone(command.note_id)

        from oeapp.models.note import Note
        note = Note.get(self.session, command.note_id)
        self.assertIsNotNone(note)
        self.assertEqual(note.note_text_md, "Test note")

    def test_undo_deletes_note(self):
        """Test undo() deletes note."""
        command = AddNoteCommand(
            session=self.session,
            sentence_id=self.sentence_id,
            start_token_id=self.start_token_id,
            end_token_id=self.end_token_id,
            note_text="Test note"
        )
        command.execute()
        note_id = command.note_id

        result = command.undo()

        self.assertTrue(result)
        from oeapp.models.note import Note
        note = Note.get(self.session, note_id)
        self.assertIsNone(note)


class TestUpdateNoteCommand(unittest.TestCase):
    """Test cases for UpdateNoteCommand."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        db_path = Path(self.temp_db.name)

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        self.session = SessionLocal()

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
        self.session.commit()
        self.sentence_id = sentence.id

        tokens = Token.list(self.session, self.sentence_id)
        self.token_id = tokens[0].id

        # Create a note
        from oeapp.models.note import Note
        note = Note(
            sentence_id=self.sentence_id,
            start_token=self.token_id,
            end_token=self.token_id,
            note_text_md="Original note"
        )
        self.session.add(note)
        self.session.commit()
        self.note_id = note.id

    def tearDown(self):
        """Clean up test database."""
        self.session.close()
        os.unlink(self.temp_db.name)

    def test_execute_updates_note(self):
        """Test execute() updates note."""
        from oeapp.models.note import Note
        note = Note.get(self.session, self.note_id)
        original_text = note.note_text_md

        command = UpdateNoteCommand(
            session=self.session,
            note_id=self.note_id,
            before_text=original_text,
            after_text="Updated note",
            before_start_token=self.token_id,
            before_end_token=self.token_id,
            after_start_token=self.token_id,
            after_end_token=self.token_id
        )

        result = command.execute()

        self.assertTrue(result)
        note = Note.get(self.session, self.note_id)
        self.assertEqual(note.note_text_md, "Updated note")

    def test_undo_restores_note(self):
        """Test undo() restores original note text."""
        from oeapp.models.note import Note
        note = Note.get(self.session, self.note_id)
        original_text = note.note_text_md

        command = UpdateNoteCommand(
            session=self.session,
            note_id=self.note_id,
            before_text=original_text,
            after_text="Updated note",
            before_start_token=self.token_id,
            before_end_token=self.token_id,
            after_start_token=self.token_id,
            after_end_token=self.token_id
        )
        command.execute()

        result = command.undo()

        self.assertTrue(result)
        note = Note.get(self.session, self.note_id)
        self.assertEqual(note.note_text_md, original_text)


class TestDeleteNoteCommand(unittest.TestCase):
    """Test cases for DeleteNoteCommand."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        db_path = Path(self.temp_db.name)

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        self.session = SessionLocal()

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
        self.session.commit()
        self.sentence_id = sentence.id

        tokens = Token.list(self.session, self.sentence_id)
        self.token_id = tokens[0].id

        # Create a note
        from oeapp.models.note import Note
        note = Note(
            sentence_id=self.sentence_id,
            start_token=self.token_id,
            end_token=self.token_id,
            note_text_md="Note to delete"
        )
        self.session.add(note)
        self.session.commit()
        self.note_id = note.id

    def tearDown(self):
        """Clean up test database."""
        self.session.close()
        os.unlink(self.temp_db.name)

    def test_execute_deletes_note(self):
        """Test execute() deletes note."""
        command = DeleteNoteCommand(
            session=self.session,
            note_id=self.note_id
        )

        result = command.execute()

        self.assertTrue(result)
        from oeapp.models.note import Note
        note = Note.get(self.session, self.note_id)
        self.assertIsNone(note)

    def test_undo_restores_note(self):
        """Test undo() restores deleted note."""
        command = DeleteNoteCommand(
            session=self.session,
            note_id=self.note_id
        )
        command.execute()

        result = command.undo()

        self.assertTrue(result)
        from oeapp.models.note import Note
        note = Note.get(self.session, self.note_id)
        self.assertIsNotNone(note)
        self.assertEqual(note.note_text_md, "Note to delete")


class TestToggleParagraphStartCommand(unittest.TestCase):
    """Test cases for ToggleParagraphStartCommand."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        db_path = Path(self.temp_db.name)

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        self.session = SessionLocal()

        # Create test project and sentence
        project = Project(name="Test Project")
        self.session.add(project)
        self.session.flush()
        self.project_id = project.id

        sentence = Sentence.create(
            session=self.session,
            project_id=self.project_id,
            display_order=1,
            text_oe="Se cyning",
            is_paragraph_start=False
        )
        self.session.commit()
        self.sentence_id = sentence.id

    def tearDown(self):
        """Clean up test database."""
        self.session.close()
        os.unlink(self.temp_db.name)

    def test_execute_toggles_flag(self):
        """Test execute() toggles is_paragraph_start flag."""
        command = ToggleParagraphStartCommand(
            session=self.session,
            sentence_id=self.sentence_id
        )

        sentence = Sentence.get(self.session, self.sentence_id)
        original_value = sentence.is_paragraph_start

        result = command.execute()

        self.assertTrue(result)
        self.session.refresh(sentence)
        self.assertNotEqual(sentence.is_paragraph_start, original_value)

    def test_undo_restores_flag(self):
        """Test undo() restores original is_paragraph_start flag."""
        command = ToggleParagraphStartCommand(
            session=self.session,
            sentence_id=self.sentence_id
        )

        sentence = Sentence.get(self.session, self.sentence_id)
        original_value = sentence.is_paragraph_start

        command.execute()
        command.undo()

        self.session.refresh(sentence)
        self.assertEqual(sentence.is_paragraph_start, original_value)


if __name__ == '__main__':
    unittest.main()
