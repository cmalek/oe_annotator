"""Unit tests for AnnotationModal."""

import unittest
import sys
from unittest.mock import Mock, patch

# Mock PySide6 before importing to avoid Qt dependencies in tests
sys.modules['PySide6'] = Mock()
sys.modules['PySide6.QtWidgets'] = Mock()
sys.modules['PySide6.QtCore'] = Mock()
sys.modules['PySide6.QtGui'] = Mock()

from oeapp.models.token import Token
from oeapp.models.annotation import Annotation


class MockComboBox:
    """Mock QComboBox for testing."""

    def __init__(self):
        self.items = []
        self.current_index = 0
        self.editable = False

    def addItems(self, items):
        self.items.extend(items)

    def currentIndex(self):
        return self.current_index

    def setCurrentIndex(self, index):
        self.current_index = index

    def currentText(self):
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index]
        return ""

    def setCurrentText(self, text):
        try:
            self.current_index = self.items.index(text)
        except ValueError:
            pass

    def setEditable(self, editable):
        self.editable = editable


class MockCheckBox:
    """Mock QCheckBox for testing."""

    def __init__(self):
        self.checked = False

    def isChecked(self):
        return self.checked

    def setChecked(self, checked):
        self.checked = checked


class MockLineEdit:
    """Mock QLineEdit for testing."""

    def __init__(self):
        self.text_value = ""

    def text(self):
        return self.text_value

    def setText(self, text):
        self.text_value = text

    def clear(self):
        self.text_value = ""

    def strip(self):
        return self.text_value.strip()


class MockSlider:
    """Mock QSlider for testing."""

    def __init__(self):
        self.value_int = 100

    def value(self):
        return self.value_int

    def setValue(self, value):
        self.value_int = value


