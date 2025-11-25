"""Token details sidebar widget."""

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from oeapp.ui.annotation_lookups import AnnotationLookupsMixin

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation
    from oeapp.models.sentence import Sentence
    from oeapp.models.token import Token


class TokenDetailsSidebar(AnnotationLookupsMixin, QWidget):
    """Sidebar widget displaying detailed token information."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the token details sidebar."""
        super().__init__(parent)
        self._current_token: Token | None = None
        self._current_sentence: Sentence | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area.setWidget(self.content_widget)
        layout.addWidget(scroll_area)

        # Show empty state initially
        self._show_empty_state()

    def _show_empty_state(self) -> None:
        """Show empty state with centered 'Word details' text."""
        self._clear_content()

        empty_label = QLabel("Word details")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setFont(QFont("Arial", 16))
        empty_label.setStyleSheet("color: #666;")

        self.content_layout.addStretch()
        self.content_layout.addWidget(empty_label)
        self.content_layout.addStretch()

    def _clear_content(self) -> None:
        """Clear all content from the sidebar."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def update_token(self, token: Token, sentence: Sentence) -> None:
        """
        Update the sidebar with token details.

        Args:
            token: Token to display
            sentence: Sentence containing the token

        """
        self._current_token = token
        self._current_sentence = sentence
        self._clear_content()

        annotation = cast("Annotation", token.annotation)
        pos_str = ""
        gender_str = ""
        context_str = ""
        if annotation is not None:
            pos_str = annotation.format_pos(annotation)
            gender_str = annotation.format_gender(annotation)
            context_str = annotation.format_context(annotation)

        # Header: [sentence number] token surface
        style = "color: #666; font-family: Helvetica; font-weight: normal;"
        header_text = f"[{sentence.display_order}] "
        if pos_str:
            header_text += f"<sup style='{style}'>{pos_str}</sup>"
        if gender_str:
            header_text += f"<sub style='{style}'>{gender_str}</sub>"
        header_text += f"{token.surface}"
        if context_str:
            header_text += f"<sub style='{style}'>{context_str}</sub>"
        header_label = QLabel(header_text)
        header_label.setFont(QFont("Anvers", 18, QFont.Weight.Bold))
        header_label.setWordWrap(True)
        self.content_layout.addWidget(header_label)

        self.content_layout.addSpacing(10)

        if not annotation or not annotation.pos:
            # No annotation or POS set
            no_pos_label = QLabel("No annotation available")
            no_pos_label.setStyleSheet("color: #999; font-style: italic;")
            self.content_layout.addWidget(no_pos_label)
            return

        # Display POS
        pos_text = self.PART_OF_SPEECH_MAP.get(annotation.pos, "Unknown")
        if pos_text:
            pos_label = QLabel(f"Part of Speech: {pos_text}")
            pos_label.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
            self.content_layout.addWidget(pos_label)
            self.content_layout.addSpacing(5)

        # Display POS-specific fields
        if annotation.pos == "N":
            self._display_noun_fields(annotation)
        elif annotation.pos == "V":
            self._display_verb_fields(annotation)
        elif annotation.pos == "A":
            self._display_adjective_fields(annotation)
        elif annotation.pos == "R":
            self._display_pronoun_fields(annotation)
        elif annotation.pos == "D":
            self._display_article_fields(annotation)
        elif annotation.pos == "E":
            self._display_preposition_fields(annotation)
        elif annotation.pos == "B":
            self._display_adverb_fields(annotation)
        elif annotation.pos == "C":
            self._display_conjunction_fields(annotation)
        elif annotation.pos == "I":
            self._display_interjection_fields(annotation)

        # Common fields for all POS
        self.content_layout.addSpacing(10)
        separator = QLabel("─" * 30)
        separator.setStyleSheet(
            "color: #ccc; font-family: Helvetica; font-weight: normal;"
        )
        self.content_layout.addWidget(separator)
        self.content_layout.addSpacing(10)

        self._display_common_fields(annotation)

        self.content_layout.addStretch()

    def _display_common_fields(self, annotation: Annotation) -> None:
        """
        Display fields common to all POS types.

        Args:
            annotation: Annotation to display

        """
        # Root
        root_value = annotation.root if annotation.root else "?"
        root_label = QLabel(f"Root: {root_value}")
        self._format_field_label(root_label, annotation.root)
        self.content_layout.addWidget(root_label)

        # Modern English Meaning
        mod_e_value = (
            annotation.modern_english_meaning
            if annotation.modern_english_meaning
            else "?"
        )
        mod_e_label = QLabel(f"Modern English Meaning: {mod_e_value}")
        mod_e_label.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        self._format_field_label(mod_e_label, annotation.modern_english_meaning)
        self.content_layout.addWidget(mod_e_label)

        # Uncertainty
        uncertain_value = "Yes" if annotation.uncertain else "?"
        uncertain_label = QLabel(f"Uncertainty: {uncertain_value}")
        self._format_field_label(uncertain_label, annotation.uncertain)
        self.content_layout.addWidget(uncertain_label)

        # TODO: - Note: TODO field may not exist in model, check if needed
        # For now, we'll skip it or show as "?"

        # Alternatives
        alternatives_value = (
            annotation.alternatives_json if annotation.alternatives_json else "?"
        )
        alternatives_label = QLabel(f"Alternatives: {alternatives_value}")
        self._format_field_label(alternatives_label, annotation.alternatives_json)
        self.content_layout.addWidget(alternatives_label)

        # Confidence
        confidence_value = (
            f"{annotation.confidence}%" if annotation.confidence is not None else "?"
        )
        confidence_label = QLabel(f"Confidence: {confidence_value}")
        self._format_field_label(confidence_label, annotation.confidence)
        self.content_layout.addWidget(confidence_label)

    def _format_field_label(
        self,
        label: QLabel,
        value: str | int | bool | None,  # noqa: FBT001
    ) -> None:
        """
        Format a field label based on whether value is set.

        Args:
            label: Label to format
            value: Field value (None or empty means unset)

        """
        if value is None or value == "" or value is False:
            label.setStyleSheet("color: #999; font-style: italic;")
        else:
            label.setStyleSheet(
                "color: #000; font-family: Helvetica; font-weight: normal;"
            )

    def _display_noun_fields(self, annotation: Annotation) -> None:
        """
        Display noun-specific fields.

        Args:
            annotation: Annotation to display

        """
        # Gender
        gender_value = self.GENDER_MAP.get(annotation.gender, "?")
        gender_label = QLabel(f"Gender: {gender_value}")
        self._format_field_label(gender_label, annotation.gender)
        self.content_layout.addWidget(gender_label)

        # Number
        number_value = self.NUMBER_MAP.get(annotation.number, "?")
        number_label = QLabel(f"Number: {number_value}")
        self._format_field_label(number_label, annotation.number)
        self.content_layout.addWidget(number_label)

        # Case
        case_value = self.CASE_MAP.get(annotation.case, "?")
        case_label = QLabel(f"Case: {case_value}")
        case_label.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        self._format_field_label(case_label, annotation.case)
        self.content_layout.addWidget(case_label)

        # Declension
        declension_value = annotation.declension if annotation.declension else "?"
        declension_label = QLabel(f"Declension: {declension_value}")
        self._format_field_label(declension_label, annotation.declension)
        self.content_layout.addWidget(declension_label)

    def _display_verb_fields(self, annotation: Annotation) -> None:
        """
        Display verb-specific fields.

        Args:
            annotation: Annotation to display

        """
        # Verb Class
        verb_class_value = self.VERB_CLASS_MAP.get(annotation.verb_class, "?")
        verb_class_label = QLabel(f"Verb Class: {verb_class_value}")
        self._format_field_label(verb_class_label, annotation.verb_class)
        self.content_layout.addWidget(verb_class_label)

        # Verb Tense
        tense_value = self.VERB_TENSE_MAP.get(annotation.verb_tense, "?")
        tense_label = QLabel(f"Tense: {tense_value}")
        self._format_field_label(tense_label, annotation.verb_tense)
        self.content_layout.addWidget(tense_label)

        # Verb Mood
        mood_value = self.VERB_MOOD_MAP.get(annotation.verb_mood, "?")
        mood_label = QLabel(f"Mood: {mood_value}")
        self._format_field_label(mood_label, annotation.verb_mood)
        self.content_layout.addWidget(mood_label)

        # Verb Person
        person_value = (
            self.VERB_PERSON_MAP.get(annotation.verb_person, "?")
            if annotation.verb_person is not None
            else "?"
        )
        person_label = QLabel(f"Person: {person_value}")
        self._format_field_label(person_label, annotation.verb_person)
        self.content_layout.addWidget(person_label)

        # Number
        number_value = self.NUMBER_MAP.get(annotation.number, "?")
        number_label = QLabel(f"Number: {number_value}")
        self._format_field_label(number_label, annotation.number)
        self.content_layout.addWidget(number_label)

        # Verb Aspect
        aspect_value = self.VERB_ASPECT_MAP.get(annotation.verb_aspect, "?")
        aspect_label = QLabel(f"Aspect: {aspect_value}")
        self._format_field_label(aspect_label, annotation.verb_aspect)
        self.content_layout.addWidget(aspect_label)

        # Verb Form
        form_value = self.VERB_FORM_MAP.get(annotation.verb_form, "?")
        form_label = QLabel(f"Form: {form_value}")
        self._format_field_label(form_label, annotation.verb_form)
        self.content_layout.addWidget(form_label)

    def _display_adjective_fields(self, annotation: Annotation) -> None:
        """
        Display adjective-specific fields.

        Args:
            annotation: Annotation to display

        """
        # Note: Degree and inflection may not be directly stored in annotation model
        # For now, we'll show what's available

        # Gender
        gender_value = self.GENDER_MAP.get(annotation.gender, "?")
        gender_label = QLabel(f"Gender: {gender_value}")
        self._format_field_label(gender_label, annotation.gender)
        self.content_layout.addWidget(gender_label)

        # Number
        number_value = self.NUMBER_MAP.get(annotation.number, "?")
        number_label = QLabel(f"Number: {number_value}")
        self._format_field_label(number_label, annotation.number)
        self.content_layout.addWidget(number_label)

        # Case
        case_value = self.CASE_MAP.get(annotation.case, "?")
        case_label = QLabel(f"Case: {case_value}")
        self._format_field_label(case_label, annotation.case)
        self.content_layout.addWidget(case_label)

    def _display_pronoun_fields(self, annotation: Annotation) -> None:
        """
        Display pronoun-specific fields.

        Args:
            annotation: Annotation to display

        """
        # Pronoun Type
        pro_type_value = self.PRONOUN_TYPE_MAP.get(annotation.pronoun_type, "?")
        pro_type_label = QLabel(f"Pronoun Type: {pro_type_value}")
        self._format_field_label(pro_type_label, annotation.pronoun_type)
        self.content_layout.addWidget(pro_type_label)

        # Gender
        gender_value = self.GENDER_MAP.get(annotation.gender, "?")
        gender_label = QLabel(f"Gender: {gender_value}")
        self._format_field_label(gender_label, annotation.gender)
        self.content_layout.addWidget(gender_label)

        # Number
        number_value = self.PRONOUN_NUMBER_MAP.get(annotation.pronoun_number, "?")
        number_label = QLabel(f"Number: {number_value}")
        self._format_field_label(number_label, annotation.number)
        self.content_layout.addWidget(number_label)

        # Case
        case_value = self.CASE_MAP.get(annotation.case, "?")
        case_label = QLabel(f"Case: {case_value}")
        self._format_field_label(case_label, annotation.case)
        self.content_layout.addWidget(case_label)

    def _display_article_fields(self, annotation: Annotation) -> None:
        """
        Display article/determiner-specific fields.

        Args:
            annotation: Annotation to display

        """
        # Article Type
        article_type_value = self.ARTICLE_TYPE_MAP.get(annotation.article_type, "?")
        article_type_label = QLabel(f"Article Type: {article_type_value}")
        self._format_field_label(article_type_label, annotation.article_type)
        self.content_layout.addWidget(article_type_label)

        # Gender
        gender_value = self.GENDER_MAP.get(annotation.gender, "?")
        gender_label = QLabel(f"Gender: {gender_value}")
        self._format_field_label(gender_label, annotation.gender)
        self.content_layout.addWidget(gender_label)

        # Number
        number_value = self.NUMBER_MAP.get(annotation.number, "?")
        number_label = QLabel(f"Number: {number_value}")
        self._format_field_label(number_label, annotation.number)
        self.content_layout.addWidget(number_label)

        # Case
        case_value = self.CASE_MAP.get(annotation.case, "?")
        case_label = QLabel(f"Case: {case_value}")
        self._format_field_label(case_label, annotation.case)
        self.content_layout.addWidget(case_label)

    def _display_preposition_fields(self, annotation: Annotation) -> None:
        """
        Display preposition-specific fields.

        Args:
            annotation: Annotation to display

        """
        # Preposition Case
        prep_case_value = self.PREPOSITION_CASE_MAP.get(annotation.prep_case, "?")
        prep_case_label = QLabel(f"Governed Case: {prep_case_value}")
        self._format_field_label(prep_case_label, annotation.prep_case)
        self.content_layout.addWidget(prep_case_label)

    def _display_adverb_fields(self, annotation: Annotation) -> None:
        """Display adverb-specific fields."""
        # Adverbs have minimal fields

    def _display_conjunction_fields(self, annotation: Annotation) -> None:
        """Display conjunction-specific fields."""
        # Conjunctions have minimal fields

    def _display_interjection_fields(self, annotation: Annotation) -> None:
        """Display interjection-specific fields."""
        # Interjections have minimal fields

    def clear(self) -> None:
        """Clear the sidebar and show empty state."""
        self._current_token = None
        self._current_sentence = None
        self._show_empty_state()
