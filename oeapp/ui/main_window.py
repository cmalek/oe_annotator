"""Main application window."""

import json
import sys
from pathlib import Path
from typing import Final, cast

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from oeapp.db import SessionLocal, apply_migrations, create_engine_with_path
from oeapp.models.project import Project
from oeapp.models.token import Token
from oeapp.services.autosave import AutosaveService
from oeapp.services.backup import BackupService
from oeapp.services.commands import CommandManager, MergeSentenceCommand
from oeapp.services.export_docx import DOCXExporter
from oeapp.services.filter import FilterService
from oeapp.services.import_export import ProjectExporter, ProjectImporter
from oeapp.ui.dialogs import (
    BackupsViewDialog,
    ImportProjectDialog,
    MigrationFailureDialog,
    NewProjectDialog,
    OpenProjectDialog,
    RestoreDialog,
    SettingsDialog,
)
from oeapp.ui.filter_dialog import FilterDialog
from oeapp.ui.help_dialog import HelpDialog
from oeapp.ui.sentence_card import SentenceCard


class MainMenu:
    """Main application menu."""

    def __init__(self, main_window: MainWindow) -> None:
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
        # Store reference for preferences menu
        self.file_menu = self.menu.addMenu("&File")

        new_action = QAction("&New Project...", self.file_menu)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(
            lambda: NewProjectDialog(self.main_window).execute()
        )
        self.file_menu.addAction(new_action)

        open_action = QAction("&Open Project...", self.file_menu)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(
            lambda: OpenProjectDialog(self.main_window).execute()
        )
        self.file_menu.addAction(open_action)

        self.file_menu.addSeparator()

        save_action = QAction("&Save", self.file_menu)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self.main_window.save_project)
        self.file_menu.addAction(save_action)

        export_action = QAction("&DOCX Export...", self.file_menu)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(
            self.main_window.action_service.export_project_docx
        )
        self.file_menu.addAction(export_action)

        self.file_menu.addSeparator()

        filter_action = QAction("&Filter Annotations...", self.file_menu)
        filter_action.setShortcut(QKeySequence("Ctrl+F"))
        filter_action.triggered.connect(self.main_window.show_filter_dialog)
        self.file_menu.addAction(filter_action)

    def add_tools_menu(self) -> None:
        """
        Create tools menu.

        This means adding a "Tools" menu to :attr:`self.menu`, the main menu bar,
        with the following actions:

        - Backup Now
        - Restore...
        - Backups...
        """
        tools_menu = self.menu.addMenu("&Tools")

        backup_action = QAction("&Backup Now", tools_menu)
        backup_action.triggered.connect(self.main_window.backup_now)
        tools_menu.addAction(backup_action)

        restore_action = QAction("&Restore...", tools_menu)
        restore_action.triggered.connect(self.main_window.show_restore_dialog)
        tools_menu.addAction(restore_action)

        backups_view_action = QAction("&Backups...", tools_menu)
        backups_view_action.triggered.connect(self.main_window.show_backups_dialog)
        tools_menu.addAction(backups_view_action)

    def add_preferences_menu(self) -> None:
        """
        Create preferences/settings menu item.

        On macOS, this goes in the application menu.
        On Windows/Linux, this goes in the File menu.
        """
        if sys.platform == "darwin":
            # macOS: Add to application menu (first menu, typically app name)
            # The application menu is automatically created by Qt on macOS
            # We need to find it by looking for menus

            menu_bar = self.main_window.menuBar()
            if isinstance(menu_bar, QMenuBar):
                actions = menu_bar.actions()
                if actions:
                    app_menu_action = actions[0]
                    app_menu = app_menu_action.menu()
                    if isinstance(app_menu, QMenu):
                        app_menu.addSeparator()
                        preferences_action = QAction("&Preferences...", app_menu)
                        preferences_action.setShortcut(QKeySequence("Ctrl+,"))
                        preferences_action.triggered.connect(
                            self.main_window.show_settings_dialog
                        )
                        app_menu.addAction(preferences_action)
        else:
            # Windows/Linux: Add to File menu
            self.file_menu.addSeparator()
            settings_action = QAction("&Settings...", self.file_menu)
            settings_action.triggered.connect(self.main_window.show_settings_dialog)
            self.file_menu.addAction(settings_action)

    def add_project_menu(self) -> None:
        """
        Create project menu.

        This means adding a "Project" menu to :attr:`self.menu`, the main menu bar,
        with the following actions:

        - Export...
        - Import...
        """
        project_menu = self.menu.addMenu("&Project")

        export_action = QAction("&Export...", project_menu)
        export_action.triggered.connect(self.main_window.export_project_json)
        project_menu.addAction(export_action)

        import_action = QAction("&Import...", project_menu)
        import_action.triggered.connect(
            self.main_window.action_service.import_project_json
        )
        project_menu.addAction(import_action)

    def add_help_menu(self) -> None:
        """
        Create help menu.

        This means adding a "Help" menu to :attr:`self.menu`, the main menu bar,
        with the following actions:

        - Help
        """
        help_menu = self.menu.addMenu("&Help")

        help_action = QAction("&Help", help_menu)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(lambda: self.main_window.show_help())
        help_menu.addAction(help_action)

    def build(self) -> None:
        """Build the main menu."""
        self.add_file_menu()
        self.add_tools_menu()
        self.add_project_menu()
        self.add_help_menu()
        # Add preferences after menus are built so we can find the right place
        self.add_preferences_menu()


