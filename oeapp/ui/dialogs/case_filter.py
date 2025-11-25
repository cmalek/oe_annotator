"""Case filter dialog for selecting which cases to highlight."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from oeapp.ui.mixins import AnnotationLookupsMixin


class CaseFilterDialog(AnnotationLookupsMixin, QDialog):
    """
    Non-modal dialog for selecting which cases to highlight.

    Displays checkboxes for each case with color indicators.
    """

    # Signal emitted when selected cases change
    # Emits set of selected case codes (e.g., {"n", "a", "g"})
    cases_changed = Signal(set)
    # Signal emitted when dialog is closed
    dialog_closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize case filter dialog.

        Keyword Args:
            parent: Parent widget

        """
        super().__init__(parent)
        self.setModal(False)
        self.setWindowTitle("Select Cases to Highlight")
        self.setMinimumWidth(300)

        # Store checkbox references
        self.case_checkboxes: dict[str, QCheckBox] = {}
        # Default: all cases selected
        self._selected_cases: set[str] = {"n", "a", "g", "d", "i"}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title label
        title_label = QLabel("Select Cases to Highlight")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Add checkboxes for each case
        cases = ["n", "a", "g", "d", "i"]
        for case_code in cases:
            case_row = self._create_case_row(case_code)
            layout.addLayout(case_row)

        layout.addStretch()

        # Add Select All / Deselect All buttons
        button_layout = QHBoxLayout()
        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(self._select_all)
        deselect_all_button = QPushButton("Deselect All")
        deselect_all_button.clicked.connect(self._deselect_all)
        button_layout.addWidget(select_all_button)
        button_layout.addWidget(deselect_all_button)
        layout.addLayout(button_layout)

    def _create_case_row(self, case_code: str) -> QHBoxLayout:
        """
        Create a row with checkbox and color indicator for a case.

        Args:
            case_code: Case code (e.g., "n", "a", "g", "d", "i")

        Returns:
            QHBoxLayout containing checkbox and color indicator

        """
        from oeapp.ui.sentence_card import SentenceCard  # noqa: PLC0415

        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)

        # Create checkbox
        case_name = self.CASE_MAP.get(case_code, case_code)
        checkbox = QCheckBox(case_name)
        checkbox.setChecked(True)  # Default: all selected
        checkbox.stateChanged.connect(self._on_checkbox_changed)
        self.case_checkboxes[case_code] = checkbox
        row_layout.addWidget(checkbox)

        # Create color indicator
        color = SentenceCard.CASE_COLORS.get(case_code)
        if color:
            color_label = QLabel()
            color_label.setFixedSize(20, 20)
            # Convert QColor to RGB for stylesheet
            rgb = f"rgb({color.red()}, {color.green()}, {color.blue()})"
            color_label.setStyleSheet(
                f"background-color: {rgb}; border: 1px solid #999;"
            )
            color_label.setToolTip(f"Color for {case_name}")
            row_layout.addWidget(color_label)

        row_layout.addStretch()
        return row_layout

    def _on_checkbox_changed(self) -> None:
        """Handle checkbox state change and emit signal."""
        selected = set()
        for case_code, checkbox in self.case_checkboxes.items():
            if checkbox.isChecked():
                selected.add(case_code)
        self._selected_cases = selected
        self.cases_changed.emit(selected)

    def _select_all(self) -> None:
        """Select all case checkboxes."""
        for checkbox in self.case_checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all(self) -> None:
        """Deselect all case checkboxes."""
        for checkbox in self.case_checkboxes.values():
            checkbox.setChecked(False)

    def get_selected_cases(self) -> set[str]:
        """
        Get the currently selected cases.

        Returns:
            Set of selected case codes

        """
        return self._selected_cases.copy()

    def set_selected_cases(self, cases: set[str]) -> None:
        """
        Set which cases are selected.

        Args:
            cases: Set of case codes to select

        """
        self._selected_cases = cases.copy()
        # Block signals temporarily to avoid multiple emissions
        for checkbox in self.case_checkboxes.values():
            checkbox.blockSignals(True)  # noqa: FBT003
        for case_code, checkbox in self.case_checkboxes.items():
            checkbox.setChecked(case_code in cases)
        for checkbox in self.case_checkboxes.values():
            checkbox.blockSignals(False)  # noqa: FBT003
        # Emit signal once with final state
        self.cases_changed.emit(self._selected_cases)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """
        Handle dialog close event.

        Args:
            event: Close event

        """
        self.dialog_closed.emit()
        super().closeEvent(event)
