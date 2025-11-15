"""Token table UI component."""

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from oeapp.models.token import Token

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation


class TokenTable(QWidget):
    """
    Widget displaying token annotation grid.

    Args:
        parent: Parent widget

    """

    token_selected = Signal(Token)
    annotation_requested = Signal(Token)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        #: The tokens to display.
        self.tokens: list[Token] = []
        #: The annotations to display.
        self.annotations: dict[int, Annotation] = {}  # token_id -> Annotation
        # Set up the UI.
        self._setup_ui()

    def _setup_ui(self) -> None:
        """
        Set up the UI layout.

        This looks like this:
        +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
        | Word   | POS    | Gender | Number | Case   | Declension | PronounType | VerbClass | VerbForm | PrepObjCase | Notes  |
        +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
        | Token 1 | POS 1 | Gender 1 | Number 1 | Case 1 | Declension 1 | PronounType 1 | VerbClass 1 | VerbForm 1 | PrepObjCase 1 | Notes 1 |
        | Token 2 | POS 2 | Gender 2 | Number 2 | Case 2 | Declension 2 | PronounType 2 | VerbClass 2 | VerbForm 2 | PrepObjCase 2 | Notes 2 |
        | ...     | ...    | ...      | ...      | ...    | ...         | ...         | ...         | ...        | ...         | ...    |
        +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
        """  # noqa: E501
        # Create the layout.
        layout = QVBoxLayout(self)
        # Create the table.
        self.table = QTableWidget(self)
        # Set the number of columns to 11.
        self.table.setColumnCount(11)
        # Set the horizontal header labels.
        self.table.setHorizontalHeaderLabels(
            [
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
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMaximumHeight(200)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

    def _on_item_double_clicked(self, item: QTableWidgetItem) -> None:
        """
        Handle double-click on table item.

        - If the clicked item is not a token, do nothing.
        - If the clicked item is a token, emit the token_selected signal.

        Args:
            item: Clicked table item

        """
        row = item.row()
        # If the row is valid, emit the token_selected signal.
        if 0 <= row < len(self.tokens):
            token = self.tokens[row]
            self.annotation_requested.emit(token)

    def _on_selection_changed(self):
        """
        Handle selection change.

        - If the selected row is not a token, do nothing.
        - If the selected row is a token, get the token and emit the
          token_selected signal.

        """
        # Get the current row of the table.
        row = self.table.currentRow()
        if 0 <= row < len(self.tokens):
            token = self.tokens[row]
            self.token_selected.emit(token)

    def set_tokens(
        self, tokens: list[Token], annotations: dict[int, Annotation] | None = None
    ) -> None:
        """
        Set tokens and annotations to display.

        Args:
            tokens: List of tokens

        Keyword Args:
            annotations: Dictionary mapping ``token_id`` to
                :class:`~oeapp.models.annotation.Annotation` objects

        """
        # Set the tokens to display.
        self.tokens = tokens
        # Set the annotations to display.
        self.annotations = annotations or {}
        # Set the number of rows to the number of tokens.
        self.table.setRowCount(len(tokens))
        # Loop through the tokens and add them to the table.

        for row, token in enumerate(tokens):
            # Word
            self.table.setItem(row, 0, QTableWidgetItem(token.surface))
            # Get annotation for this token
            annotation = self.annotations.get(cast("int", token.id))
            if annotation:
                self.table.setItem(row, 1, QTableWidgetItem(annotation.pos or "—"))
                self.table.setItem(row, 2, QTableWidgetItem(annotation.gender or "—"))
                self.table.setItem(row, 3, QTableWidgetItem(annotation.number or "—"))
                self.table.setItem(row, 4, QTableWidgetItem(annotation.case or "—"))
                self.table.setItem(
                    row, 5, QTableWidgetItem(annotation.declension or "—")
                )
                self.table.setItem(
                    row, 6, QTableWidgetItem(annotation.pronoun_type or "—")
                )
                self.table.setItem(
                    row, 7, QTableWidgetItem(annotation.verb_class or "—")
                )
                self.table.setItem(
                    row, 8, QTableWidgetItem(annotation.verb_form or "—")
                )
                self.table.setItem(
                    row, 9, QTableWidgetItem(annotation.prep_case or "—")
                )
            else:
                # Fill with "—" for unannotated tokens
                for col in range(1, 10):
                    self.table.setItem(row, col, QTableWidgetItem("—"))
            # Notes column
            self.table.setItem(row, 10, QTableWidgetItem(""))

    def update_annotation(self, annotation: Annotation) -> None:
        """
        Update annotation display for a token.

        Args:
            annotation: Updated annotation

        """
        # Update the annotation in the annotations dictionary.
        self.annotations[annotation.token_id] = annotation
        # Find token row
        for row, token in enumerate(self.tokens):
            if token.id == annotation.token_id:
                # Update row
                self.table.setItem(row, 1, QTableWidgetItem(annotation.pos or "—"))
                self.table.setItem(row, 2, QTableWidgetItem(annotation.gender or "—"))
                self.table.setItem(row, 3, QTableWidgetItem(annotation.number or "—"))
                self.table.setItem(row, 4, QTableWidgetItem(annotation.case or "—"))
                self.table.setItem(
                    row, 5, QTableWidgetItem(annotation.declension or "—")
                )
                self.table.setItem(
                    row, 6, QTableWidgetItem(annotation.pronoun_type or "—")
                )
                self.table.setItem(
                    row, 7, QTableWidgetItem(annotation.verb_class or "—")
                )
                self.table.setItem(
                    row, 8, QTableWidgetItem(annotation.verb_form or "—")
                )
                self.table.setItem(
                    row, 9, QTableWidgetItem(annotation.prep_case or "—")
                )
                break

    def get_selected_token(self) -> Token | None:
        """
        Get currently selected token.

        - If there is no selected token, return ``None``.
        - If there is a selected token, return the selected token.

        Returns:
            Selected :class:`~oeapp.models.token.Token` object or ``None``

        """
        row = self.table.currentRow()
        if 0 <= row < len(self.tokens):
            return self.tokens[row]
        return None

    def select_token(self, token_index: int) -> None:
        """
        Select a token by index, if the index is valid.  If the index is not
        valid, do nothing.

        Args:
            token_index: Index of the :class:`~oeapp.models.token.Token` object
                to select

        """
        # If the token index is valid, select the row.
        if 0 <= token_index < len(self.tokens):
            self.table.selectRow(token_index)
