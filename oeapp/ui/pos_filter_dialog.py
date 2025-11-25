"""POS filter dialog for selecting which parts of speech to highlight."""

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

from oeapp.ui.annotation_lookups import AnnotationLookupsMixin


class POSFilterDialog(AnnotationLookupsMixin, QDialog):
    """
    Non-modal dialog for selecting which parts of speech to highlight.

    Displays checkboxes for each POS tag with color indicators.
    """

    # Signal emitted when selected POS tags change
    # Emits set of selected POS codes (e.g., {"N", "V", "A"})
    pos_changed = Signal(set)
    # Signal emitted when dialog is closed
    dialog_closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize POS filter dialog.

        Keyword Args:
            parent: Parent widget

        """
        super().__init__(parent)
        self.setModal(False)
        self.setWindowTitle("Select Parts of Speech to Highlight")
        self.setMinimumWidth(300)

        # Store checkbox references
        self.pos_checkboxes: dict[str, QCheckBox] = {}
        # Default: all POS tags selected
        self._selected_pos: set[str] = {"N", "V", "A", "R", "D", "B", "C", "E", "I"}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title label
        title_label = QLabel("Select Parts of Speech to Highlight")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Add checkboxes for each POS tag
        pos_tags = ["N", "V", "A", "R", "D", "B", "C", "E", "I"]
        for pos_code in pos_tags:
            pos_row = self._create_pos_row(pos_code)
            layout.addLayout(pos_row)

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

    def _create_pos_row(self, pos_code: str) -> QHBoxLayout:
        """
        Create a row with checkbox and color indicator for a POS tag.

        Args:
            pos_code: POS code (e.g., "N", "V", "A", "R", "D", "B", "C", "E", "I")

        Returns:
            QHBoxLayout containing checkbox and color indicator

        """
        from oeapp.ui.sentence_card import SentenceCard  # noqa: PLC0415

        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)

        # Create checkbox
        pos_name = self.PART_OF_SPEECH_MAP.get(pos_code, pos_code)
        if pos_name is None:
            pos_name = pos_code
        checkbox = QCheckBox(pos_name)
        checkbox.setChecked(True)  # Default: all selected
        checkbox.stateChanged.connect(self._on_checkbox_changed)
        self.pos_checkboxes[pos_code] = checkbox
        row_layout.addWidget(checkbox)

        # Create color indicator
        color = SentenceCard.POS_COLORS.get(pos_code)
        if color:
            color_label = QLabel()
            color_label.setFixedSize(20, 20)
            # Convert QColor to RGB for stylesheet
            rgb = f"rgb({color.red()}, {color.green()}, {color.blue()})"
            color_label.setStyleSheet(
                f"background-color: {rgb}; border: 1px solid #999;"
            )
            color_label.setToolTip(f"Color for {pos_name}")
            row_layout.addWidget(color_label)

        row_layout.addStretch()
        return row_layout

    def _on_checkbox_changed(self) -> None:
        """Handle checkbox state change and emit signal."""
        selected = set()
        for pos_code, checkbox in self.pos_checkboxes.items():
            if checkbox.isChecked():
                selected.add(pos_code)
        self._selected_pos = selected
        self.pos_changed.emit(selected)

    def _select_all(self) -> None:
        """Select all POS checkboxes."""
        for checkbox in self.pos_checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all(self) -> None:
        """Deselect all POS checkboxes."""
        for checkbox in self.pos_checkboxes.values():
            checkbox.setChecked(False)

    def get_selected_pos(self) -> set[str]:
        """
        Get the currently selected POS tags.

        Returns:
            Set of selected POS codes

        """
        return self._selected_pos.copy()

    def set_selected_pos(self, pos_tags: set[str]) -> None:
        """
        Set which POS tags are selected.

        Args:
            pos_tags: Set of POS codes to select

        """
        self._selected_pos = pos_tags.copy()
        # Block signals temporarily to avoid multiple emissions
        for checkbox in self.pos_checkboxes.values():
            checkbox.blockSignals(True)  # noqa: FBT003
        for pos_code, checkbox in self.pos_checkboxes.items():
            checkbox.setChecked(pos_code in pos_tags)
        for checkbox in self.pos_checkboxes.values():
            checkbox.blockSignals(False)  # noqa: FBT003
        # Emit signal once with final state
        self.pos_changed.emit(self._selected_pos)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """
        Handle dialog close event.

        Args:
            event: Close event

        """
        self.dialog_closed.emit()
        super().closeEvent(event)

