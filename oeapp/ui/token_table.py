"""Token table UI component."""

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QKeyEvent,
    QKeySequence,
    QShortcut,
    QShowEvent,
)  # Needed at runtime
from PySide6.QtWidgets import (
    QHeaderView,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from oeapp.models.token import Token

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation


class AnnotationTableWidget(QTableWidget):
    """
    Custom QTableWidget that intercepts "A" key to open annotation dialog.

    This prevents QTableWidget's incremental search from handling "A" key
    when a token is selected.
    """

    annotation_key_pressed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the custom table widget."""
        super().__init__(parent)
        self._token_table_ref: TokenTable | None = None  # Will be set by TokenTable

    def set_token_table_ref(self, token_table: TokenTable) -> None:
        """
        Set reference to parent :class:`TokenTable` for checking selected token.

        Args:
            token_table: Reference to parent :class:`TokenTable`

        """
        self._token_table_ref = token_table

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """
        Override keyPressEvent to intercept "Shift+A" key. and emit
        annotation_key_pressed signal.  This is used to open the annotation
        modal when a token is selected.

        If the key is not "Shift+A", use default behavior (including incremental
        search).

        If no token is selected, allow default behavior (including incremental
        search).

        Args:
            event: Key event

        """
        if (
            event.key() == Qt.Key.Key_A
            and event.modifiers() == Qt.KeyboardModifier.ShiftModifier
        ):
            # Check if a token is selected before handling
            if self._token_table_ref:
                token = self._token_table_ref.get_selected_token()
                if token:
                    # Emit signal to request annotation
                    self.annotation_key_pressed.emit()
                    # Accept the event to prevent further processing
                    event.accept()
                    return
            # If no token selected, allow default behavior (incremental search)
        # For all other keys, use default behavior (including incremental search)
        super().keyPressEvent(event)


class TokenTable(QWidget):
    """
    Widget displaying token annotation grid.

    Args:
        parent: Parent widget

    """

    #: Signal emitted when a token is selected.
    token_selected = Signal(Token)
    #: Signal emitted when annotation is requested for a token (e.g. when "A"
    #: key is pressed on the table widget).
    annotation_requested = Signal(Token)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        #: The tokens to display.
        self.tokens: list[Token] = []
        #: The annotations to display.
        self.annotations: dict[int, Annotation] = {}  # token_id -> Annotation
        self._setup_ui()

    def _setup_ui(self) -> None:
        """
        Set up the UI layout.

        This looks like this:
        +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
        | Word   | POS    | ModE   | Root   | Gender | Number | Case   | Declension | PronounType | VerbClass | VerbForm | PrepObjCase |
        +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
        | Token 1 | POS 1 | ModE 1 | Root 1 | Gender 1 | Number 1 | Case 1 | Declension 1 | PronounType 1 | VerbClass 1 | VerbForm 1 | PrepObjCase 1 |
        | Token 2 | POS 2 | ModE 2 | Root 2 | Gender 2 | Number 2 | Case 2 | Declension 2 | PronounType 2 | VerbClass 2 | VerbForm 2 | PrepObjCase 2 |
        | ...     | ...    | ...    | ...    | ...      | ...      | ...    | ...         | ...         | ...         | ...        | ...         |
        +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
        """  # noqa: E501
        # Create the layout.
        layout = QVBoxLayout(self)
        # Create the custom table widget that handles "A" key.
        self.table = AnnotationTableWidget(self)
        # Set reference to this TokenTable so the widget can check for selected token
        self.table.set_token_table_ref(self)
        # Connect the annotation key signal
        self.table.annotation_key_pressed.connect(self._on_annotation_key_pressed)
        # Set the number of columns to 12.
        self.table.setColumnCount(12)
        # Set the horizontal header labels.
        self.table.setHorizontalHeaderLabels(
            [
                "Word",
                "POS",
                "ModE",
                "Root",
                "Gender",
                "Number",
                "Case",
                "Declension",
                "PronounType",
                "VerbClass",
                "VerbForm",
                "PrepObjCase",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.table.setMinimumHeight(150)
        self.table.updateGeometry()
        # Add QShortcut for "A" key on the table widget with WidgetShortcut context
        # This should take precedence over incremental search
        annotate_shortcut = QShortcut(QKeySequence("A"), self.table)
        annotate_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        annotate_shortcut.activated.connect(self._on_annotation_key_pressed)
        layout.addWidget(self.table)
        index = layout.indexOf(self.table)
        layout.setStretch(index, 1)  # give table vertical priority

    @property
    def has_focus(self) -> bool:
        """
        Check if the token table has focus.
        """
        return self.table.hasFocus()

    @property
    def current_row(self) -> int:
        """
        Get the current row of the token table.
        """
        current_row = self.table.currentRow()
        if current_row == -1:
            return 1
        return current_row

    def focus(self) -> None:
        """
        Focus the token table.
        """
        self.table.setFocus()

    def setVisible(self, visible: bool) -> None:  # noqa: FBT001, N802
        """
        Set the visibility of the token table.

        Args:
            visible: Whether to show the token table

        """
        super().setVisible(visible)
        self.table.setVisible(visible)
        if visible:
            self.table.setUpdatesEnabled(True)
            self.table.viewport().update()  # optional, to force a repaint

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

    def _on_selection_changed(self) -> None:
        """
        Handle selection change.

        - If the selected row is not a token, do nothing.
        - If the selected row is a token, get the token and emit the
          token_selected signal.

        """
        # Get the current row of the table.
        row = self.current_row
        if 0 <= row < len(self.tokens):
            token = self.tokens[row]
            self.token_selected.emit(token)

    def _on_annotation_key_pressed(self) -> None:
        """
        Handle "A" key press on the table widget.

        Emits annotation_requested signal if a token is selected.
        """
        token = self.get_selected_token()
        if token:
            self.annotation_requested.emit(token)

    def set_tokens(self, tokens: list[Token]) -> None:
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
        # Set the number of rows to the number of tokens.
        self.table.setRowCount(len(tokens))
        # Loop through the tokens and add them to the table.

        for row, token in enumerate(tokens):
            # Word
            self.table.setItem(row, 0, QTableWidgetItem(token.surface))
            # Get annotation for this token
            annotation = token.annotation
            if annotation:
                # POS
                self.table.setItem(row, 1, QTableWidgetItem(annotation.pos or "—"))
                # ModE
                self.table.setItem(
                    row, 2, QTableWidgetItem(annotation.modern_english_meaning or "—")
                )
                # Root
                self.table.setItem(row, 3, QTableWidgetItem(annotation.root or "—"))
                # Gender
                self.table.setItem(row, 4, QTableWidgetItem(annotation.gender or "—"))
                # Number
                self.table.setItem(row, 5, QTableWidgetItem(annotation.number or "—"))
                # Case
                self.table.setItem(row, 6, QTableWidgetItem(annotation.case or "—"))
                # Declension
                self.table.setItem(
                    row, 7, QTableWidgetItem(annotation.declension or "—")
                )
                # PronounType
                self.table.setItem(
                    row, 8, QTableWidgetItem(annotation.pronoun_type or "—")
                )
                # VerbClass
                self.table.setItem(
                    row, 9, QTableWidgetItem(annotation.verb_class or "—")
                )
                # VerbForm
                self.table.setItem(
                    row, 10, QTableWidgetItem(annotation.verb_form or "—")
                )
                # PrepObjCase
                self.table.setItem(
                    row, 11, QTableWidgetItem(annotation.prep_case or "—")
                )
            else:
                # Fill with "—" for unannotated tokens
                for col in range(1, 12):
                    self.table.setItem(row, col, QTableWidgetItem("—"))

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
                # POS
                self.table.setItem(row, 1, QTableWidgetItem(annotation.pos or "—"))
                # ModE
                self.table.setItem(
                    row, 2, QTableWidgetItem(annotation.modern_english_meaning or "—")
                )
                # Root
                self.table.setItem(row, 3, QTableWidgetItem(annotation.root or "—"))
                # Gender
                self.table.setItem(row, 4, QTableWidgetItem(annotation.gender or "—"))
                # Number
                self.table.setItem(row, 5, QTableWidgetItem(annotation.number or "—"))
                # Case
                self.table.setItem(row, 6, QTableWidgetItem(annotation.case or "—"))
                # Declension
                self.table.setItem(
                    row, 7, QTableWidgetItem(annotation.declension or "—")
                )
                # PronounType
                self.table.setItem(
                    row, 8, QTableWidgetItem(annotation.pronoun_type or "—")
                )
                # VerbClass
                self.table.setItem(
                    row, 9, QTableWidgetItem(annotation.verb_class or "—")
                )
                # VerbForm
                self.table.setItem(
                    row, 10, QTableWidgetItem(annotation.verb_form or "—")
                )
                # PrepObjCase
                self.table.setItem(
                    row, 11, QTableWidgetItem(annotation.prep_case or "—")
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
        row = self.current_row
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
            # Ensure the selected row is scrolled into view
            item = self.table.item(token_index, 0)
            if item:
                self.table.scrollToItem(item)

    def refresh(self) -> None:
        """
        Refresh the table display from stored tokens.

        This repopulates the table with the tokens currently stored in self.tokens.
        Useful when the widget is shown again after being hidden.
        """
        if self.tokens:
            self.set_tokens(self.tokens)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        """
        Handle show event to refresh table when widget becomes visible.

        Args:
            event: Show event

        """
        super().showEvent(event)
        # Always refresh table when shown if we have stored tokens
        # This handles cases where Qt clears the table when hidden
        # Check if table is empty or if we have tokens to refresh
        if self.tokens and (self.table.rowCount() == 0 or not self.table.item(0, 0)):
            # Table is empty or first item is missing - refresh it
            self.refresh()
