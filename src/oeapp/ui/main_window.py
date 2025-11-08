"""Main application window."""

import sqlite3
import sys
from pathlib import Path
from typing import Final

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
)
from src.oeapp.models.annotation import Annotation
from src.oeapp.models.sentence import Sentence
from src.oeapp.models.token import Token
from src.oeapp.services.autosave import AutosaveService
from src.oeapp.services.commands import CommandManager
from src.oeapp.services.db import Database
from src.oeapp.services.export_docx import DOCXExporter
from src.oeapp.services.filter import FilterService
from src.oeapp.services.splitter import split_sentences, tokenize
from src.oeapp.ui.filter_dialog import FilterDialog
from src.oeapp.ui.help_dialog import HelpDialog
from src.oeapp.ui.sentence_card import SentenceCard


class MainMenu:
    """Main application menu."""

    def __init__(self, main_window: QMainWindow) -> None:
        """
        Initialize main menu.

        Args:
            main_window: Main window instance

        """
        #: Main window instance
        self.main_window = main_window
        #: Menu bar
        self.menu = self.main_window.menuBar()

    def add_file_menu(self) -> None:
        """
        Create file menu.

        This means adding a "File" menu to :attr:`self.menu`, the main menu bar,
        with the following actions:

        - New Project...
        - Open Project...
        - Save
        - Export...
        - Filter Annotations...

        """
        file_menu = self.menu.addMenu("&File")

        new_action = QAction("&New Project...", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project...", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        export_action = QAction("&Export...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self.export_project)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        filter_action = QAction("&Filter Annotations...", self)
        filter_action.setShortcut(QKeySequence("Ctrl+F"))
        filter_action.triggered.connect(self.show_filter_dialog)
        file_menu.addAction(filter_action)

    def add_help_menu(self) -> None:
        """
        Create help menu.

        This means adding a "Help" menu to :attr:`self.menu`, the main menu bar,
        with the following actions:

        - Help
        """
        help_menu = self.menu.addMenu("&Help")

        help_action = QAction("&Help", self)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(self.main_window.show_help)
        help_menu.addAction(help_action)

    def build(self) -> None:
        """Build the main menu."""
        self.add_file_menu()
        self.add_help_menu()


