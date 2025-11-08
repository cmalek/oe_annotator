"""Annotation modal dialog."""

from typing import TYPE_CHECKING, ClassVar

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from src.oeapp.models.annotation import Annotation

if TYPE_CHECKING:
    from src.oeapp.models.token import Token


class AnnotationModal(QDialog):
    """Modal dialog for annotating tokens with prompt-based entry."""

    annotation_applied = Signal(Annotation)

    # Class-level state to remember last used values per POS type
    _last_values: ClassVar[dict[str, dict]] = {}

    def __init__(
        self,
        token: Token,
        annotation: Annotation | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """
        Initialize annotation modal.

        Args:
            token: Token to annotate

        Keyword Args:
            annotation: Existing annotation (if any)
            parent: Parent widget

        """
        super().__init__(parent)
        self.token = token
        self.annotation = annotation or Annotation(token_id=token.id)
        self.fields_widget: QWidget | None = None
        self._setup_ui()
        self._setup_keyboard_shortcuts()
        self._load_existing_annotation()

    def _setup_ui(self):
        """
        Set up the UI layout.

        """
        self.setWindowTitle(f"Annotate: {self.token.surface}")
        self.setModal(True)
        self.resize(500, 600)

        layout = QVBoxLayout(self)

        # Header: Current token word and POS status
        header_label = QLabel(f"Token: <b>{self.token.surface}</b>")
        header_label.setFont(self.font())
        layout.addWidget(header_label)

        self.status_label = QLabel("POS: Not set")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)

        layout.addSpacing(10)

        # POS Selection
        pos_group = QGroupBox("Part of Speech")
        pos_layout = QVBoxLayout()
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(
            [
                "",
                "Noun (N)",
                "Verb (V)",
                "Adjective (A)",
                "Pronoun (R)",
                "Determiner/Article (D)",
                "Adverb (B)",
                "Conjunction (C)",
                "Preposition (E)",
                "Interjection (I)",
            ]
        )
        self.pos_combo.currentIndexChanged.connect(self._on_pos_changed)
        pos_layout.addWidget(self.pos_combo)
        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)

        # Dynamic fields section
        self.fields_group = QGroupBox("Annotation Fields")
        self.fields_layout = QFormLayout()
        self.fields_widget = QWidget()
        self.fields_widget.setLayout(self.fields_layout)
        self.fields_group.setLayout(QVBoxLayout())
        self.fields_group.layout().addWidget(self.fields_widget)
        layout.addWidget(self.fields_group)

        # Metadata section
        metadata_group = QGroupBox("Metadata")
        metadata_layout = QVBoxLayout()

        self.uncertain_check = QCheckBox("Uncertain (?)")
        metadata_layout.addWidget(self.uncertain_check)

        alternatives_layout = QHBoxLayout()
        alternatives_layout.addWidget(QLabel("Alternatives:"))
        self.alternatives_edit = QLineEdit()
        self.alternatives_edit.setPlaceholderText("e.g., w2 / s3")
        alternatives_layout.addWidget(self.alternatives_edit)
        metadata_layout.addLayout(alternatives_layout)

        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Confidence:"))
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(0, 100)
        self.confidence_slider.setValue(100)
        self.confidence_label = QLabel("100%")
        self.confidence_slider.valueChanged.connect(
            lambda v: self.confidence_label.setText(f"{v}%")
        )
        confidence_layout.addWidget(self.confidence_slider)
        confidence_layout.addWidget(self.confidence_label)
        metadata_layout.addLayout(confidence_layout)

        self.todo_check = QCheckBox("TODO (needs review)")
        metadata_layout.addWidget(self.todo_check)

        metadata_group.setLayout(metadata_layout)
        layout.addWidget(metadata_group)

        layout.addStretch()

        # Action buttons
        button_layout = QHBoxLayout()
        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self._clear_all)
        button_layout.addWidget(self.clear_button)

        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.apply_button = QPushButton("Apply")
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(self._apply_annotation)
        button_layout.addWidget(self.apply_button)

        layout.addLayout(button_layout)

        # Keyboard shortcuts will be set up in _setup_keyboard_shortcuts()

    def _setup_keyboard_shortcuts(self) -> None:
        """
        Set up keyboard shortcuts for the modal.
        """
        # Escape to cancel
        QShortcut(QKeySequence("Escape"), self).activated.connect(self.reject)
        # Enter/Return to apply
        QShortcut(QKeySequence("Return"), self).activated.connect(
            self._apply_annotation
        )
        # Enter to apply
        QShortcut(QKeySequence("Enter"), self).activated.connect(self._apply_annotation)

        # POS selection shortcuts: N/V/A/R/D/B/C/E/I
        QShortcut(QKeySequence("N"), self).activated.connect(
            lambda: self._select_pos_by_key("N")
        )
        # V to select POS (Verb)
        QShortcut(QKeySequence("V"), self).activated.connect(
            lambda: self._select_pos_by_key("V")
        )
        # A to select POS (Adjective)
        QShortcut(QKeySequence("A"), self).activated.connect(
            lambda: self._select_pos_by_key("A")
        )
        # R to select POS (Pronoun)
        QShortcut(QKeySequence("R"), self).activated.connect(
            lambda: self._select_pos_by_key("R")
        )
        # D to select POS (Determiner/Article)
        QShortcut(QKeySequence("D"), self).activated.connect(
            lambda: self._select_pos_by_key("D")
        )
        # B to select POS (Adverb)
        QShortcut(QKeySequence("B"), self).activated.connect(
            lambda: self._select_pos_by_key("B")
        )
        # C to select POS (Conjunction)
        QShortcut(QKeySequence("C"), self).activated.connect(
            lambda: self._select_pos_by_key("C")
        )
        # E to select POS (Preposition)
        QShortcut(QKeySequence("E"), self).activated.connect(
            lambda: self._select_pos_by_key("E")
        )
        # I to select POS (Interjection)
        QShortcut(QKeySequence("I"), self).activated.connect(
            lambda: self._select_pos_by_key("I")
        )

        # Tab navigation
        # Tab handling is automatic in Qt, but we can add Shift+Tab if needed

    def _select_pos_by_key(self, pos_key: str):
        """
        Select POS by keyboard shortcut.

        Args:
            pos_key: POS key (N, V, A, R, D, B, C, E, I)

        """
        pos_map = {
            "N": "Noun (N)",
            "V": "Verb (V)",
            "A": "Adjective (A)",
            "R": "Pronoun (R)",
            "D": "Determiner/Article (D)",
            "B": "Adverb (B)",
            "C": "Conjunction (C)",
            "E": "Preposition (E)",
            "I": "Interjection (I)",
        }
        pos_text = pos_map.get(pos_key)
        if pos_text:
            index = self.pos_combo.findText(pos_text)
            if index >= 0:
                self.pos_combo.setCurrentIndex(index)

    def _on_pos_changed(self) -> None:
        """
        Handle POS selection change.
        """
        # Clear existing fields
        while self.fields_layout.rowCount() > 0:
            self.fields_layout.removeRow(0)

        pos_map = {
            "": None,
            "Noun (N)": "N",
            "Verb (V)": "V",
            "Adjective (A)": "A",
            "Pronoun (R)": "R",
            "Determiner/Article (D)": "D",
            "Adverb (B)": "B",
            "Conjunction (C)": "C",
            "Preposition (E)": "E",
            "Interjection (I)": "I",
        }
        pos = pos_map[self.pos_combo.currentText()]

        if pos == "N":  # Noun
            self._add_noun_fields()
            self._restore_last_values("N")
        elif pos == "V":  # Verb
            self._add_verb_fields()
            self._restore_last_values("V")
        elif pos == "A":  # Adjective
            self._add_adjective_fields()
            self._restore_last_values("A")
        elif pos == "R":  # Pronoun
            self._add_pronoun_fields()
            self._restore_last_values("R")
        elif pos == "E":  # Preposition
            self._add_preposition_fields()
            self._restore_last_values("E")
        elif pos == "B":  # Adverb
            self._add_adverb_fields()
            self._restore_last_values("B")

        self._update_status_label()

    def _restore_last_values(self, pos: str) -> None:  # noqa: PLR0912
        """
        Restore last used values for a POS type.

        Args:
            pos: POS type code

        """
        if pos not in self._last_values:
            return

        last_vals = self._last_values[pos]

        # Restore values based on POS
        if pos == "N" and hasattr(self, "gender_combo"):
            if "gender" in last_vals:
                self.gender_combo.setCurrentIndex(last_vals["gender"])
            if "number" in last_vals:
                self.number_combo.setCurrentIndex(last_vals["number"])
            if "case" in last_vals:
                self.case_combo.setCurrentIndex(last_vals["case"])
            if "declension" in last_vals:
                self.declension_combo.setCurrentText(last_vals["declension"])
        elif pos == "V" and hasattr(self, "verb_class_combo"):
            if "verb_class" in last_vals:
                self.verb_class_combo.setCurrentText(last_vals["verb_class"])
            if "verb_tense" in last_vals:
                self.verb_tense_combo.setCurrentIndex(last_vals["verb_tense"])
            if "verb_mood" in last_vals:
                self.verb_mood_combo.setCurrentIndex(last_vals["verb_mood"])
            if "verb_person" in last_vals:
                self.verb_person_combo.setCurrentIndex(last_vals["verb_person"])
            if "verb_number" in last_vals:
                self.verb_number_combo.setCurrentIndex(last_vals["verb_number"])
            if "verb_aspect" in last_vals:
                self.verb_aspect_combo.setCurrentIndex(last_vals["verb_aspect"])
            if "verb_form" in last_vals:
                self.verb_form_combo.setCurrentIndex(last_vals["verb_form"])

    def _save_current_values(self, pos: str) -> None:
        """
        Save current values for a POS type.

        Args:
            pos: POS type code

        """
        if pos not in self._last_values:
            self._last_values[pos] = {}

        if pos == "N" and hasattr(self, "gender_combo"):
            self._last_values[pos]["gender"] = self.gender_combo.currentIndex()
            self._last_values[pos]["number"] = self.number_combo.currentIndex()
            self._last_values[pos]["case"] = self.case_combo.currentIndex()
            self._last_values[pos]["declension"] = self.declension_combo.currentText()
        elif pos == "V" and hasattr(self, "verb_class_combo"):
            self._last_values[pos]["verb_class"] = self.verb_class_combo.currentText()
            self._last_values[pos]["verb_tense"] = self.verb_tense_combo.currentIndex()
            self._last_values[pos]["verb_mood"] = self.verb_mood_combo.currentIndex()
            self._last_values[pos]["verb_person"] = (
                self.verb_person_combo.currentIndex()
            )
            self._last_values[pos]["verb_number"] = (
                self.verb_number_combo.currentIndex()
            )
            self._last_values[pos]["verb_aspect"] = (
                self.verb_aspect_combo.currentIndex()
            )
            self._last_values[pos]["verb_form"] = self.verb_form_combo.currentIndex()
        # Add similar for other POS types...

    def _add_noun_fields(self) -> None:
        """Add fields for noun annotation."""
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["", "Masculine (m)", "Feminine (f)", "Neuter (n)"])
        self.fields_layout.addRow("Gender:", self.gender_combo)

        self.number_combo = QComboBox()
        self.number_combo.addItems(["", "Singular (s)", "Plural (p)"])
        self.fields_layout.addRow("Number:", self.number_combo)

        self.case_combo = QComboBox()
        self.case_combo.addItems(
            [
                "",
                "Nominative (n)",
                "Accusative (a)",
                "Genitive (g)",
                "Dative (d)",
                "Instrumental (i)",
            ]
        )
        self.fields_layout.addRow("Case:", self.case_combo)

        self.declension_combo = QComboBox()
        self.declension_combo.setEditable(True)
        self.declension_combo.addItems(
            [
                "",
                "strong",
                "weak",
                "o-stem",
                "i-stem",
                "u-stem",
                "ja-stem",
                "jo-stem",
                "wa-stem",
                "wo-stem",
            ]
        )
        self.fields_layout.addRow("Declension:", self.declension_combo)

    def _add_verb_fields(self) -> None:
        """Add fields for verb annotation."""
        self.verb_class_combo = QComboBox()
        self.verb_class_combo.setEditable(True)
        self.verb_class_combo.addItems(
            [
                "",
                "Weak I (w1)",
                "Weak II (w2)",
                "Weak III (w3)",
                "Strong I (s1)",
                "Strong II (s2)",
                "Strong III (s3)",
                "Strong IV (s4)",
                "Strong V (s5)",
                "Strong VI (s6)",
                "Strong VII (s7)",
            ]
        )
        self.fields_layout.addRow("Class:", self.verb_class_combo)

        self.verb_tense_combo = QComboBox()
        self.verb_tense_combo.addItems(["", "Past (p)", "Present (n)"])
        self.fields_layout.addRow("Tense:", self.verb_tense_combo)

        self.verb_mood_combo = QComboBox()
        self.verb_mood_combo.addItems(
            ["", "Indicative (i)", "Subjunctive (s)", "Imperative (imp)"]
        )
        self.fields_layout.addRow("Mood:", self.verb_mood_combo)

        self.verb_person_combo = QComboBox()
        self.verb_person_combo.addItems(["", "1st", "2nd", "3rd"])
        self.fields_layout.addRow("Person:", self.verb_person_combo)

        self.verb_number_combo = QComboBox()
        self.verb_number_combo.addItems(["", "Singular (s)", "Plural (p)"])
        self.fields_layout.addRow("Number:", self.verb_number_combo)

        self.verb_aspect_combo = QComboBox()
        self.verb_aspect_combo.addItems(
            ["", "Perfect (p)", "Progressive (prg)", "Gnomic (gn)"]
        )
        self.fields_layout.addRow("Aspect:", self.verb_aspect_combo)

        self.verb_form_combo = QComboBox()
        self.verb_form_combo.addItems(
            ["", "Finite (f)", "Infinitive (i)", "Participle (p)"]
        )
        self.fields_layout.addRow("Form:", self.verb_form_combo)

    def _add_adjective_fields(self) -> None:
        """Add fields for adjective annotation."""
        self.adj_degree_combo = QComboBox()
        self.adj_degree_combo.addItems(
            ["", "Positive (p)", "Comparative (c)", "Superlative (s)"]
        )
        self.fields_layout.addRow("Degree:", self.adj_degree_combo)

        self.adj_inflection_combo = QComboBox()
        self.adj_inflection_combo.addItems(["", "Strong (s)", "Weak (w)"])
        self.fields_layout.addRow("Inflection:", self.adj_inflection_combo)

        self.adj_gender_combo = QComboBox()
        self.adj_gender_combo.addItems(
            ["", "Masculine (m)", "Feminine (f)", "Neuter (n)"]
        )
        self.fields_layout.addRow("Gender:", self.adj_gender_combo)

        self.adj_number_combo = QComboBox()
        self.adj_number_combo.addItems(["", "Singular (s)", "Plural (p)"])
        self.fields_layout.addRow("Number:", self.adj_number_combo)

        self.adj_case_combo = QComboBox()
        self.adj_case_combo.addItems(
            [
                "",
                "Nominative (n)",
                "Accusative (a)",
                "Genitive (g)",
                "Dative (d)",
                "Instrumental (i)",
            ]
        )
        self.fields_layout.addRow("Case:", self.adj_case_combo)

    def _add_pronoun_fields(self) -> None:
        """Add fields for pronoun annotation."""
        self.pro_type_combo = QComboBox()
        self.pro_type_combo.addItems(
            [
                "",
                "Personal (p)",
                "Relative (r)",
                "Demonstrative (d)",
                "Interrogative (i)",
            ]
        )
        self.fields_layout.addRow("Type:", self.pro_type_combo)

        self.pro_gender_combo = QComboBox()
        self.pro_gender_combo.addItems(
            ["", "Masculine (m)", "Feminine (f)", "Neuter (n)"]
        )
        self.fields_layout.addRow("Gender:", self.pro_gender_combo)

        self.pro_number_combo = QComboBox()
        self.pro_number_combo.addItems(["", "Singular (s)", "Plural (p)"])
        self.fields_layout.addRow("Number:", self.pro_number_combo)

        self.pro_case_combo = QComboBox()
        self.pro_case_combo.addItems(
            [
                "",
                "Nominative (n)",
                "Accusative (a)",
                "Genitive (g)",
                "Dative (d)",
                "Instrumental (i)",
            ]
        )
        self.fields_layout.addRow("Case:", self.pro_case_combo)

    def _add_preposition_fields(self) -> None:
        """Add fields for preposition annotation."""
        self.prep_case_combo = QComboBox()
        self.prep_case_combo.addItems(
            ["", "Accusative (a)", "Dative (d)", "Genitive (g)"]
        )
        self.fields_layout.addRow("Governed Case:", self.prep_case_combo)

    def _add_adverb_fields(self) -> None:
        """Add fields for adverb annotation."""
        self.adv_degree_combo = QComboBox()
        self.adv_degree_combo.addItems(
            ["", "Positive (p)", "Comparative (c)", "Superlative (s)"]
        )
        self.fields_layout.addRow("Degree:", self.adv_degree_combo)

    def _load_existing_annotation(self) -> None:
        """Load existing annotation values into the form."""
        if not self.annotation.pos:
            return

        # Set POS
        pos_map = {
            None: 0,
            "N": 1,
            "V": 2,
            "A": 3,
            "R": 4,
            "D": 5,
            "B": 6,
            "C": 7,
            "E": 8,
            "I": 9,
        }
        self.pos_combo.setCurrentIndex(pos_map.get(self.annotation.pos, 0))

        # Trigger field creation
        self._on_pos_changed(self.pos_combo.currentIndex())

        # Load values based on POS
        if self.annotation.pos == "N":
            self._load_noun_values()
        elif self.annotation.pos == "V":
            self._load_verb_values()
        elif self.annotation.pos == "A":
            self._load_adjective_values()
        elif self.annotation.pos == "R":
            self._load_pronoun_values()
        elif self.annotation.pos == "E":
            self._load_preposition_values()
        elif self.annotation.pos == "B":
            self._load_adverb_values()

        # Load metadata
        self.uncertain_check.setChecked(self.annotation.uncertain)
        if self.annotation.alternatives_json:
            self.alternatives_edit.setText(self.annotation.alternatives_json)
        if self.annotation.confidence is not None:
            self.confidence_slider.setValue(self.annotation.confidence)

    def _load_noun_values(self) -> None:
        """Load noun annotation values."""
        gender_map = {"m": 1, "f": 2, "n": 3}
        if self.annotation.gender:
            self.gender_combo.setCurrentIndex(gender_map.get(self.annotation.gender, 0))
        number_map = {"s": 1, "p": 2}
        if self.annotation.number:
            self.number_combo.setCurrentIndex(number_map.get(self.annotation.number, 0))
        case_map = {"n": 1, "a": 2, "g": 3, "d": 4, "i": 5}
        if self.annotation.case:
            self.case_combo.setCurrentIndex(case_map.get(self.annotation.case, 0))
        if self.annotation.declension:
            self.declension_combo.setCurrentText(self.annotation.declension)

    def _load_verb_values(self) -> None:
        """Load verb annotation values."""
        if self.annotation.verb_class:
            # Try to find matching class
            for i in range(self.verb_class_combo.count()):
                if self.annotation.verb_class in self.verb_class_combo.itemText(i):
                    self.verb_class_combo.setCurrentIndex(i)
                    break
            else:
                self.verb_class_combo.setCurrentText(self.annotation.verb_class)
        tense_map = {"p": 1, "n": 2}
        if self.annotation.verb_tense:
            self.verb_tense_combo.setCurrentIndex(
                tense_map.get(self.annotation.verb_tense, 0)
            )
        mood_map = {"i": 1, "s": 2, "imp": 3}
        if self.annotation.verb_mood:
            self.verb_mood_combo.setCurrentIndex(
                mood_map.get(self.annotation.verb_mood, 0)
            )
        person_map = {1: 1, 2: 2, 3: 3}
        if self.annotation.verb_person:
            self.verb_person_combo.setCurrentIndex(
                person_map.get(self.annotation.verb_person, 0)
            )
        number_map = {"s": 1, "p": 2}
        if self.annotation.number:
            self.verb_number_combo.setCurrentIndex(
                number_map.get(self.annotation.number, 0)
            )
        if self.annotation.verb_aspect:
            aspect_map = {"p": 1, "prg": 2, "gn": 3}
            self.verb_aspect_combo.setCurrentIndex(
                aspect_map.get(self.annotation.verb_aspect, 0)
            )
        form_map = {"f": 1, "i": 2, "p": 3}
        if self.annotation.verb_form:
            self.verb_form_combo.setCurrentIndex(
                form_map.get(self.annotation.verb_form, 0)
            )

    def _load_adjective_values(self) -> None:
        """Load adjective annotation values."""
        if self.annotation.verb_aspect:  # Reusing field for degree
            degree_map = {"p": 1, "c": 2, "s": 3}
            self.adj_degree_combo.setCurrentIndex(
                degree_map.get(self.annotation.verb_aspect, 0)
            )
        # Note: verb_aspect was used incorrectly above, need proper field
        if self.annotation.gender:
            gender_map = {"m": 1, "f": 2, "n": 3}
            self.adj_gender_combo.setCurrentIndex(
                gender_map.get(self.annotation.gender, 0)
            )
        if self.annotation.number:
            number_map = {"s": 1, "p": 2}
            self.adj_number_combo.setCurrentIndex(
                number_map.get(self.annotation.number, 0)
            )
        if self.annotation.case:
            case_map = {"n": 1, "a": 2, "g": 3, "d": 4, "i": 5}
            self.adj_case_combo.setCurrentIndex(case_map.get(self.annotation.case, 0))

    def _load_pronoun_values(self):
        """Load pronoun annotation values."""
        type_map = {"p": 1, "r": 2, "d": 3, "i": 4}
        if self.annotation.pronoun_type:
            self.pro_type_combo.setCurrentIndex(
                type_map.get(self.annotation.pronoun_type, 0)
            )
        if self.annotation.gender:
            gender_map = {"m": 1, "f": 2, "n": 3}
            self.pro_gender_combo.setCurrentIndex(
                gender_map.get(self.annotation.gender, 0)
            )
        if self.annotation.number:
            number_map = {"s": 1, "p": 2}
            self.pro_number_combo.setCurrentIndex(
                number_map.get(self.annotation.number, 0)
            )
        if self.annotation.case:
            case_map = {"n": 1, "a": 2, "g": 3, "d": 4, "i": 5}
            self.pro_case_combo.setCurrentIndex(case_map.get(self.annotation.case, 0))

    def _load_preposition_values(self):
        """Load preposition annotation values."""
        case_map = {"a": 1, "d": 2, "g": 3}
        if self.annotation.prep_case:
            self.prep_case_combo.setCurrentIndex(
                case_map.get(self.annotation.prep_case, 0)
            )

    def _load_adverb_values(self):
        """Load adverb annotation values."""
        # Adverbs don't have many fields in the current model

    def _update_status_label(self):
        """Update status label with current annotation summary."""
        pos_text = self.pos_combo.currentText()
        if not pos_text:
            self.status_label.setText("POS: Not set")
            return

        pos_map = {
            "Noun (N)": "N",
            "Verb (V)": "V",
            "Adjective (A)": "A",
            "Pronoun (R)": "R",
            "Determiner/Article (D)": "D",
            "Adverb (B)": "B",
            "Conjunction (C)": "C",
            "Preposition (E)": "E",
            "Interjection (I)": "I",
        }
        pos = pos_map[pos_text]

        summary_parts = [pos_text]
        # Add summary based on POS
        if hasattr(self, "gender_combo") and self.gender_combo.currentIndex() > 0:
            summary_parts.append(self.gender_combo.currentText())
        if hasattr(self, "number_combo") and self.number_combo.currentIndex() > 0:
            summary_parts.append(self.number_combo.currentText())

        self.status_label.setText(f"POS: {', '.join(summary_parts)}")

    def _clear_all(self) -> None:
        """Clear all fields."""
        self.pos_combo.setCurrentIndex(0)
        self.uncertain_check.setChecked(False)
        self.alternatives_edit.clear()
        self.confidence_slider.setValue(100)
        self.todo_check.setChecked(False)

    def _apply_annotation(self) -> None:
        """Apply annotation and close dialog."""
        # Get POS
        pos_map = {
            "": None,
            "Noun (N)": "N",
            "Verb (V)": "V",
            "Adjective (A)": "A",
            "Pronoun (R)": "R",
            "Determiner/Article (D)": "D",
            "Adverb (B)": "B",
            "Conjunction (C)": "C",
            "Preposition (E)": "E",
            "Interjection (I)": "I",
        }
        self.annotation.pos = pos_map[self.pos_combo.currentText()]

        # Save current values for future use
        if self.annotation.pos:
            self._save_current_values(self.annotation.pos)

        # Extract values based on POS
        if self.annotation.pos == "N":
            self._extract_noun_values()
        elif self.annotation.pos == "V":
            self._extract_verb_values()
        elif self.annotation.pos == "A":
            self._extract_adjective_values()
        elif self.annotation.pos == "R":
            self._extract_pronoun_values()
        elif self.annotation.pos == "E":
            self._extract_preposition_values()
        elif self.annotation.pos == "B":
            self._extract_adverb_values()

        # Extract metadata
        self.annotation.uncertain = self.uncertain_check.isChecked()
        alternatives_text = self.alternatives_edit.text().strip()
        if alternatives_text:
            self.annotation.alternatives_json = alternatives_text
        self.annotation.confidence = self.confidence_slider.value()

        self.annotation_applied.emit(self.annotation)
        self.accept()

    def _extract_noun_values(self):
        """Extract noun annotation values."""
        gender_map = {
            "": None,
            "Masculine (m)": "m",
            "Feminine (f)": "f",
            "Neuter (n)": "n",
        }
        self.annotation.gender = gender_map.get(self.gender_combo.currentText())
        number_map = {"": None, "Singular (s)": "s", "Plural (p)": "p"}
        self.annotation.number = number_map.get(self.number_combo.currentText())
        case_map = {
            "": None,
            "Nominative (n)": "n",
            "Accusative (a)": "a",
            "Genitive (g)": "g",
            "Dative (d)": "d",
            "Instrumental (i)": "i",
        }
        self.annotation.case = case_map.get(self.case_combo.currentText())
        declension = self.declension_combo.currentText().strip()
        self.annotation.declension = declension if declension else None

    def _extract_verb_values(self):
        """Extract verb annotation values."""
        class_text = self.verb_class_combo.currentText().strip()
        if class_text:
            # Extract code from text like "Weak II (w2)"
            if "(" in class_text:
                self.annotation.verb_class = class_text.split("(")[1].rstrip(")")
            else:
                self.annotation.verb_class = class_text
        tense_map = {"": None, "Past (p)": "p", "Present (n)": "n"}
        self.annotation.verb_tense = tense_map.get(self.verb_tense_combo.currentText())
        mood_map = {
            "": None,
            "Indicative (i)": "i",
            "Subjunctive (s)": "s",
            "Imperative (imp)": "imp",
        }
        self.annotation.verb_mood = mood_map.get(self.verb_mood_combo.currentText())
        person_map = {"": None, "1st": 1, "2nd": 2, "3rd": 3}
        self.annotation.verb_person = person_map.get(
            self.verb_person_combo.currentText()
        )
        number_map = {"": None, "Singular (s)": "s", "Plural (p)": "p"}
        self.annotation.number = number_map.get(self.verb_number_combo.currentText())
        aspect_map = {
            "": None,
            "Perfect (p)": "p",
            "Progressive (prg)": "prg",
            "Gnomic (gn)": "gn",
        }
        self.annotation.verb_aspect = aspect_map.get(
            self.verb_aspect_combo.currentText()
        )
        form_map = {
            "": None,
            "Finite (f)": "f",
            "Infinitive (i)": "i",
            "Participle (p)": "p",
        }
        self.annotation.verb_form = form_map.get(self.verb_form_combo.currentText())

    def _extract_adjective_values(self):
        """Extract adjective annotation values."""
        # Note: Need proper degree field
        gender_map = {
            "": None,
            "Masculine (m)": "m",
            "Feminine (f)": "f",
            "Neuter (n)": "n",
        }
        self.annotation.gender = gender_map.get(self.adj_gender_combo.currentText())
        number_map = {"": None, "Singular (s)": "s", "Plural (p)": "p"}
        self.annotation.number = number_map.get(self.adj_number_combo.currentText())
        case_map = {
            "": None,
            "Nominative (n)": "n",
            "Accusative (a)": "a",
            "Genitive (g)": "g",
            "Dative (d)": "d",
            "Instrumental (i)": "i",
        }
        self.annotation.case = case_map.get(self.adj_case_combo.currentText())

    def _extract_pronoun_values(self):
        """Extract pronoun annotation values."""
        type_map = {
            "": None,
            "Personal (p)": "p",
            "Relative (r)": "r",
            "Demonstrative (d)": "d",
            "Interrogative (i)": "i",
        }
        self.annotation.pronoun_type = type_map.get(self.pro_type_combo.currentText())
        gender_map = {
            "": None,
            "Masculine (m)": "m",
            "Feminine (f)": "f",
            "Neuter (n)": "n",
        }
        self.annotation.gender = gender_map.get(self.pro_gender_combo.currentText())
        number_map = {"": None, "Singular (s)": "s", "Plural (p)": "p"}
        self.annotation.number = number_map.get(self.pro_number_combo.currentText())
        case_map = {
            "": None,
            "Nominative (n)": "n",
            "Accusative (a)": "a",
            "Genitive (g)": "g",
            "Dative (d)": "d",
            "Instrumental (i)": "i",
        }
        self.annotation.case = case_map.get(self.pro_case_combo.currentText())

    def _extract_preposition_values(self):
        """Extract preposition annotation values."""
        case_map = {
            "": None,
            "Accusative (a)": "a",
            "Dative (d)": "d",
            "Genitive (g)": "g",
        }
        self.annotation.prep_case = case_map.get(self.prep_case_combo.currentText())

    def _extract_adverb_values(self):
        """Extract adverb annotation values."""
        # Adverbs have minimal fields
