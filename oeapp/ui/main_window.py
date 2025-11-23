"""Main application window."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from oeapp.db import SessionLocal
from oeapp.exc import MigrationFailed
from oeapp.models.project import Project
from oeapp.models.token import Token
from oeapp.services import MigrationService
from oeapp.services.autosave import AutosaveService
from oeapp.services.backup import BackupService
from oeapp.services.commands import CommandManager, MergeSentenceCommand
from oeapp.services.export_docx import DOCXExporter
from oeapp.services.filter import FilterService
from oeapp.services.import_export import ProjectExporter, ProjectImporter
from oeapp.ui.dialogs import (
    BackupsViewDialog,
    DeleteProjectDialog,
    ImportProjectDialog,
    MigrationFailureDialog,
    NewProjectDialog,
    OpenProjectDialog,
    RestoreDialog,
    SettingsDialog,
)
from oeapp.ui.filter_dialog import FilterDialog
from oeapp.ui.help_dialog import HelpDialog
from oeapp.ui.menus import MainMenu
from oeapp.ui.sentence_card import SentenceCard
from oeapp.ui.token_details_sidebar import TokenDetailsSidebar

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation
    from oeapp.models.sentence import Sentence


class MainWindow(QMainWindow):
    """Main application window."""

    #: Main window geometry
    MAIN_WINDOW_GEOMETRY: Final[tuple[int, int, int, int]] = (100, 100, 1600, 800)

    def __init__(self) -> None:
        super().__init__()
        #: Backup service
        self.backup_service = BackupService()
        #: Backup check timer
        self.backup_timer: QTimer | None = None

        # Handle migrations with backup/restore on failure
        # Note: session is created after migrations to avoid issues
        self._handle_migrations()

        #: SQLAlchemy session
        self.session = SessionLocal()
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
        #: Main window actions
        self.action_service = MainWindowActions(self)
        #: Currently selected sentence card
        self.selected_sentence_card: SentenceCard | None = None

        # Build the main window
        self.build()

        # Setup backup checking
        self._setup_backup_checking()

    def _setup_main_window(self) -> None:
        """
        Set up the main window.
        """
        self.setWindowTitle("Ænglisc Toolkit")
        # Set window icon from application icon
        app = QApplication.instance()
        if isinstance(app, QApplication) and not app.windowIcon().isNull():
            self.setWindowIcon(app.windowIcon())
        self.setGeometry(100, 100, 1600, 800)

        # Central widget with two-column layout
        central_widget = QWidget()
        central_layout = QHBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # Left column: scroll area with sentence cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area = scroll_area
        # Content widget with layout
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(content_widget)
        central_layout.addWidget(scroll_area, stretch=1)

        # Right column: token details sidebar
        self.token_details_sidebar = TokenDetailsSidebar()
        self.token_details_sidebar.setFixedWidth(350)
        self.token_details_sidebar.setStyleSheet(
            "background-color: #f5f5f5; border-left: 1px solid #ddd;"
        )
        central_layout.addWidget(self.token_details_sidebar)

        self.setCentralWidget(central_widget)

        # Status bar for autosave status
        self.show_message("Ready")
        # Initial message
        welcome_label = QLabel(
            "Welcome to Ænglisc Toolkit\n\nUse File → New Project to get started"
        )
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("font-size: 14pt; color: #666; padding: 50px;")
        self.content_layout.addWidget(welcome_label)

    def _setup_main_menu(self) -> None:
        """Set up the main menu."""
        menu = MainMenu(self)
        menu.build()

    def build(self) -> None:
        """
        Build the main window.

        - Setup the main window.
        - Setup the main menu.
        - Setup global shortcuts.

        """
        self._setup_main_window()
        self._setup_main_menu()
        self._setup_global_shortcuts()

    def _handle_migrations(self) -> None:
        """
        Handle database migrations with automatic backup and restore on failure.
        """
        settings = QSettings()
        migration_service = MigrationService()
        skip_until_version = cast(
            "str | None", settings.value("migration/skip_until_version", None, type=str)
        )
        try:
            result = migration_service.migrate(skip_until_version)
        except MigrationFailed as e:
            dialog = MigrationFailureDialog(
                self,
                e.error,
                e.backup_app_version,
            )
            settings.setValue(
                "migration/last_working_version",
                e.backup_migration_version,
            )
            dialog.execute()
            sys.exit(1)

        if result.migration_version:
            settings.setValue(
                "migration/last_working_version",
                result.migration_version,
            )
        if result.app_version:
            settings.setValue(
                "app/current_version",
                result.app_version,
            )

    def _setup_backup_checking(self) -> None:
        """Setup periodic backup checking."""
        # Check every 5 minutes if backup is needed
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self._check_backup)
        self.backup_timer.start(5 * 60 * 1000)  # 5 minutes in milliseconds

        # Also check on startup
        self._check_backup()

    def _check_backup(self) -> None:
        """Check if backup is needed and create one if so."""
        if self.backup_service.should_backup():
            backup_path = self.backup_service.create_backup()
            if backup_path:
                self.show_message("Backup created", duration=2000)

    def _show_startup_dialog(self) -> None:
        """
        Show the appropriate startup dialog based on whether projects exist.

        - If there are no projects in the database, show NewProjectDialog.
        - If there are projects, show OpenProjectDialog.
        """
        # Check if there are any projects in the database
        if bool(Project.first(self.session)):
            # Projects exist, show OpenProjectDialog
            OpenProjectDialog(self).execute()
        else:
            # No projects exist, show NewProjectDialog
            NewProjectDialog(self).execute()

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
        next_sentence_shortcut.activated.connect(self.action_service.next_sentence)
        prev_sentence_shortcut = QShortcut(QKeySequence("K"), self)
        prev_sentence_shortcut.activated.connect(self.action_service.prev_sentence)

        # T for focus translation
        focus_translation_shortcut = QShortcut(QKeySequence("T"), self)
        focus_translation_shortcut.activated.connect(
            self.action_service.focus_translation
        )

        # Undo/Redo shortcuts
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.action_service.undo)
        redo_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        redo_shortcut.activated.connect(self.action_service.redo)
        redo_shortcut_alt = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        redo_shortcut_alt.activated.connect(self.action_service.redo)

    def show_message(self, message: str, duration: int = 2000) -> None:
        """
        Show a message in the status bar.

        Args:
            message: Message to show

        Keyword Args:
            duration: Duration of the message in milliseconds (default: 2000)

        """
        self.statusBar().showMessage(message, duration)

    def show_warning(self, message: str, title: str = "Warning") -> None:
        """
        Show a warning message.

        Args:
            message: Message to show

        Keyword Args:
            title: Title of the message (default: "Warning")

        """
        QMessageBox.warning(self, title, message)

    def show_error(self, message: str, title: str = "Error") -> None:
        """
        Show an error message.

        Args:
            message: Message to show

        Keyword Args:
            title: Title of the message (default: "Error")

        """
        QMessageBox.warning(self, title, message)

    def show_information(self, message: str, title: str = "Information") -> None:
        """
        Show an information message.

        Args:
            message: Message to show

        Keyword Args:
            title: Title of the message (default: "Information")

        """
        QMessageBox.information(self, title, message)

    def ensure_visible(self, widget: QWidget) -> None:
        """
        Ensure a widget is visible.

        Args:
            widget: Widget to ensure visible

        """
        self.scroll_area.ensureWidgetVisible(widget)

    def _configure_project(self, project: Project) -> None:
        """
        Configure the app for the given project.  This means:

        - Set the current project ID
        - Initialize autosave and command manager
        - Clear existing content
        - Create new sentence cards
        - Connect signals to the sentence cards
        - Show the welcome message if there are no projects
        - Scroll to the first sentence card
        - Update the window title to the project name

        Args:
            project: Project to configure

        """
        self.current_project_id = project.id

        # Initialize autosave and command manager
        self.autosave_service = AutosaveService(self.action_service.autosave)
        self.command_manager = CommandManager(self.session)
        self.filter_service = FilterService(self.session)

        # Clear existing content
        for i in reversed(range(self.content_layout.count())):
            self.content_layout.itemAt(i).widget().setParent(None)  # type: ignore[union-attr]

        self.sentence_cards = []
        for sentence in project.sentences:
            card = SentenceCard(
                sentence, session=self.session, command_manager=self.command_manager
            )
            card.set_tokens(sentence.tokens)
            card.translation_edit.textChanged.connect(self._on_translation_changed)
            card.oe_text_edit.textChanged.connect(self._on_sentence_text_changed)
            card.sentence_merged.connect(self._on_sentence_merged)
            card.token_selected_for_details.connect(self._on_token_selected_for_details)
            card.annotation_applied.connect(self._on_annotation_applied)
            self.sentence_cards.append(card)
            self.content_layout.addWidget(card)

    def _on_translation_changed(self) -> None:
        """
        Handle translation text change by autosaving.
        """
        if self.autosave_service:
            self.show_message("Saving...", duration=500)
            self.autosave_service.trigger()

    def _on_sentence_text_changed(self):
        """
        Handle sentence text change by autosaving.
        """
        if self.autosave_service:
            self.show_message("Saving...", duration=500)
            self.autosave_service.trigger()

    def save_project(self) -> None:
        """
        Save current project.
        """
        if not self.session or not self.current_project_id:
            self.show_warning("No project open")
            return
        if self.autosave_service:
            self.autosave_service.save_now()
            self.show_message("Project saved")
        else:
            self.show_information("Project saved (autosave enabled)", title="Info")

    def show_help(self, topic: str | None = None) -> None:
        """
        Show help dialog.

        Args:
            topic: Optional topic to display initially

        """
        dialog = HelpDialog(topic=topic, parent=self)
        dialog.show()

    def show_filter_dialog(self) -> None:
        """
        Show filter dialog.
        """
        if not self.session or not self.current_project_id:
            self.show_warning(
                "Please create or open a project first.", title="No Project"
            )
            return

        dialog = FilterDialog(
            cast("FilterService", self.filter_service),
            self.current_project_id,
            parent=self,
        )
        dialog.token_selected.connect(self.action_service.navigate_to_token)
        dialog.exec()

    def show_settings_dialog(self) -> None:
        """
        Show settings dialog.
        """
        dialog = SettingsDialog(self)
        dialog.execute()

    def show_restore_dialog(self) -> None:
        """
        Show restore dialog.
        """
        dialog = RestoreDialog(self)
        dialog.execute()
        # After restore, we may need to reload
        if self.current_project_id:
            project = Project.get(self.session, self.current_project_id)
            if project:
                self._configure_project(project)

    def show_backups_dialog(self) -> None:
        """
        Show backups view dialog.
        """
        dialog = BackupsViewDialog(self)
        dialog.execute()

    def export_project_json(
        self, project_id: int | None = None, parent: QWidget | None = None
    ) -> bool:
        """
        Export project to JSON format.

        Args:
            project_id: Optional project ID to export. If not provided, uses
                current_project_id.
            parent: Optional parent widget for the file dialog. If not provided,
                uses self.

        Returns:
            True if export was successful, False if canceled or failed

        """
        # Use provided project_id or fall back to current_project_id
        target_project_id = (
            project_id if project_id is not None else self.current_project_id
        )

        if not self.session or not target_project_id:
            self.show_warning("No project open")
            return False

        # Get project name for default filename
        project = Project.get(self.session, target_project_id)
        if project is None:
            self.show_warning("Project not found")
            return False

        default_filename = ProjectExporter.sanitize_filename(project.name) + ".json"

        # Get file path from user
        dialog_parent = parent if parent is not None else self
        file_path, _ = QFileDialog.getSaveFileName(
            dialog_parent,
            "Export Project",
            default_filename,
            "JSON Files (*.json);;All Files (*)",
        )

        # If the user cancels the dialog, do nothing
        if not file_path:
            return False

        # Export project data
        exporter = ProjectExporter(self.session)
        try:
            exporter.export_project_json(target_project_id, file_path)
        except ValueError as e:
            self.show_error(str(e), title="Export Error")
            return False

        self.show_information(
            f"Project exported successfully to:\n{file_path}",
            title="Export Successful",
        )
        self.show_message("Export completed", duration=3000)
        return True

    def _on_sentence_merged(self) -> None:
        """
        Handle sentence merge signal.

        Reloads the project from the database to refresh all sentence cards
        after a merge operation.

        """
        if not self.session or not self.current_project_id:
            return

        # Reload project from database
        project = Project.get(self.session, self.current_project_id)
        if project is None:
            return

        # Preserve existing command manager to keep undo history
        existing_command_manager = self.command_manager
        existing_autosave = self.autosave_service
        existing_filter = self.filter_service

        # Refresh the project configuration (reloads all sentence cards)
        self._configure_project(project)

        # Restore preserved services
        if existing_command_manager:
            self.command_manager = existing_command_manager
        if existing_autosave:
            self.autosave_service = existing_autosave
        if existing_filter:
            self.filter_service = existing_filter

        # Update all sentence cards to use the preserved command manager
        for card in self.sentence_cards:
            card.command_manager = self.command_manager

        # Ensure UI is updated/repainted
        self.scroll_area.update()
        self.update()

        self.show_message("Sentences merged", duration=2000)

    def _on_token_selected_for_details(
        self, token: Token, sentence: Sentence, sentence_card: SentenceCard
    ) -> None:
        """
        Handle token selection for details sidebar.

        Args:
            token: Selected token
            sentence: Sentence containing the token
            sentence_card: Sentence card containing the token

        """
        # If there's a previously selected sentence card (different from current),
        # clear its selection
        if self.selected_sentence_card and self.selected_sentence_card != sentence_card:
            self.selected_sentence_card._clear_token_selection()

        # Check if token is being deselected (selected_token_index is None)
        if sentence_card.selected_token_index is None:
            # Clear sidebar
            self.token_details_sidebar.clear()
            self.selected_sentence_card = None
        else:
            # Update sidebar with token details
            self.token_details_sidebar.update_token(token, sentence)

            # Store reference to currently selected sentence card
            self.selected_sentence_card = sentence_card

    def _on_annotation_applied(self, annotation: Annotation) -> None:
        """
        Handle annotation applied signal.

        If the annotation is for the currently selected token in the sidebar,
        refresh the sidebar.

        Args:
            annotation: Applied annotation

        """
        # Check if this annotation is for the currently selected token
        if (
            self.selected_sentence_card
            and self.selected_sentence_card.selected_token_index is not None
        ):
            token_index = self.selected_sentence_card.selected_token_index
            if (
                token_index < len(self.selected_sentence_card.tokens)
                and self.selected_sentence_card.tokens[token_index].id
                == annotation.token_id
            ):
                # Refresh sidebar with updated annotation
                token = self.selected_sentence_card.tokens[token_index]
                # Refresh token from database to ensure annotation relationship is up-to-date
                if self.session:
                    self.session.refresh(token)
                self.token_details_sidebar.update_token(
                    token, self.selected_sentence_card.sentence
                )


class MainWindowActions:
    """
    Main window actions.  We separate the work from the UI to make the code more
    readable and maintainable.

    Args:
        main_window: Main window instance

    """

    def __init__(self, main_window: MainWindow) -> None:
        """
        Initialize main window actions.
        """
        self.main_window = main_window
        #: SQLAlchemy session
        self.session = main_window.session
        #: Sentence cards (reference to main_window's list)
        self.sentence_cards = main_window.sentence_cards
        #: Filter service

    @property
    def command_manager(self):
        """Get the current command manager from main window."""
        return self.main_window.command_manager

    @property
    def autosave_service(self):
        """Get the current autosave service from main window."""
        return self.main_window.autosave_service

    def next_sentence(self) -> None:
        """
        Navigate to next sentence.

        - If no sentence card is focused, the first sentence card is focused.
        - If the last sentence card is focused, the last sentence card is focused.

        """
        if not self.sentence_cards:
            self.sentence_cards[0].focus()
            return
        # Find currently focused sentence card
        current_index = -1
        for i, card in enumerate(self.sentence_cards):
            if card.has_focus:
                current_index = i
                break
        if current_index >= 0 and current_index < len(self.sentence_cards) - 1:
            self.sentence_cards[current_index + 1].focus()

    def prev_sentence(self) -> None:
        """
        Navigate to previous sentence.

        - If no sentence card is focused, the last sentence card is focused.
        - If the first sentence card is focused, the first sentence card is focused.

        """
        if not self.sentence_cards:
            self.sentence_cards[-1].focus()
            return
        # Find currently focused sentence card
        current_index = -1
        for i, card in enumerate(self.sentence_cards):
            if card.has_focus:
                current_index = i
                break
        if current_index > 0:
            self.sentence_cards[current_index - 1].focus()

    def focus_translation(self) -> None:
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
            if card.has_focus:
                card.focus_translation()
                break

    def undo(self) -> None:
        """
        Undo last action.

        - If there is no command manager or the command manager cannot undo, do nothing.
        - If the command manager can undo, undo the last action.
        - If the undo fails, show a message in the status bar.
        """
        if self.command_manager and self.command_manager.can_undo():
            # Check if the command to undo is a structural change (like merge)
            needs_full_reload = False
            if self.command_manager.undo_stack:
                last_command = self.command_manager.undo_stack[-1]
                if isinstance(last_command, MergeSentenceCommand):
                    needs_full_reload = True

            if self.command_manager.undo():
                self.main_window.show_message("Undone")
                # After undo, the command is in redo_stack, check if it was a merge
                if not needs_full_reload and self.command_manager.redo_stack:
                    last_undone = self.command_manager.redo_stack[-1]
                    if isinstance(last_undone, MergeSentenceCommand):
                        needs_full_reload = True

                if needs_full_reload:
                    # Reload entire project structure after structural change
                    self._reload_project_structure()
                else:
                    self.refresh_all_cards()
            else:
                self.main_window.show_message("Undo failed")

    def redo(self) -> None:
        """
        Redo last undone action.

        - If there is no command manager or the command manager cannot redo, do nothing.
        - If the command manager can redo, redo the last action.
        - If the redo fails, show a message in the status bar.
        """
        if self.command_manager and self.command_manager.can_redo():
            # Check if the command to redo is a structural change (like merge)
            needs_full_reload = False
            if self.command_manager.redo_stack:
                last_command = self.command_manager.redo_stack[-1]
                if isinstance(last_command, MergeSentenceCommand):
                    needs_full_reload = True

            if self.command_manager.redo():
                self.main_window.show_message("Redone")
                # After redo, the command is in undo_stack, check if it was a merge
                if not needs_full_reload and self.command_manager.undo_stack:
                    last_redone = self.command_manager.undo_stack[-1]
                    if isinstance(last_redone, MergeSentenceCommand):
                        needs_full_reload = True

                if needs_full_reload:
                    # Reload entire project structure after structural change
                    self._reload_project_structure()
                else:
                    self.refresh_all_cards()
            else:
                self.main_window.show_message("Redo failed")

    def refresh_all_cards(self) -> None:
        """
        Refresh all sentence cards from database.

        - If there is no database or the current project ID is not set, do nothing.
        - Reload annotations for all sentence cards.
        """
        if not self.session or not self.main_window.current_project_id:
            return
        # Reload annotations for all cards
        for card in self.sentence_cards:
            if card.sentence.id:
                card.set_tokens(card.sentence.tokens)

    def _reload_project_structure(self) -> None:
        """
        Reload the entire project structure from database.

        This is needed after structural changes like merge/undo merge
        that change the number of sentences.
        """
        if not self.main_window.session or not self.main_window.current_project_id:
            return

        # Reload project from database
        project = Project.get(
            self.main_window.session, self.main_window.current_project_id
        )
        if project is None:
            return

        # Preserve existing services
        existing_command_manager = self.main_window.command_manager
        existing_autosave = self.main_window.autosave_service
        existing_filter = self.main_window.filter_service

        # Refresh the project configuration (reloads all sentence cards)
        self.main_window._configure_project(project)

        # Restore preserved services
        if existing_command_manager:
            self.main_window.command_manager = existing_command_manager
        if existing_autosave:
            self.main_window.autosave_service = existing_autosave
        if existing_filter:
            self.main_window.filter_service = existing_filter

        # Update all sentence cards to use the preserved command manager
        for card in self.main_window.sentence_cards:
            card.command_manager = self.main_window.command_manager

        # Ensure UI is updated/repainted
        self.main_window.scroll_area.update()
        self.main_window.update()

    def autosave(self) -> None:
        """
        Do an autosave operation.

        - If there is no database or the current project ID is not set, do nothing.
        - Save the current project.
        - Show a message in the status bar that the project has been saved.

        """
        assert self.session is not None, "Session not initialized"  # noqa: S101
        assert self.main_window.current_project_id is not None, (  # noqa: S101
            "Current project ID not set"
        )
        if (
            project := Project.get(
                self.main_window.session, self.main_window.current_project_id
            )
            is None
        ):
            return
        self.session.add(project)
        self.session.commit()
        self.main_window.show_message("Saved")

    def navigate_to_token(self, token_id: int) -> None:
        """
        Navigate to a specific token.

        - If there is no database or the current project ID is not set, do nothing.
        - If there is no token with the given ID, do nothing.
        - If there is a token with the given ID, navigate to the token.

        Args:
            token_id: Token ID to navigate to

        """
        token = Token.get(self.session, token_id)
        if token is None:
            return
        sentence_id = token.sentence_id

        # Find the sentence card
        for card in self.sentence_cards:
            if card.sentence.id == sentence_id:
                # Scroll to the card
                self.main_window.ensure_visible(card)
                # Select the token by finding it in the tokens list
                token_idx = None
                for idx, token in enumerate(card.tokens):
                    if token.id == token_id:
                        token_idx = idx
                        break
                if token_idx is not None:
                    card.token_table.focus()
                    card.token_table.select_token(token_idx)
                    # Open annotation modal
                    card._open_annotation_modal()
                break

    def import_project_json(self) -> None:
        """
        Import project from JSON format.
        """
        if not self.session:
            self.main_window.show_warning("Database session not available")
            return

        # Get file path from user
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Import Project", "", "JSON Files (*.json);;All Files (*)"
        )

        # If the user cancels the dialog, do nothing
        if not file_path:
            return

        try:
            # Import project
            imported_project, was_renamed = ProjectImporter(
                self.session
            ).import_project_json(file_path)

            # Show confirmation dialog
            dialog = ImportProjectDialog(
                self.main_window, imported_project, was_renamed
            )
            if dialog.execute():
                # User chose to open the project
                self.main_window._configure_project(imported_project)
                self.main_window.setWindowTitle(
                    f"Ænglisc Toolkit - {imported_project.name}"
                )
                self.main_window.show_message(
                    "Project imported and opened", duration=3000
                )
            else:
                self.main_window.show_message(
                    "Project imported successfully", duration=2000
                )

        except ValueError as e:
            self.main_window.show_error(str(e), title="Import Error")
        except Exception as e:  # noqa: BLE001
            self.main_window.show_error(
                f"An error occurred during import:\n{e!s}", title="Import Error"
            )

    def delete_project(self) -> None:
        """
        Delete a project from the database.

        Creates a backup before deletion and opens DeleteProjectDialog.
        """
        # Create backup before any destructive action
        backup_path = self.main_window.backup_service.create_backup()
        if not backup_path:
            self.main_window.show_error(
                "Failed to create backup. Deletion cancelled for safety.",
                title="Backup Failed",
            )
            return

        # Open delete project dialog
        dialog = DeleteProjectDialog(self.main_window)
        dialog.execute()

    def export_project_docx(self) -> None:
        """
        Export project to DOCX.
        """
        if not self.session or not self.main_window.current_project_id:
            self.main_window.show_warning("No project open")
            return

        # Get file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Export Project",
            "",
            "Word Documents (*.docx);;All Files (*)",
        )

        # If the user cancels the dialog, do nothing.
        if not file_path:
            return

        # Ensure .docx extension
        if not file_path.endswith(".docx"):
            file_path += ".docx"

        exporter = DOCXExporter(self.session)
        try:
            export_success = exporter.export(
                self.main_window.current_project_id, Path(file_path)
            )
        except PermissionError as e:
            self.main_window.show_error(
                f"Export failed: Permission denied.\n{e!s}",
                title="Export Error",
            )
            return
        except OSError as e:
            self.main_window.show_error(
                f"Export failed: File not found.\n{e!s}",
                title="Export Error",
            )
            return

        if export_success:
            self.main_window.show_information(
                f"Project exported successfully to:\n{file_path}",
                title="Export Successful",
            )
            self.main_window.show_message("Export completed", duration=3000)
        else:
            self.main_window.show_warning(
                "Failed to export project. Check console for details.",
                title="Export Failed",
            )

    def backup_now(self) -> None:
        """
        Create a backup immediately.

        - Create a backup
        - Show a message in the status bar that the backup has been created

        """
        backup_path = self.main_window.backup_service.create_backup()
        if backup_path:
            self.main_window.show_information(
                f"Backup created successfully:\n{backup_path.name}",
                title="Backup Complete",
            )
            self.main_window.show_message("Backup created", duration=2000)
        else:
            self.main_window.show_error("Failed to create backup.")
