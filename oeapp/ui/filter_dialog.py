"""Filter dialog for finding annotations."""

from typing import Final

from PySide6.QtCore import QModelIndex, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from oeapp.services.filter import FilterCriteria, FilterService


class AnnotationFilterCriteriaBuilder:
    """
    Adds a translation filter criteria group to a layout.  This allows
    the user to filter the annotations of the OE words based on the criteria.

    The filter criteria are:

    - Part of speech: noun, verb, adjective, pronoun, etc.
    - Incomplete: show only incomplete annotations
    - Uncertainty: certain or uncertain
    - Missing field: show only annotations with missing fields
    - Confidence: confidence level in identifying the correct annotation
    - Alternatives: show only annotations with alternatives

    """

    #: Part of speech filter labels
    PARTS_OF_SPEECH: Final[list[str]] = [
        "Any POS",
        "Noun (N)",
        "Verb (V)",
        "Adjective (A)",
        "Pronoun (R)",
        "Determiner (D)",
        "Adverb (B)",
        "Conjunction (C)",
        "Preposition (E)",
        "Interjection (I)",
    ]

    #: Missing field filter labels
    MISSING_FIELDS: Final[list[str]] = [
        "None",
        "Gender",
        "Number",
        "Case",
        "Verb Tense",
        "Verb Mood",
        "Verb Person",
        "Verb Class",
        "Pronoun Type",
        "Preposition Case",
    ]

    #: Uncertainty filter labels
    UNCERTAINTY_FILTER_LABELS: Final[list[str]] = [
        "All",
        "Uncertain only",
        "Certain only",
    ]

    #: "Has alternatives" filter labels
    ALTERNATIVES_FILTER_LABELS: Final[list[str]] = [
        "All",
        "With alternatives",
        "Without alternatives",
    ]

    def _add_part_of_speech_filters(self, form_layout: QFormLayout) -> None:
        """
        Add the part of speech filters to the form layout.

        This means:

        - Creating a POS criteria label
        """
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(self.PARTS_OF_SPEECH)
        form_layout.addRow("Part of Speech:", self.pos_combo)

    def _add_incomplete_filters(self, form_layout: QFormLayout) -> None:
        """
        Add the incomplete filters to the form layout.

        This means:

        - Creating a incomplete filters label
        """
        self.incomplete_check = QCheckBox("Show only incomplete annotations")
        self.incomplete_check.setToolTip(
            "Find annotations missing required fields (e.g., verbs missing tense, "
            "nouns missing case, etc.)"
        )
        form_layout.addRow("Incomplete:", self.incomplete_check)

    def _add_uncertainty_filters(self, form_layout: QFormLayout) -> None:
        """
        Add the uncertainty filters to the form layout.

        This means:

        - Creating a uncertainty filters label
        """
        self.uncertainty_combo = QComboBox()
        self.uncertainty_combo.addItems(self.UNCERTAINTY_FILTER_LABELS)
        form_layout.addRow("Uncertainty:", self.uncertainty_combo)

    def _add_missing_field_filters(self, form_layout: QFormLayout) -> None:
        """
        Add the missing field filters to the form layout.

        This means:

        - Creating a missing field filters label
        """
        self.missing_field_combo = QComboBox()
        self.missing_field_combo.addItems(self.MISSING_FIELDS)
        form_layout.addRow("Missing Field:", self.missing_field_combo)

    def _add_confidence_filters(self, form_layout: QFormLayout) -> None:
        """
        Add the confidence filters to the form layout.

        This means:

        - Creating a confidence filters label
        """
        self.confidence_layout = QHBoxLayout()
        self.min_confidence_spin = QSpinBox()
        self.min_confidence_spin.setRange(0, 100)
        self.min_confidence_spin.setSpecialValueText("Any")
        self.min_confidence_spin.setValue(0)
        self.confidence_layout.addWidget(QLabel("Min:"))
        self.confidence_layout.addWidget(self.min_confidence_spin)
        self.confidence_layout.addWidget(QLabel("Max:"))
        self.max_confidence_spin = QSpinBox()
        self.max_confidence_spin.setRange(0, 100)
        self.max_confidence_spin.setSpecialValueText("Any")
        self.max_confidence_spin.setValue(100)
        self.confidence_layout.addWidget(self.max_confidence_spin)
        self.confidence_layout.addStretch()
        form_layout.addRow("Confidence:", self.confidence_layout)

    def _add_alternatives_filters(self, form_layout: QFormLayout) -> None:
        """
        Add the alternatives filters to the form layout.

        This means:

        - Creating a alternatives filters label
        """
        self.alternatives_combo = QComboBox()
        self.alternatives_combo.addItems(self.ALTERNATIVES_FILTER_LABELS)
        form_layout.addRow("Alternatives:", self.alternatives_combo)

    def build(self, layout: QVBoxLayout) -> None:
        """
        Add the filter criteria group to the dialog.

        This means, creating a filter criteria group with the following filters:

        - Part of speech: noun, verb, adjective, pronoun, etc.
        - Incomplete: show only incomplete annotations
        - Missing field: show only annotations with missing fields
        - Uncertainty: certain or uncertain
        - Confidence: confidence level in identifying the correct annotation
        - Alternatives: show only annotations with alternatives

        """
        filter_group = QGroupBox("Annotation Filter Criteria")
        filter_layout = QFormLayout()
        self._add_part_of_speech_filters(filter_layout)
        self._add_incomplete_filters(filter_layout)
        self._add_missing_field_filters(filter_layout)
        self._add_uncertainty_filters(filter_layout)
        self._add_confidence_filters(filter_layout)
        self._add_alternatives_filters(filter_layout)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)


