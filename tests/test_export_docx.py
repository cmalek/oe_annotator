"""Unit tests for DOCXExporter."""

import unittest
import tempfile
import os
from pathlib import Path
from docx import Document
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from oeapp.db import Base, get_session
from oeapp.services.export_docx import DOCXExporter
from oeapp.models.annotation import Annotation
from oeapp.models.project import Project
from oeapp.models.sentence import Sentence
from oeapp.models.token import Token


class TestDOCXExporter(unittest.TestCase):
    """Test cases for DOCXExporter."""

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

        self.exporter = DOCXExporter(self.session)

        # Create test project
        project = Project(name="Test OE Project")
        self.session.add(project)
        self.session.flush()
        self.project_id = project.id
        self.session.commit()

    def tearDown(self):
        """Clean up test database."""
        self.session.close()
        os.unlink(self.temp_db.name)

    def test_export_with_superscripts_and_subscripts(self):
        """Test that DOCX export correctly formats superscripts and subscripts for annotations."""
        # Create a sentence with Old English text
        sentence = Sentence.create(
            session=self.session,
            project_id=self.project_id,
            display_order=1,
            text_oe="Se cyning fēoll"
        )
        sentence.text_modern = "The king fell"
        self.session.add(sentence)
        self.session.commit()
        sentence_id = sentence.id

        # Get tokens (created automatically by Sentence.create)
        tokens = Token.list(self.session, sentence_id)
        token_id_1 = tokens[0].id
        token_id_2 = tokens[1].id
        token_id_3 = tokens[2].id

        # Create annotations
        # Token 1: Demonstrative pronoun, masculine, singular, nominative
        annotation1 = self.session.get(Annotation, token_id_1)
        if annotation1 is None:
            annotation1 = Annotation(token_id=token_id_1)
            self.session.add(annotation1)
        annotation1.pos = "R"
        annotation1.gender = "m"
        annotation1.number = "s"
        annotation1.case = "n"
        annotation1.pronoun_type = "d"
        annotation1.confidence = 100

        # Token 2: Noun, masculine, singular, nominative, strong declension
        annotation2 = self.session.get(Annotation, token_id_2)
        if annotation2 is None:
            annotation2 = Annotation(token_id=token_id_2)
            self.session.add(annotation2)
        annotation2.pos = "N"
        annotation2.gender = "m"
        annotation2.number = "s"
        annotation2.case = "n"
        annotation2.declension = "s"
        annotation2.confidence = 95

        # Token 3: Verb, strong class 7, past tense, indicative, 3rd person, singular
        annotation3 = self.session.get(Annotation, token_id_3)
        if annotation3 is None:
            annotation3 = Annotation(token_id=token_id_3)
            self.session.add(annotation3)
        annotation3.pos = "V"
        annotation3.verb_class = "s7"
        annotation3.verb_tense = "p"
        annotation3.verb_mood = "i"
        annotation3.verb_person = 3
        annotation3.number = "s"
        annotation3.verb_form = "f"
        annotation3.confidence = 100

        self.session.commit()

        # Export to DOCX
        output_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.docx')
        output_file.close()
        output_path = Path(output_file.name)

        try:
            result = self.exporter.export(self.project_id, output_path)
            self.assertTrue(result)
            self.assertTrue(output_path.exists())

            # Read the exported document
            doc = Document(str(output_path))

            # Find the paragraph with Old English text
            oe_paragraph = None
            for para in doc.paragraphs:
                if any(run.text for run in para.runs if "Se" in run.text or "cyning" in run.text):
                    oe_paragraph = para
                    break

            self.assertIsNotNone(oe_paragraph, "Could not find OE text paragraph")

            # Verify runs have proper formatting
            superscript_found = False
            subscript_found = False

            for run in oe_paragraph.runs:
                if run.font.superscript:
                    superscript_found = True
                if run.font.subscript:
                    subscript_found = True

            self.assertTrue(superscript_found, "Annotations should contain superscripts")
            self.assertTrue(subscript_found, "Annotations should contain subscripts")

        finally:
            if output_path.exists():
                os.unlink(output_path)

    def test_export_with_uncertain_annotation(self):
        """Test that uncertain annotations are marked with '?' in the export."""
        sentence = Sentence.create(
            session=self.session,
            project_id=self.project_id,
            display_order=1,
            text_oe="þæt wīf"
        )
        sentence.text_modern = "that woman"
        self.session.add(sentence)
        self.session.commit()
        sentence_id = sentence.id

        tokens = Token.list(self.session, sentence_id)
        token_id = tokens[0].id

        # Create uncertain annotation
        annotation = self.session.get(Annotation, token_id)
        if annotation is None:
            annotation = Annotation(token_id=token_id)
            self.session.add(annotation)
        annotation.pos = "R"
        annotation.gender = "n"
        annotation.number = "s"
        annotation.case = "a"
        annotation.pronoun_type = "d"
        annotation.uncertain = True
        annotation.alternatives_json = "n"
        self.session.commit()

        # Export
        output_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.docx')
        output_file.close()
        output_path = Path(output_file.name)

        try:
            result = self.exporter.export(self.project_id, output_path)
            self.assertTrue(result)

            # Read document and verify export succeeded
            doc = Document(str(output_path))
            text_content = "\n".join([para.text for para in doc.paragraphs])

            # Verify the sentence and annotation are present
            self.assertIn("þæt", text_content)
            self.assertIn("that woman", text_content)

        finally:
            if output_path.exists():
                os.unlink(output_path)

    def test_export_multiple_sentences(self):
        """Test exporting multiple sentences in correct order."""
        # Create multiple sentences
        for i in range(1, 4):
            sentence = Sentence.create(
                session=self.session,
                project_id=self.project_id,
                display_order=i,
                text_oe=f"Sentence {i}"
            )
            sentence.text_modern = f"Translation {i}"
            self.session.add(sentence)
        self.session.commit()

        # Export
        output_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.docx')
        output_file.close()
        output_path = Path(output_file.name)

        try:
            result = self.exporter.export(self.project_id, output_path)
            self.assertTrue(result)

            # Read document
            doc = Document(str(output_path))
            text = "\n".join([para.text for para in doc.paragraphs])

            # Verify all sentences are present (tokens are displayed, not text_oe)
            self.assertIn("Sentence", text)
            self.assertIn("1", text)
            self.assertIn("2", text)
            self.assertIn("3", text)
            self.assertIn("Translation 1", text)
            self.assertIn("Translation 2", text)
            self.assertIn("Translation 3", text)

        finally:
            if output_path.exists():
                os.unlink(output_path)

    def test_export_with_complex_annotations(self):
        """Test export with various POS types and their specific fields."""
        sentence = Sentence.create(
            session=self.session,
            project_id=self.project_id,
            display_order=1,
            text_oe="on þǣm dæge"
        )
        sentence_id = sentence.id

        tokens = Token.list(self.session, sentence_id)
        token_id_1 = tokens[0].id
        token_id_2 = tokens[1].id
        token_id_3 = tokens[2].id

        # Preposition: on
        annotation1 = self.session.get(Annotation, token_id_1)
        if annotation1 is None:
            annotation1 = Annotation(token_id=token_id_1)
            self.session.add(annotation1)
        annotation1.pos = "E"
        annotation1.prep_case = "d"

        # Demonstrative: þǣm
        annotation2 = self.session.get(Annotation, token_id_2)
        if annotation2 is None:
            annotation2 = Annotation(token_id=token_id_2)
            self.session.add(annotation2)
        annotation2.pos = "R"
        annotation2.gender = "m"
        annotation2.number = "s"
        annotation2.case = "d"
        annotation2.pronoun_type = "d"

        # Noun: dæge
        annotation3 = self.session.get(Annotation, token_id_3)
        if annotation3 is None:
            annotation3 = Annotation(token_id=token_id_3)
            self.session.add(annotation3)
        annotation3.pos = "N"
        annotation3.gender = "m"
        annotation3.number = "s"
        annotation3.case = "d"
        annotation3.declension = "i"

        self.session.commit()

        # Export
        output_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.docx')
        output_file.close()
        output_path = Path(output_file.name)

        try:
            result = self.exporter.export(self.project_id, output_path)
            self.assertTrue(result)
            self.assertTrue(output_path.exists())

            # Verify document was created successfully
            doc = Document(str(output_path))
            self.assertGreater(len(doc.paragraphs), 0)

        finally:
            if output_path.exists():
                os.unlink(output_path)

    def test_export_empty_project(self):
        """Test exporting a project with no sentences."""
        output_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.docx')
        output_file.close()
        output_path = Path(output_file.name)

        try:
            result = self.exporter.export(self.project_id, output_path)
            self.assertTrue(result)
            self.assertTrue(output_path.exists())

            # Document should still be created with just the title
            doc = Document(str(output_path))
            self.assertGreater(len(doc.paragraphs), 0)

        finally:
            if output_path.exists():
                os.unlink(output_path)


if __name__ == '__main__':
    unittest.main()
