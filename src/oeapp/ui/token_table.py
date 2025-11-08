"""Token table UI component."""

from PySide6.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QHeaderView, QVBoxLayout
from PySide6.QtCore import Qt, Signal

from src.oeapp.models.token import Token
from src.oeapp.models.annotation import Annotation


class TokenTable(QWidget):
    """Widget displaying token annotation grid."""

    token_selected = Signal(Token)
    annotation_requested = Signal(Token)

    def __init__(self, parent=None):
        """Initialize token table.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.tokens: list[Token] = []
        self.annotations: dict[int, Annotation] = {}  # token_id -> Annotation
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        self.table = QTableWidget(self)
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Word",
            "POS",
            "Gender",
            "Number",
            "Case",
            "Declension",
            "PronounType",
            "VerbClass",
            "VerbForm",
            "PrepObjCase",
            "Notes",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMaximumHeight(200)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

    def _on_item_double_clicked(self, item):
        """Handle double-click on table item.

        Args:
            item: Clicked table item
        """
        row = item.row()
        if 0 <= row < len(self.tokens):
            token = self.tokens[row]
            self.annotation_requested.emit(token)

    def _on_selection_changed(self):
        """Handle selection change."""
        row = self.table.currentRow()
        if 0 <= row < len(self.tokens):
            token = self.tokens[row]
            self.token_selected.emit(token)

    def set_tokens(self, tokens: list[Token], annotations: dict[int, Annotation] = None):
        """Set tokens and annotations to display.

        Args:
            tokens: List of tokens
            annotations: Dictionary mapping token_id to Annotation
        """
        self.tokens = tokens
        self.annotations = annotations or {}
        self.table.setRowCount(len(tokens))

        for row, token in enumerate(tokens):
            # Word
            self.table.setItem(row, 0, QTableWidgetItem(token.surface))
            # Get annotation for this token
            annotation = self.annotations.get(token.id)
            if annotation:
                self.table.setItem(row, 1, QTableWidgetItem(annotation.pos or "—"))
                self.table.setItem(row, 2, QTableWidgetItem(annotation.gender or "—"))
                self.table.setItem(row, 3, QTableWidgetItem(annotation.number or "—"))
                self.table.setItem(row, 4, QTableWidgetItem(annotation.case or "—"))
                self.table.setItem(row, 5, QTableWidgetItem(annotation.declension or "—"))
                self.table.setItem(row, 6, QTableWidgetItem(annotation.pronoun_type or "—"))
                self.table.setItem(row, 7, QTableWidgetItem(annotation.verb_class or "—"))
                self.table.setItem(row, 8, QTableWidgetItem(annotation.verb_form or "—"))
                self.table.setItem(row, 9, QTableWidgetItem(annotation.prep_case or "—"))
            else:
                # Fill with "—" for unannotated tokens
                for col in range(1, 10):
                    self.table.setItem(row, col, QTableWidgetItem("—"))
            # Notes column
            self.table.setItem(row, 10, QTableWidgetItem(""))

    def update_annotation(self, annotation: Annotation):
        """Update annotation display for a token.

        Args:
            annotation: Updated annotation
        """
        self.annotations[annotation.token_id] = annotation
        # Find token row
        for row, token in enumerate(self.tokens):
            if token.id == annotation.token_id:
                # Update row
                self.table.setItem(row, 1, QTableWidgetItem(annotation.pos or "—"))
                self.table.setItem(row, 2, QTableWidgetItem(annotation.gender or "—"))
                self.table.setItem(row, 3, QTableWidgetItem(annotation.number or "—"))
                self.table.setItem(row, 4, QTableWidgetItem(annotation.case or "—"))
                self.table.setItem(row, 5, QTableWidgetItem(annotation.declension or "—"))
                self.table.setItem(row, 6, QTableWidgetItem(annotation.pronoun_type or "—"))
                self.table.setItem(row, 7, QTableWidgetItem(annotation.verb_class or "—"))
                self.table.setItem(row, 8, QTableWidgetItem(annotation.verb_form or "—"))
                self.table.setItem(row, 9, QTableWidgetItem(annotation.prep_case or "—"))
                break

    def get_selected_token(self) -> Token | None:
        """Get currently selected token.

        Returns:
            Selected token or None
        """
        row = self.table.currentRow()
        if 0 <= row < len(self.tokens):
            return self.tokens[row]
        return None

    def select_token(self, token_index: int):
        """Select a token by index.

        Args:
            token_index: Index of token to select
        """
        if 0 <= token_index < len(self.tokens):
            self.table.selectRow(token_index)