class FilterDialog(QDialog):
    """
    Dialog for filtering and finding annotations.
    """

    #: Part of speech map
    PART_OF_SPEECH_MAP: Final[dict[str, str]] = {
        "Noun (N)": "N",
        "Verb (V)": "V",
        "Adjective (A)": "A",
        "Pronoun (R)": "R",
        "Determiner (D)": "D",
        "Adverb (B)": "B",
        "Conjunction (C)": "C",
        "Preposition (E)": "E",
        "Interjection (I)": "I",
    }

    FIELD_MAP: Final[dict[str, str]] = {
        "Gender": "gender",
        "Number": "number",
        "Case": "case",
        "Verb Tense": "verb_tense",
        "Verb Mood": "verb_mood",
        "Verb Person": "verb_person",
        "Verb Class": "verb_class",
        "Pronoun Type": "pronoun_type",
        "Preposition Case": "prep_case",
    }

    token_selected = Signal(int)  # Emits token_id when user selects a token

    def __init__(
        self,
        filter_service: FilterService,
        project_id: int,
        parent: QWidget | None = None,
    ) -> None:
        """
        Initialize filter dialog.

        Args:
            filter_service: Filter service instance
            project_id: Current project ID

        Keyword Args:
            parent: Parent widget

        """
        super().__init__(parent)
        #: Filter service instance
        self.filter_service = filter_service
        #: Project ID
        self.project_id = project_id
        #: Current results
        self.current_results: list[dict] = []
        self._setup_ui()
        self._load_statistics()

    def _setup_window(self) -> None:
        """
        Set up the window.

        This means:

        - Setting the window title
        - Setting the window geometry
        - Setting the minimum size
        """
        self.setWindowTitle("Filter Annotations")
        self.setGeometry(100, 100, 900, 700)
        self.setMinimumSize(800, 600)

    def _setup_layout(self) -> None:
        """
        Set up the layout.

        This means:

        - Creating a vertical layout for the dialog
        """
        return QVBoxLayout(self)

    def _add_header(self, layout: QVBoxLayout) -> None:
        """
        Add the header to the layout.

        This means:

        - Creating a header label
        """
        header = QLabel("Filter and Find Annotations")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

    def _add_statistics(self, layout: QVBoxLayout) -> None:
        """
        Add the statistics to the layout.

        This means:

        - Creating a statistics label
        """
        stats_label = QLabel("Project Statistics")
        stats_font = QFont()
        stats_font.setBold(True)
        stats_label.setFont(stats_font)
        layout.addWidget(stats_label)
        self.stats_text = QLabel()
        self.stats_text.setWordWrap(True)
        layout.addWidget(self.stats_text)

    def _add_buttons(self, layout: QVBoxLayout) -> None:
        """
        Add the buttons to the layout.

        This means:

        - Creating a apply button
        - Creating a clear button
        """
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply Filter")
        self.apply_button.clicked.connect(self._apply_filter)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear_filters)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.clear_button)
        layout.addLayout(button_layout)

    def _add_results_table(self, layout: QVBoxLayout) -> None:
        """
        Add the results table to the layout.

        The results table displays the following columns:

        - Sentence: the sentence number
        - Token: the token
        - POS: the part of speech
        - Issues: the issues with the annotation (e.g., missing fields, uncertain, etc.)
        - Uncertain: whether the annotation is uncertain

        The results table is used to display the results of the filter criteria.

        """
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(
            [
                "Sentence",
                "Token",
                "POS",
                "Issues",
                "Uncertain",
            ]
        )
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.doubleClicked.connect(self._on_result_double_clicked)
        layout.addWidget(self.results_table)

    def _setup_ui(self) -> None:
        """
        Set up the UI layout.

        This means:

        - Setting the window title
        - Setting the window geometry
        - Setting the minimum size
        - Creating a vertical layout for the dialog
        - Adding a header label
        - Adding a statistics section
        - Adding a filter criteria section
        - Adding a results table
        - Adding a dialog buttons

        """
        # The window itself
        self._setup_window()
        layout = self._setup_layout()
        self._add_header(layout)
        self._add_statistics(layout)
        filter_builder = AnnotationFilterCriteriaBuilder()
        filter_builder.build(layout)
        self._add_buttons(layout)
        self._add_results_table(layout)
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_statistics(self) -> None:
        """
        Load and display project statistics.

        This shows:

        - Total tokens: the total number of tokens in the project
        - Annotated tokens: the number of tokens that have been annotated
        - Unannotated tokens: the number of tokens that have not been annotated
        - Uncertain tokens: the number of tokens that are uncertain
        - Incomplete tokens: the number of tokens that are incomplete
        - POS distribution: the distribution of the parts of speech in the project

        """
        stats = self.filter_service.get_statistics(self.project_id)
        stats_text = (
            f"Total tokens: {stats['total_tokens']} | "
            f"Annotated: {stats['annotated_tokens']} | "
            f"Unannotated: {stats['unannotated_tokens']} | "
            f"Uncertain: {stats['uncertain_count']} | "
            f"Incomplete: {stats['incomplete_count']}"
        )
        if stats["pos_distribution"]:
            pos_text = ", ".join(
                [f"{pos}: {count}" for pos, count in stats["pos_distribution"].items()]
            )
            stats_text += f"\nPOS distribution: {pos_text}"
        self.stats_text.setText(stats_text)

    def _apply_filter(self) -> None:
        """
        Apply filter criteria and show results.
        """
        criteria = FilterCriteria()

        # POS filter
        pos_text = self.pos_combo.currentText()
        if pos_text != "Any POS":
            criteria.pos = self.PART_OF_SPEECH_MAP.get(pos_text)

        # Incomplete filter
        criteria.incomplete = self.incomplete_check.isChecked()

        # Missing field filter
        missing_field_text = self.missing_field_combo.currentText()
        if missing_field_text != "None":
            criteria.missing_field = self.FIELD_MAP.get(missing_field_text)

        # Uncertainty filter
        uncertain_text = self.uncertain_combo.currentText()
        if uncertain_text == "Uncertain only":
            criteria.uncertain = True
        elif uncertain_text == "Certain only":
            criteria.uncertain = False

        # Confidence range
        if self.min_confidence_spin.value() > 0:
            criteria.min_confidence = self.min_confidence_spin.value()
        if self.max_confidence_spin.value() < 100:  # noqa: PLR2004
            criteria.max_confidence = self.max_confidence_spin.value()

        # Alternatives filter
        alternatives_text = self.alternatives_combo.currentText()
        if alternatives_text == "With alternatives":
            criteria.has_alternatives = True
        elif alternatives_text == "Without alternatives":
            criteria.has_alternatives = False

        # Execute filter
        try:
            self.current_results = self.filter_service.find_tokens(
                self.project_id, criteria
            )
            self._display_results()
        except Exception as e:
            QMessageBox.warning(
                self, "Filter Error", f"An error occurred while filtering:\n{e!s}"
            )

    def _display_results(self) -> None:
        """Display filter results in the table."""
        self.results_table.setRowCount(len(self.current_results))

        for row_idx, result in enumerate(self.current_results):
            # Sentence number
            sentence_item = QTableWidgetItem(f"[{result['sentence_order']}]")
            self.results_table.setItem(row_idx, 0, sentence_item)

            # Token
            token_item = QTableWidgetItem(result["surface"])
            self.results_table.setItem(row_idx, 1, token_item)

            # POS
            pos_item = QTableWidgetItem(result["pos"] or "—")
            self.results_table.setItem(row_idx, 2, pos_item)

            # Issues (missing fields)
            issues = []
            if result["pos"] == "N":
                if not result["gender"]:
                    issues.append("no gender")
                if not result["number"]:
                    issues.append("no number")
                if not result["case"]:
                    issues.append("no case")
            elif result["pos"] == "V":
                if not result["verb_tense"]:
                    issues.append("no tense")
                if not result["verb_mood"]:
                    issues.append("no mood")
                if not result["verb_person"]:
                    issues.append("no person")
                if not result["number"]:
                    issues.append("no number")
            elif result["pos"] == "A":
                if not result["gender"]:
                    issues.append("no gender")
                if not result["number"]:
                    issues.append("no number")
                if not result["case"]:
                    issues.append("no case")
            elif result["pos"] == "R":
                if not result["pronoun_type"]:
                    issues.append("no type")
                if not result["gender"]:
                    issues.append("no gender")
                if not result["number"]:
                    issues.append("no number")
                if not result["case"]:
                    issues.append("no case")
            elif result["pos"] == "E":
                if not result["prep_case"]:
                    issues.append("no case")

            issues_text = ", ".join(issues) if issues else "—"
            issues_item = QTableWidgetItem(issues_text)
            self.results_table.setItem(row_idx, 3, issues_item)

            # Uncertain
            uncertain_item = QTableWidgetItem("Yes" if result["uncertain"] else "No")
            self.results_table.setItem(row_idx, 4, uncertain_item)

        # Resize columns
        self.results_table.resizeColumnsToContents()

        # Show count
        if len(self.current_results) == 0:
            QMessageBox.information(
                self, "No Results", "No tokens match the filter criteria."
            )

    def _clear_filters(self) -> None:
        """
        Clear all filter criteria.
        """
        self.pos_combo.setCurrentIndex(0)
        self.incomplete_check.setChecked(False)
        self.missing_field_combo.setCurrentIndex(0)
        self.uncertain_combo.setCurrentIndex(0)
        self.min_confidence_spin.setValue(0)
        self.max_confidence_spin.setValue(100)
        self.alternatives_combo.setCurrentIndex(0)
        self.results_table.setRowCount(0)
        self.current_results = []

    def _on_result_double_clicked(self, index: QModelIndex) -> None:
        """
        Handle double-click on result row.  This means:

        - Emitting the token_id when the user double-clicks on a result row
        - Accepting the dialog

        Args:
            index: The index of the result row

        """
        if index.row() < len(self.current_results):
            token_id = self.current_results[index.row()]["token_id"]
            self.token_selected.emit(token_id)
            self.accept()
