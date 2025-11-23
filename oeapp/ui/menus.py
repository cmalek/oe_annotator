import sys
from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenu, QMenuBar

from oeapp.ui.dialogs import NewProjectDialog, OpenProjectDialog

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


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
        #: File menu

    def add_menu(self, menu: str) -> QMenu:
        """
        Add a menu to the main menu bar.

        Args:
            menu: title of the menu

        Returns:
            The added menu instance

        """
        return self.menu.addMenu(menu)

    def build(self) -> None:
        """Build the main menu."""
        # Save a reference to the file menu so PreferencesMenu can find it,
        # if needed.
        self.file_menu = FileMenu(self, self.main_window).file_menu
        ProjectMenu(self, self.main_window)
        ToolsMenu(self, self.main_window)
        HelpMenu(self, self.main_window)
        # This must come after the file menu so we can find the right place base
        # on OS; on macOS, it goes in the application menu, on Windows/Linux, it
        # goes in the File menu.
        PreferencesMenu(self, self.main_window)


class FileMenu:
    """
    A "File" menu to be added to the main menu bar with the following actions:

    - New Project...
    - Open Project...
    - Save
    - Export...
    - Filter Annotations...

    Args:
        main_menu: Main menu instance
        main_window: Main window instance

    """

    def __init__(self, main_menu: MainMenu, main_window: MainWindow) -> None:
        """
        Initialize file menu.
        """
        #: Main window instance
        self.main_window = main_window
        #: Main menu instance
        self.main_menu = main_menu
        self.populate()

    def populate(self) -> None:
        """
        Populate the file menu with the following actions:

        This means adding a "File" menu to the main menu bar, with the following
        actions: with the following actions:

        - New Project...
        - Open Project...
        - Save
        - Export...
        - Filter Annotations...

        """
        # Store reference for preferences menu
        self.file_menu = self.main_menu.add_menu("&File")

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


class ToolsMenu:
    """
    A "Tools" menu to be added to the main menu bar with the following actions:

    - Backup Now
    - Restore...
    - Backups...
    """

    def __init__(self, main_menu: MainMenu, main_window: MainWindow) -> None:
        #: Main window instance
        self.main_window = main_window
        #: Main menu instance
        self.main_menu = main_menu
        self.populate()

    def populate(self) -> None:
        """
        Create tools menu.

        This means adding a "Tools" menu to the main menu bar, with the
        following actions: with the following actions:

        - Backup Now
        - Restore...
        - Backups...
        """
        self.tools_menu = self.main_menu.add_menu("&Tools")

        backup_action = QAction("&Backup Now", self.tools_menu)
        backup_action.triggered.connect(self.main_window.backup_now)
        self.tools_menu.addAction(backup_action)

        restore_action = QAction("&Restore...", self.tools_menu)
        restore_action.triggered.connect(self.main_window.show_restore_dialog)
        self.tools_menu.addAction(restore_action)

        backups_view_action = QAction("&Backups...", self.tools_menu)
        backups_view_action.triggered.connect(self.main_window.show_backups_dialog)
        self.tools_menu.addAction(backups_view_action)


class PreferencesMenu:
    """
    A "Preferences" menu to be added to the main menu bar with the following
    actions:

    - Preferences...
    """

    def __init__(self, main_menu: MainMenu, main_window: MainWindow) -> None:
        #: Main window instance
        self.main_window = main_window
        #: Main menu instance
        self.main_menu = main_menu
        self.populate()

    def populate(self) -> None:
        """
        Populate the preferences menu with the following actions:

        - Preferences...

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
            self.main_menu.file_menu.addSeparator()
            settings_action = QAction("&Settings...", self.file_menu)
            settings_action.triggered.connect(self.main_window.show_settings_dialog)
            self.main_menu.file_menu.addAction(settings_action)


class ProjectMenu:
    """
    A "Project" menu to be added to the main menu bar with the following actions:

    - Export...
    - Import...
    """

    def __init__(self, main_menu: MainMenu, main_window: MainWindow) -> None:
        #: Main window instance
        self.main_window = main_window
        #: Main menu instance
        self.main_menu = main_menu
        self.populate()

    def populate(self) -> None:
        """
        Populate the project menu with the following actions:

        This means adding a "Project" menu to the main menu bar, with the
        following actions: with the following actions:

        - Export...
        - Import...
        """
        self.project_menu = self.main_menu.add_menu("&Project")

        export_action = QAction("&Export...", self.project_menu)
        export_action.triggered.connect(self.main_window.export_project_json)
        self.project_menu.addAction(export_action)

        import_action = QAction("&Import...", self.project_menu)
        import_action.triggered.connect(
            self.main_window.action_service.import_project_json
        )
        self.project_menu.addAction(import_action)


class HelpMenu:
    """
    A "Help" menu to be added to the main menu bar with the following actions:

    - Help
    """

    def __init__(self, main_menu: MainMenu, main_window: MainWindow) -> None:
        #: Main window instance
        self.main_window = main_window
        #: Main menu instance
        self.main_menu = main_menu
        self.populate()

    def populate(self) -> None:
        """
        Adding a "Help" menu to the main menu bar, with the following actions:

        - Help
        """
        self.help_menu = self.main_menu.add_menu("&Help")

        help_action = QAction("&Help", self.help_menu)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(lambda: self.main_window.show_help())
        self.help_menu.addAction(help_action)