class MainWindow(QMainWindow):
    """Main application window."""

    #: Main window geometry
    MAIN_WINDOW_GEOMETRY: Final[tuple[int, int, int, int]] = (100, 100, 1200, 800)

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
        self.setGeometry(100, 100, 1200, 800)
        # Central widget with scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area = scroll_area
        self.setCentralWidget(scroll_area)
        # Content widget with layout
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(content_widget)
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

        # Check if we should skip migrations
        skip_until_version = settings.value(
            "migration/skip_until_version", None, type=str
        )
        if skip_until_version:
            # Create a temporary engine to check current version

            temp_engine = create_engine_with_path()
            current_db_version = self.backup_service.get_current_migration_version(
                temp_engine
            )
            temp_engine.dispose()
            # Compare versions as strings (Alembic versions are hex strings)
            if current_db_version and str(current_db_version) < str(skip_until_version):
                # Skip migrations - user has chosen to stay on older version
                return

        # Check if backup is needed
        if self.backup_service.should_backup():
            self.backup_service.create_backup()

        # Create backup before attempting migration (if needed)
        backup_path = None
        if self.backup_service.should_backup():
            backup_path = self.backup_service.create_backup()

        # Always try to apply migrations
        try:
            apply_migrations()
            # Migration succeeded - continue normally
        except Exception as e:
            # Migration failed - restore backup if we have one
            if backup_path:
                metadata = self.backup_service.restore_backup(backup_path)
                backup_app_version = None
                if metadata:
                    backup_app_version = metadata.get("application_version")

                # Update settings
                if metadata and metadata.get("migration_version"):
                    settings.setValue(
                        "migration/last_working_version",
                        metadata["migration_version"],
                    )

                # Show error dialog
                dialog = MigrationFailureDialog(self, e, backup_app_version)
                dialog.execute()

                # Exit application
                sys.exit(1)
            else:
                # No backup available - this is bad, but try to continue
                print(f"Migration error and no backup available: {e}")  # noqa: T201

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
        first_project = self.session.scalar(select(Project).limit(1))
        has_projects = first_project is not None

        if not has_projects:
            # No projects exist, show NewProjectDialog
            NewProjectDialog(self).execute()
        else:
            # Projects exist, show OpenProjectDialog
            OpenProjectDialog(self).execute()

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
        Configure the app for the given project.

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
            project = self.session.get(Project, self.current_project_id)
            if project:
                self._configure_project(project)

    def show_backups_dialog(self) -> None:
        """
        Show backups view dialog.
        """
        dialog = BackupsViewDialog(self)
        dialog.execute()

    def backup_now(self) -> None:
        """
        Create a backup immediately.
        """
        backup_path = self.backup_service.create_backup()
        if backup_path:
            self.show_information(
                f"Backup created successfully:\n{backup_path.name}",
                title="Backup Complete",
            )
            self.show_message("Backup created", duration=2000)
        else:
            self.show_error("Failed to create backup.")

    def export_project_json(self) -> None:
        """
        Export project to JSON format.
        """
        if not self.session or not self.current_project_id:
            self.show_warning("No project open")
            return

        # Get project name for default filename
        project = self.session.get(Project, self.current_project_id)
        if project is None:
            self.show_warning("Project not found")
            return

        # Generate default filename: project name (lowercased, whitespace -> _)
        # + ".json"
        default_filename = project.name.lower().replace(" ", "_") + ".json"

        # Get file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Project",
            default_filename,
            "JSON Files (*.json);;All Files (*)",
        )

        # If the user cancels the dialog, do nothing
        if not file_path:
            return

        # Ensure .json extension
        if not file_path.endswith(".json"):
            file_path += ".json"

        # Export project data
        exporter = ProjectExporter(self.session)
        try:
            project_data = exporter.export_project(self.current_project_id)
        except ValueError as e:
            self.show_error(str(e), title="Export Error")
            return

        # Write JSON to file
        try:
            with Path(file_path).open("w", encoding="utf-8") as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
        except (OSError, PermissionError) as e:
            self.show_error(
                f"Failed to write export file:\n{e!s}", title="Export Error"
            )
            return
        except (TypeError, ValueError) as e:
            self.show_error(
                f"Failed to serialize project data:\n{e!s}", title="Export Error"
            )
            return

        self.show_information(
            f"Project exported successfully to:\n{file_path}",
            title="Export Successful",
        )
        self.show_message("Export completed", duration=3000)

    def _on_sentence_merged(self) -> None:
        """
        Handle sentence merge signal.

        Reloads the project from the database to refresh all sentence cards
        after a merge operation.

        """
        if not self.session or not self.current_project_id:
            return

        # Reload project from database
        project = self.session.get(Project, self.current_project_id)
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
        project = self.main_window.session.get(
            Project, self.main_window.current_project_id
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
        project = self.session.get(Project, self.main_window.current_project_id)
        if project is None:
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
        token = self.session.get(Token, token_id)
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
            # Load and parse JSON
            with Path(file_path).open("r", encoding="utf-8") as f:
                project_data = json.load(f)

            # Import project
            importer = ProjectImporter(self.session)
            imported_project, was_renamed = importer.import_project(project_data)

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
