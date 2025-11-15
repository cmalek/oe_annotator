"""Unit tests for DOCXExporter."""

import unittest
import tempfile
import os
from pathlib import Path
from docx import Document

from oeapp.services.db import Database
from oeapp.services.export_docx import DOCXExporter
from oeapp.models.annotation import Annotation


class TestDOCXExporter(unittest.TestCase):
    """Test cases for DOCXExporter."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db = Database(self.temp_db.name)
        self.exporter = DOCXExporter(self.db)

        # Create test project
        cursor = self.db.conn.cursor()
        cursor.execute("INSERT INTO projects (name) VALUES (?)", ("Test OE Project",))
        self.project_id = cursor.lastrowid
        self.db.conn.commit()

    def tearDown(self):
        """Clean up test database."""
        self.db.close()
        os.unlink(self.temp_db.name)

    def test_export_with_superscripts_and_subscripts(self):
        """Test that DOCX export correctly formats superscripts and subscripts for annotations."""
        # Create a sentence with Old English text
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT INTO sentences (project_id, display_order, text_oe, text_modern) VALUES (?, ?, ?, ?)",
            (self.project_id, 1, "Se cyning fēoll", "The king fell")
        )
        sentence_id = cursor.lastrowid

        # Create tokens
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface, lemma) VALUES (?, ?, ?, ?)",
            (sentence_id, 0, "Se", "se")
        )
        token_id_1 = cursor.lastrowid

        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface, lemma) VALUES (?, ?, ?, ?)",
            (sentence_id, 1, "cyning", "cyning")
        )
        token_id_2 = cursor.lastrowid

        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface, lemma) VALUES (?, ?, ?, ?)",
            (sentence_id, 2, "fēoll", "feallan")
        )
        token_id_3 = cursor.lastrowid

        # Create annotations
        # Token 1: Demonstrative pronoun, masculine, singular, nominative
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, gender, number, "case", pronoun_type, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (token_id_1, "R", "m", "s", "n", "d", 100)
        )

        # Token 2: Noun, masculine, singular, nominative, strong declension
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, gender, number, "case", declension, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (token_id_2, "N", "m", "s", "n", "strong", 95)
        )

        # Token 3: Verb, strong class 7, past tense, indicative, 3rd person, singular
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, verb_class, verb_tense, verb_mood,
                                       verb_person, number, verb_form, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (token_id_3, "V", "s7", "p", "i", 3, "s", "f", 100)
        )

        self.db.conn.commit()

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
            italic_found = False

            for run in oe_paragraph.runs:
                if run.font.superscript:
                    superscript_found = True
                if run.font.subscript:
                    subscript_found = True
                if run.italic:
                    italic_found = True

            self.assertTrue(italic_found, "Old English text should be italicized")
            self.assertTrue(superscript_found, "Annotations should contain superscripts")
            self.assertTrue(subscript_found, "Annotations should contain subscripts")

        finally:
            if output_path.exists():
                os.unlink(output_path)

    def test_export_with_uncertain_annotation(self):
        """Test that uncertain annotations are marked with '?' in the export."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT INTO sentences (project_id, display_order, text_oe, text_modern) VALUES (?, ?, ?, ?)",
            (self.project_id, 1, "þæt wīf", "that woman")
        )
        sentence_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (sentence_id, 0, "þæt")
        )
        token_id = cursor.lastrowid

        # Create uncertain annotation
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, gender, number, "case", pronoun_type,
                                       uncertain, alternatives_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (token_id, "R", "n", "s", "a", "d", 1, "n")
        )
        self.db.conn.commit()

        # Export
        output_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.docx')
        output_file.close()
        output_path = Path(output_file.name)

        try:
            result = self.exporter.export(self.project_id, output_path)
            self.assertTrue(result)

            # Read document and check for uncertainty marker
            doc = Document(str(output_path))
            text_content = "\n".join([para.text for para in doc.paragraphs])

            # Should contain '?' for uncertain annotation
            self.assertIn("?", text_content, "Uncertain annotations should be marked with '?'")

        finally:
            if output_path.exists():
                os.unlink(output_path)

    def test_export_multiple_sentences(self):
        """Test exporting multiple sentences in correct order."""
        cursor = self.db.conn.cursor()

        # Create multiple sentences
        for i in range(1, 4):
            cursor.execute(
                "INSERT INTO sentences (project_id, display_order, text_oe, text_modern) VALUES (?, ?, ?, ?)",
                (self.project_id, i, f"Sentence {i}", f"Translation {i}")
            )
            sentence_id = cursor.lastrowid

            # Add a token to each sentence
            cursor.execute(
                "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
                (sentence_id, 0, f"Word{i}")
            )

        self.db.conn.commit()

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
            self.assertIn("Word1", text)
            self.assertIn("Word2", text)
            self.assertIn("Word3", text)
            self.assertIn("Translation 1", text)
            self.assertIn("Translation 2", text)
            self.assertIn("Translation 3", text)

        finally:
            if output_path.exists():
                os.unlink(output_path)

    def test_export_with_complex_annotations(self):
        """Test export with various POS types and their specific fields."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT INTO sentences (project_id, display_order, text_oe) VALUES (?, ?, ?)",
            (self.project_id, 1, "on þǣm dæge")
        )
        sentence_id = cursor.lastrowid

        # Preposition: on
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (sentence_id, 0, "on")
        )
        token_id_1 = cursor.lastrowid
        cursor.execute(
            "INSERT INTO annotations (token_id, pos, prep_case) VALUES (?, ?, ?)",
            (token_id_1, "E", "d")
        )

        # Demonstrative: þǣm
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (sentence_id, 1, "þǣm")
        )
        token_id_2 = cursor.lastrowid
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, gender, number, "case", pronoun_type)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (token_id_2, "R", "m", "s", "d", "d")
        )

        # Noun: dæge
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (sentence_id, 2, "dæge")
        )
        token_id_3 = cursor.lastrowid
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, gender, number, "case", declension)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (token_id_3, "N", "m", "s", "d", "i-stem")
        )

        self.db.conn.commit()

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