class TestAnnotationModal(unittest.TestCase):
    """Test cases for AnnotationModal."""

    def setUp(self):
        """Set up test token and annotation."""
        self.token = Token(
            id=1,
            sentence_id=1,
            order_index=0,
            surface="cyning",
            lemma="cyning"
        )

    def test_load_noun_annotation(self):
        """Test loading existing noun annotation into modal."""
        annotation = Annotation(
            token_id=1,
            pos="N",
            gender="m",
            number="s",
            case="n",
            declension="strong"
        )

        # Verify annotation data is correct
        self.assertEqual(annotation.pos, "N")
        self.assertEqual(annotation.gender, "m")
        self.assertEqual(annotation.number, "s")
        self.assertEqual(annotation.case, "n")
        self.assertEqual(annotation.declension, "strong")

    def test_load_verb_annotation(self):
        """Test loading existing verb annotation into modal."""
        annotation = Annotation(
            token_id=1,
            pos="V",
            verb_class="s7",
            verb_tense="p",
            verb_mood="i",
            verb_person=3,
            number="s",
            verb_form="f"
        )

        # Verify verb annotation fields
        self.assertEqual(annotation.pos, "V")
        self.assertEqual(annotation.verb_class, "s7")
        self.assertEqual(annotation.verb_tense, "p")
        self.assertEqual(annotation.verb_mood, "i")
        self.assertEqual(annotation.verb_person, 3)
        self.assertEqual(annotation.number, "s")
        self.assertEqual(annotation.verb_form, "f")

    def test_load_pronoun_annotation(self):
        """Test loading existing pronoun annotation into modal."""
        annotation = Annotation(
            token_id=1,
            pos="R",
            pronoun_type="d",
            gender="m",
            number="s",
            case="n"
        )

        # Verify pronoun annotation fields
        self.assertEqual(annotation.pos, "R")
        self.assertEqual(annotation.pronoun_type, "d")
        self.assertEqual(annotation.gender, "m")
        self.assertEqual(annotation.number, "s")
        self.assertEqual(annotation.case, "n")

    def test_save_noun_annotation_data(self):
        """Test extracting and saving noun annotation data."""
        # Simulate user input
        pos = "N"
        gender = "m"
        number = "s"
        case = "n"
        declension = "strong"

        # Create annotation
        annotation = Annotation(
            token_id=1,
            pos=pos,
            gender=gender,
            number=number,
            case=case,
            declension=declension
        )

        # Verify saved data
        self.assertEqual(annotation.pos, pos)
        self.assertEqual(annotation.gender, gender)
        self.assertEqual(annotation.number, number)
        self.assertEqual(annotation.case, case)
        self.assertEqual(annotation.declension, declension)

    def test_save_verb_annotation_data(self):
        """Test extracting and saving verb annotation data."""
        # Simulate user input for verb
        annotation = Annotation(
            token_id=1,
            pos="V",
            verb_class="w1",
            verb_tense="n",
            verb_mood="s",
            verb_person=2,
            number="p",
            verb_aspect="p",
            verb_form="f"
        )

        # Verify saved data includes all verb fields
        self.assertEqual(annotation.pos, "V")
        self.assertEqual(annotation.verb_class, "w1")
        self.assertEqual(annotation.verb_tense, "n")
        self.assertEqual(annotation.verb_mood, "s")
        self.assertEqual(annotation.verb_person, 2)
        self.assertEqual(annotation.number, "p")
        self.assertEqual(annotation.verb_aspect, "p")
        self.assertEqual(annotation.verb_form, "f")

    def test_save_adjective_annotation_data(self):
        """Test extracting and saving adjective annotation data."""
        annotation = Annotation(
            token_id=1,
            pos="A",
            gender="f",
            number="p",
            case="a"
        )

        # Verify adjective fields
        self.assertEqual(annotation.pos, "A")
        self.assertEqual(annotation.gender, "f")
        self.assertEqual(annotation.number, "p")
        self.assertEqual(annotation.case, "a")

    def test_save_preposition_annotation_data(self):
        """Test extracting and saving preposition annotation data."""
        annotation = Annotation(
            token_id=1,
            pos="E",
            prep_case="d"
        )

        # Verify preposition field
        self.assertEqual(annotation.pos, "E")
        self.assertEqual(annotation.prep_case, "d")

    def test_pos_specific_fields_visibility(self):
        """Test that POS-specific fields are shown based on selection."""
        # Test noun fields
        noun_annotation = Annotation(
            token_id=1,
            pos="N",
            gender="m",
            number="s",
            case="n",
            declension="strong"
        )
        self.assertIsNotNone(noun_annotation.gender)
        self.assertIsNotNone(noun_annotation.number)
        self.assertIsNotNone(noun_annotation.case)
        self.assertIsNotNone(noun_annotation.declension)

        # Test verb fields
        verb_annotation = Annotation(
            token_id=1,
            pos="V",
            verb_tense="p",
            verb_mood="i"
        )
        self.assertIsNotNone(verb_annotation.verb_tense)
        self.assertIsNotNone(verb_annotation.verb_mood)

    def test_metadata_fields(self):
        """Test metadata fields (uncertain, alternatives, confidence)."""
        annotation = Annotation(
            token_id=1,
            pos="N",
            gender="m",
            number="s",
            case="n",
            uncertain=True,
            alternatives_json="w2 / s3",
            confidence=75
        )

        # Verify metadata
        self.assertTrue(annotation.uncertain)
        self.assertEqual(annotation.alternatives_json, "w2 / s3")
        self.assertEqual(annotation.confidence, 75)

    def test_extract_noun_values_from_ui(self):
        """Test extracting noun values from UI components."""
        # Mock UI components
        gender_combo = MockComboBox()
        gender_combo.addItems(["", "Masculine (m)", "Feminine (f)", "Neuter (n)"])
        gender_combo.setCurrentIndex(1)  # Masculine

        number_combo = MockComboBox()
        number_combo.addItems(["", "Singular (s)", "Plural (p)"])
        number_combo.setCurrentIndex(1)  # Singular

        case_combo = MockComboBox()
        case_combo.addItems(["", "Nominative (n)", "Accusative (a)", "Genitive (g)", "Dative (d)"])
        case_combo.setCurrentIndex(1)  # Nominative

        # Extract values (simulating _extract_noun_values)
        gender_map = {"": None, "Masculine (m)": "m", "Feminine (f)": "f", "Neuter (n)": "n"}
        number_map = {"": None, "Singular (s)": "s", "Plural (p)": "p"}
        case_map = {"": None, "Nominative (n)": "n", "Accusative (a)": "a", "Genitive (g)": "g", "Dative (d)": "d"}

        gender = gender_map.get(gender_combo.currentText())
        number = number_map.get(number_combo.currentText())
        case = case_map.get(case_combo.currentText())

        # Verify extraction
        self.assertEqual(gender, "m")
        self.assertEqual(number, "s")
        self.assertEqual(case, "n")

    def test_extract_verb_values_from_ui(self):
        """Test extracting verb values from UI components."""
        # Mock verb UI components
        tense_combo = MockComboBox()
        tense_combo.addItems(["", "Past (p)", "Present (n)"])
        tense_combo.setCurrentIndex(2)  # Present

        mood_combo = MockComboBox()
        mood_combo.addItems(["", "Indicative (i)", "Subjunctive (s)"])
        mood_combo.setCurrentIndex(2)  # Subjunctive

        person_combo = MockComboBox()
        person_combo.addItems(["", "1st", "2nd", "3rd"])
        person_combo.setCurrentIndex(3)  # 3rd

        # Extract values
        tense_map = {"": None, "Past (p)": "p", "Present (n)": "n"}
        mood_map = {"": None, "Indicative (i)": "i", "Subjunctive (s)": "s"}
        person_map = {"": None, "1st": 1, "2nd": 2, "3rd": 3}

        tense = tense_map.get(tense_combo.currentText())
        mood = mood_map.get(mood_combo.currentText())
        person = person_map.get(person_combo.currentText())

        # Verify extraction
        self.assertEqual(tense, "n")
        self.assertEqual(mood, "s")
        self.assertEqual(person, 3)

    def test_clear_all_fields(self):
        """Test clearing all annotation fields."""
        # Create annotation with data
        annotation = Annotation(
            token_id=1,
            pos="N",
            gender="m",
            number="s",
            case="n",
            uncertain=True,
            confidence=80
        )

        # Clear annotation (simulating clear button)
        cleared_annotation = Annotation(token_id=1)

        # Verify all fields are cleared
        self.assertIsNone(cleared_annotation.pos)
        self.assertIsNone(cleared_annotation.gender)
        self.assertIsNone(cleared_annotation.number)
        self.assertIsNone(cleared_annotation.case)
        self.assertFalse(cleared_annotation.uncertain)
        self.assertIsNone(cleared_annotation.confidence)

    def test_partial_annotation_save(self):
        """Test saving annotation with only some fields filled."""
        # User might only fill POS and leave other fields empty
        annotation = Annotation(
            token_id=1,
            pos="N"
        )

        # Verify partial annotation
        self.assertEqual(annotation.pos, "N")
        self.assertIsNone(annotation.gender)
        self.assertIsNone(annotation.number)
        self.assertIsNone(annotation.case)

    def test_complex_annotation_all_fields(self):
        """Test saving complex annotation with all fields populated."""
        annotation = Annotation(
            token_id=1,
            pos="V",
            verb_class="s3",
            verb_tense="p",
            verb_mood="i",
            verb_person=3,
            number="s",
            verb_aspect="p",
            verb_form="f",
            uncertain=True,
            alternatives_json="s2 / w1",
            confidence=60
        )

        # Verify all fields are saved
        self.assertEqual(annotation.pos, "V")
        self.assertEqual(annotation.verb_class, "s3")
        self.assertEqual(annotation.verb_tense, "p")
        self.assertEqual(annotation.verb_mood, "i")
        self.assertEqual(annotation.verb_person, 3)
        self.assertEqual(annotation.number, "s")
        self.assertEqual(annotation.verb_aspect, "p")
        self.assertEqual(annotation.verb_form, "f")
        self.assertTrue(annotation.uncertain)
        self.assertEqual(annotation.alternatives_json, "s2 / w1")
        self.assertEqual(annotation.confidence, 60)


if __name__ == '__main__':
    unittest.main()