class MainWindow(QMainWindow):
    """Main application window."""

    #: Database name in what directory we need to store the database
    DB_NAME: Final[str] = "default.db"

    def __init__(self) -> None:
        """Initialize main window."""
        super().__init__()
        self.db: Database | None = None
        #: Current project ID
        self.current_project_id: int | None = None
        #: Sentence cards
        self.sentence_cards: list[SentenceCard] = []
        #: Autosave service
        self.autosave_service: AutosaveService | None = None
        #: Command manager
        self.command_manager: CommandManager | None = None
        #: Filter service
        self.filter_service: FilterService | None = None

        # Build the main window
        self.build()

    def _setup_main_window(self) -> None:
        """Set up the main window."""
        self.setWindowTitle("Old English Annotator")
        self.setGeometry(100, 100, 1200, 800)
        # Central widget with scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area = scroll_area
        self.setCentralWidget(scroll_area)
        # Status bar for autosave status
        self.statusBar().showMessage("Ready")
        # Initial message
        welcome_label = QLabel(
            "Welcome to Old English Annotator\n\nUse File → New Project to get started"
        )
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("font-size: 14pt; color: #666; padding: 50px;")
        self.content_layout.addWidget(welcome_label)

    def _setup_main_menu(self) -> None:
        """Set up the main menu."""
        menu = MainMenu(self)
        menu.build()

    def build(self) -> None:
        """Build the main window."""
        self._setup_main_window()
        self._setup_main_menu()
        self._setup_global_shortcuts()

    def _setup_global_shortcuts(self) -> None:
        """
        Set up global keyboard shortcuts for navigation.

        The following shortcuts are set up:
        - J/K for next/previous sentence
        - T for focus translation
        - Undo: Ctrl+Z
        - Redo: Ctrl+R or Ctrl+Shift+R
        """
        # J/K for next/previous sentence
        next_sentence_shortcut = QShortcut(QKeySequence("J"), self)
        next_sentence_shortcut.activated.connect(self._next_sentence)
        prev_sentence_shortcut = QShortcut(QKeySequence("K"), self)
        prev_sentence_shortcut.activated.connect(self._prev_sentence)

        # T for focus translation
        focus_translation_shortcut = QShortcut(QKeySequence("T"), self)
        focus_translation_shortcut.activated.connect(self._focus_translation)

        # Undo/Redo shortcuts
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self._undo)
        redo_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        redo_shortcut.activated.connect(self._redo)
        redo_shortcut_alt = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        redo_shortcut_alt.activated.connect(self._redo)

    def _next_sentence(self) -> None:
        """
        Navigate to next sentence.

        - If no sentence card is focused, the first sentence card is focused.
        - If the last sentence card is focused, the last sentence card is focused.

        """
        if not self.sentence_cards:
            self.sentence_cards[0].token_table.table.setFocus()
            self.sentence_cards[0].token_table.select_token(0)
            return
        # Find currently focused sentence card
        current_index = -1
        for i, card in enumerate(self.sentence_cards):
            if card.hasFocus() or card.token_table.table.hasFocus():
                current_index = i
                break
        if current_index >= 0 and current_index < len(self.sentence_cards) - 1:
            self.sentence_cards[current_index + 1].token_table.table.setFocus()
            self.sentence_cards[current_index + 1].token_table.select_token(0)

    def _prev_sentence(self) -> None:
        """
        Navigate to previous sentence.

        - If no sentence card is focused, the last sentence card is focused.
        - If the first sentence card is focused, the first sentence card is focused.

        """
        if not self.sentence_cards:
            self.sentence_cards[-1].token_table.table.setFocus()
            self.sentence_cards[-1].token_table.select_token(0)
            return
        # Find currently focused sentence card
        current_index = -1
        for i, card in enumerate(self.sentence_cards):
            if card.hasFocus() or card.token_table.table.hasFocus():
                current_index = i
                break
        if current_index > 0:
            self.sentence_cards[current_index - 1].token_table.table.setFocus()
            self.sentence_cards[current_index - 1].token_table.select_token(0)

    def _focus_translation(self) -> None:
        """
        Focus translation field of current sentence.

        - If there is no sentence card focused, do nothing.
        - If no sentence card is focused, the translation field of the last
          sentence card is focused.
        - If the translation field of the last sentence card is focused, the
          translation field of the first sentence card is focused.

        """
        if not self.sentence_cards:
            return
        for card in self.sentence_cards:
            if card.hasFocus() or card.token_table.table.hasFocus():
                card.translation_edit.setFocus()
                break

    def _undo(self) -> None:
        """
        Undo last action.

        - If there is no command manager or the command manager cannot undo, do nothing.
        - If the command manager can undo, undo the last action.
        - If the undo fails, show a message in the status bar.
        """
        if self.command_manager and self.command_manager.can_undo():
            if self.command_manager.undo():
                self.statusBar().showMessage("Undone", 2000)
                self._refresh_all_cards()
            else:
                self.statusBar().showMessage("Undo failed", 2000)

    def _redo(self) -> None:
        """
        Redo last undone action.

        - If there is no command manager or the command manager cannot redo, do nothing.
        - If the command manager can redo, redo the last action.
        - If the redo fails, show a message in the status bar.
        """
        if self.command_manager and self.command_manager.can_redo():
            if self.command_manager.redo():
                self.statusBar().showMessage("Redone", 2000)
                self._refresh_all_cards()
            else:
                self.statusBar().showMessage("Redo failed", 2000)

    def _refresh_all_cards(self) -> None:
        """
        Refresh all sentence cards from database.

        - If there is no database or the current project ID is not set, do nothing.
        - Reload annotations for all sentence cards.
        """
        if not self.db or not self.current_project_id:
            return
        # Reload annotations for all cards
        for card in self.sentence_cards:
            if card.sentence.id:
                self._load_card_annotations(card)

    def _load_card_annotations(self, card: SentenceCard) -> None:
        """
        Load annotations for a sentence card from database.

        - If there is no database or the sentence card has no ID, do nothing.
        - Load annotations for all tokens in the sentence card.

        Args:
            card: Sentence card to load annotations for

        """
        if not self.db or not card.sentence.id:
            return
        cursor = self.db.conn.cursor()
        annotations = {}
        for token in card.tokens:
            cursor.execute("SELECT * FROM annotations WHERE token_id = ?", (token.id,))
            row = cursor.fetchone()
            if row:
                ann = Annotation(
                    token_id=token.id,
                    pos=row["pos"],
                    gender=row["gender"],
                    number=row["number"],
                    case=row["case"],
                    declension=row["declension"],
                    pronoun_type=row["pronoun_type"],
                    verb_class=row["verb_class"],
                    verb_tense=row["verb_tense"],
                    verb_person=row["verb_person"],
                    verb_mood=row["verb_mood"],
                    verb_aspect=row["verb_aspect"],
                    verb_form=row["verb_form"],
                    prep_case=row["prep_case"],
                    uncertain=bool(row["uncertain"]),
                    alternatives_json=row["alternatives_json"],
                    confidence=row["confidence"],
                )
                annotations[token.id] = ann
        card.set_tokens(card.tokens, annotations)

    def new_project(self) -> None:
        """
        Create a new project.

        - If the user cancels the dialog, do nothing.
        - If the user enters valid Old English text, create a new project from the text.

        """
        dialog = QDialog(self)
        dialog.setWindowTitle("New Project")
        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setPlaceholderText("Paste Old English text here...")
        text_edit.setMinimumHeight(200)
        layout.addWidget(QLabel("Old English Text:"))
        layout.addWidget(text_edit)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec():
            text = text_edit.toPlainText()
            if text.strip():
                self._create_project_from_text(text)

    def _get_project_db_path(self) -> Path:
        """
        Get the path to the project database.

        - On Windows, the database is created in the user's
            ``AppData/Local/oe_annotator/projects`` directory.
        - On macOS, the database is created in the user's
            ``~/Library/Application Support/oe_annotator/projects`` directory.
        - On Linux, the database is created in the user's
            ``~/.config/oe_annotator/projects`` directory.
        - If the platform is not supported, raise a ValueError.

        """
        if sys.platform not in ["win32", "darwin", "linux"]:
            msg = f"Unsupported platform: {sys.platform}"
            raise ValueError(msg)
        if sys.platform == "win32":
            db_path = Path.home() / "AppData" / "Local" / "oe_annotator" / "projects"
        elif sys.platform == "darwin":
            db_path = (
                Path.home()
                / "Library"
                / "Application Support"
                / "oe_annotator"
                / "projects"
            )
        elif sys.platform == "linux":
            db_path = Path.home() / ".config" / "oe_annotator" / "projects"
            return Path.home() / ".config" / "oe_annotator" / "projects"
        db_path.mkdir(parents=True, exist_ok=True)
        return db_path / self.DB_NAME

    def _create_project_from_text(self, text: str):
        """
        Create project from text input.

        - If the text is empty, do nothing.
        - If the text is not empty, create a new project from the text.

        Args:
            text: Old English text to process

        """
        # Create database in an OS appropriate location
        self.db = Database(self._get_project_db_path())

        # Initialize autosave and command manager
        self.autosave_service = AutosaveService(self._perform_autosave)
        self.command_manager = CommandManager(self.db)
        self.filter_service = FilterService(self.db)

        # Create project
        cursor = self.db.conn.cursor()
        cursor.execute("INSERT INTO projects (name) VALUES (?)", ("Untitled Project",))
        self.current_project_id = cursor.lastrowid
        self.db.conn.commit()

        # Split into sentences
        sentences_text = split_sentences(text)
        self.sentence_cards = []

        # Clear existing content
        for i in reversed(range(self.content_layout.count())):
            self.content_layout.itemAt(i).widget().setParent(None)

        # Create sentence cards
        for order, sentence_text in enumerate(sentences_text, 1):
            # Insert sentence into database
            cursor.execute(
                "INSERT INTO sentences (project_id, display_order, text_oe) VALUES (?, ?, ?)",  # noqa: E501
                (self.current_project_id, order, sentence_text),
            )
            sentence_id = cursor.lastrowid

            # Tokenize sentence
            token_strings = tokenize(sentence_text)
            tokens = []
            for token_index, token_surface in enumerate(token_strings):
                cursor.execute(
                    "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",  # noqa: E501
                    (sentence_id, token_index, token_surface),
                )
                token_id = cursor.lastrowid
                tokens.append(
                    Token(
                        id=token_id,
                        sentence_id=sentence_id,
                        order_index=token_index,
                        surface=token_surface,
                    )
                )

            self.db.conn.commit()

            # Create sentence model
            sentence = Sentence(
                id=sentence_id,
                project_id=self.current_project_id,
                display_order=order,
                text_oe=sentence_text,
            )

            # Create sentence card
            card = SentenceCard(
                sentence, db=self.db, command_manager=self.command_manager
            )
            card.set_tokens(tokens)
            # Connect autosave signals
            card.translation_edit.textChanged.connect(self._on_translation_changed)
            card.oe_text_edit.textChanged.connect(self._on_sentence_text_changed)
            self.sentence_cards.append(card)
            self.content_layout.addWidget(card)

        self.setWindowTitle("Old English Annotator - Untitled Project")
        self.statusBar().showMessage("Project created", 2000)

    def _on_translation_changed(self) -> None:
        """
        Handle translation text change by autosaving.
        """
        if self.autosave_service:
            self.statusBar().showMessage("Saving...", 500)
            self.autosave_service.trigger()

    def _on_sentence_text_changed(self):
        """
        Handle sentence text change by autosaving.
        """
        if self.autosave_service:
            self.statusBar().showMessage("Saving...", 500)
            self.autosave_service.trigger()

    def _perform_autosave(self):
        """
        Perform autosave operation.
        """
        if not self.db:
            return
        try:
            # Save sentence text and translations
            cursor = self.db.conn.cursor()
            for card in self.sentence_cards:
                if card.sentence.id:
                    cursor.execute(
                        "UPDATE sentences SET text_oe = ?, text_modern = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",  # noqa: E501
                        (card.get_oe_text(), card.get_translation(), card.sentence.id),
                    )
            self.db.conn.commit()
        except sqlite3.Error as e:
            self.statusBar().showMessage(f"Save error: {e}", 5000)
            print(f"Autosave error: {e}")
        else:
            self.statusBar().showMessage("Saved", 2000)

    def open_project(self) -> None:
        """
        Open an existing project.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            str(self._get_project_db_path()[:-1]),
            "Database Files (*.db);",
        )
        self.db = Database(file_path)

        # Initialize autosave and command manager
        self.autosave_service = AutosaveService(self._perform_autosave)
        self.command_manager = CommandManager(self.db)
        self.filter_service = FilterService(self.db)

        # We need to create the sentence cards from the database

    def save_project(self) -> None:
        """
        Save current project.
        """
        if not self.db:
            QMessageBox.warning(self, "Warning", "No project open")
            return
        if self.autosave_service:
            self.autosave_service.save_now()
            self.statusBar().showMessage("Project saved", 2000)
        else:
            QMessageBox.information(self, "Info", "Project saved (autosave enabled)")

    def export_project(self) -> None:
        """Export project to DOCX."""
        if not self.db:
            QMessageBox.warning(self, "Warning", "No project open")
            return

        # Get file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Project", "", "Word Documents (*.docx);;All Files (*)"
        )

        if not file_path:
            return

        # Ensure .docx extension
        if not file_path.endswith(".docx"):
            file_path += ".docx"

        try:
            exporter = DOCXExporter(self.db)
            if exporter.export(self.current_project_id, Path(file_path)):
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Project exported successfully to:\n{file_path}",
                )
                self.statusBar().showMessage("Export completed", 3000)
            else:
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    "Failed to export project. Check console for details.",
                )
        except Exception as e:
            QMessageBox.critical(
                self, "Export Error", f"An error occurred during export:\n{e!s}"
            )
            print(f"Export error: {e}")

    def show_help(self, topic: str | None = None) -> None:
        """
        Show help dialog.

        Args:
            topic: Optional topic to display initially

        """
        dialog = HelpDialog(topic=topic, parent=self)
        dialog.exec()

    def show_filter_dialog(self) -> None:
        """
        Show filter dialog.
        """
        if not self.db or not self.current_project_id:
            QMessageBox.warning(
                self, "No Project", "Please create or open a project first."
            )
            return

        dialog = FilterDialog(self.filter_service, self.current_project_id, parent=self)
        dialog.token_selected.connect(self._navigate_to_token)
        dialog.exec()

    def _navigate_to_token(self, token_id: int) -> None:
        """
        Navigate to a specific token.

        Args:
            token_id: Token ID to navigate to

        """
        if not self.db:
            return

        # Find the sentence containing this token
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT s.id, s.display_order, t.order_index
            FROM tokens t
            JOIN sentences s ON t.sentence_id = s.id
            WHERE t.id = ?
        """,
            (token_id,),
        )
        row = cursor.fetchone()
        if not row:
            return

        sentence_id = row["id"]

        # Find the sentence card
        for card in self.sentence_cards:
            if card.sentence.id == sentence_id:
                # Scroll to the card
                self.scroll_area.ensureWidgetVisible(card)
                # Select the token by finding it in the tokens list
                token_idx = None
                for idx, token in enumerate(card.tokens):
                    if token.id == token_id:
                        token_idx = idx
                        break
                if token_idx is not None:
                    card.token_table.table.setFocus()
                    card.token_table.select_token(token_idx)
                    # Open annotation modal
                    card._open_annotation_modal()
                break
