import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from oeapp.db import get_current_code_migration_version
from oeapp.exc import AlreadyExists
from oeapp.models.project import Project
from oeapp.services.backup import BackupService

if TYPE_CHECKING:
    from datetime import datetime

    from oeapp.ui.main_window import MainWindow
else:
    MainWindow = object  # type: ignore[assignment, misc]


def load_projects_into_table(
    project_table: QTableWidget,
    main_window: MainWindow,
) -> list[Project]:
    """
    Load projects from database into a table widget.

    Args:
        project_table: Table widget to populate
        main_window: Main window instance for session access

    Returns:
        List of Project objects that were loaded

    """
    # Disable sorting while populating to avoid issues
    project_table.setSortingEnabled(False)
    project_table.setRowCount(0)

    projects = list(
        main_window.session.scalars(
            select(Project).order_by(Project.updated_at.desc())
        ).all()
    )
    if not projects:
        main_window.show_information(
            "No projects found. Create a new project first.",
            title="No Projects",
        )
        project_table.setSortingEnabled(True)
        return []

    project_table.setRowCount(len(projects))
    for row, project in enumerate(projects):
        # Project Name
        name_item = QTableWidgetItem(project.name)
        name_item.setData(Qt.ItemDataRole.UserRole, project.id)
        project_table.setItem(row, 0, name_item)

        # Last Modified - format as human-readable date
        modified_str = project.updated_at.strftime("%b %d, %Y %I:%M %p")
        modified_item = DateTimeTableWidgetItem(modified_str, project.updated_at)
        project_table.setItem(row, 1, modified_item)

        # Created - format as human-readable date
        created_str = project.created_at.strftime("%b %d, %Y %I:%M %p")
        created_item = DateTimeTableWidgetItem(created_str, project.created_at)
        project_table.setItem(row, 2, created_item)

    # Re-enable sorting after population
    project_table.setSortingEnabled(True)

    return projects


def filter_projects_table(project_table: QTableWidget, search_text: str) -> None:
    """
    Filter the project table based on search text.

    Args:
        project_table: Table widget to filter
        search_text: Text to search for in project names

    """
    search_lower = search_text.lower()
    for row in range(project_table.rowCount()):
        name_item = project_table.item(row, 0)
        if name_item:
            project_name = name_item.text().lower()
            # Show row if search text is empty or matches project name
            should_hide = bool(search_text) and search_lower not in project_name
            project_table.setRowHidden(row, should_hide)


class DateTimeTableWidgetItem(QTableWidgetItem):
    """
    Custom QTableWidgetItem that sorts by datetime value instead of display text.
    """

    def __init__(self, display_text: str, dt: datetime) -> None:
        """
        Initialize the datetime table item.

        Args:
            display_text: Text to display in the table
            dt: Datetime object for sorting

        """
        super().__init__(display_text)
        self._datetime = dt

    def __lt__(self, other: QTableWidgetItem) -> bool:
        """
        Compare items by datetime for proper sorting.

        Args:
            other: Other item to compare with

        Returns:
            True if this datetime is less than the other

        """
        if isinstance(other, DateTimeTableWidgetItem):
            return self._datetime < other._datetime
        # Fall back to text comparison for non-datetime items
        return self.text() < other.text()


class NewProjectDialog:
    """
    New project dialog.  This gets opened when the user clicks the "New Project..."
    menu item from the File menu.

    This dialog allows the user to enter a project title and select an input method
    to import Old English text.  The user can either paste in text or import a file.
    If the user imports a file, the file path will be displayed in a read-only edit
    field.  The user can then click the "OK" button to create the project.

    Args:
        main_window: Main window instance

    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 600
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 500

    def __init__(self, main_window: MainWindow) -> None:
        """
        Initialize new project dialog.
        """
        self.main_window = main_window

    def browse_file(self) -> None:
        """
        Open a file dialog to select a file and update the file path edit field.

        This should be connected to the "Browse" button in _add_file_browser_widget.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self.dialog,
            "Select Text File",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            self.selected_file_path = file_path
            self.file_path_edit.setText(file_path)

    def toggle_input_method(self, index: int) -> None:
        """
        Toggle the visibility of the text label, text edit, file label, and file
        browser widget based on the index.
        """
        if index == 0:
            self.text_label.setVisible(True)
            self.text_edit.setVisible(True)
            self.file_label.setVisible(False)
            self.file_browser_widget.setVisible(False)
        else:
            self.text_label.setVisible(False)
            self.text_edit.setVisible(False)
            self.file_label.setVisible(True)
            self.file_browser_widget.setVisible(True)

    def build(self) -> None:
        """
        Build the new project dialog.

        This means:

        - Setting the window title
        - Setting the window geometry
        - Adding the title edit
        - Adding the input method selector
        - Adding the text area
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("New Project")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)
        self._add_title_edit()
        self._add_input_method_selector()
        self._add_text_area()
        self._add_file_browser_widget()
        # Add stretch to push all widgets to the top
        self.layout.addStretch()

        self._add_button_box()

        # Set initial visibility of the text label, text edit, file label, and
        # file browser widget
        self.text_label.setVisible(True)
        self.text_edit.setVisible(True)
        self.file_label.setVisible(False)
        self.file_browser_widget.setVisible(False)

        # Connect the input method selector to the toggle_input_method function
        self.input_method_combo.currentIndexChanged.connect(self.toggle_input_method)

    def _add_title_edit(self) -> None:
        """
        Add the title edit to the dialog.  The title edit will be used to enter
        the project title.
        """
        self.title_edit = QLineEdit(self.dialog)
        self.title_edit.setPlaceholderText("Enter project title...")
        self.layout.addWidget(QLabel("Project Title:"))
        self.layout.addWidget(self.title_edit)

    def _add_input_method_selector(self) -> None:
        """
        Add the input method selector to the dialog.  The input method selector
        will be used to determine which input method to use.

        - Paste in text (default)
        - Import from file

        Choosing "Import from file" will show a file browser widget and a file
        path edit field, and hide the text area for pasting in text.

        Choosing "Paste in text" will show a text area for pasting in text, and
        hide the file browser widget and file path edit field.

        """
        self.input_method_combo = QComboBox(self.dialog)
        self.input_method_combo.addItems(["Paste in text", "Import from file"])
        self.layout.addWidget(QLabel("Input Method:"))
        self.layout.addWidget(self.input_method_combo)

    def _add_text_area(self) -> None:
        """
        Add the text area to the dialog.  The text area will be used to paste in text.
        """
        self.text_edit = QTextEdit(self.dialog)
        self.text_edit.setPlaceholderText("Paste Old English text here...")
        self.text_edit.setMinimumHeight(400)
        self.text_label = QLabel("Old English Text:")
        self.layout.addWidget(self.text_label)
        self.layout.addWidget(self.text_edit)

    def open_file_dialog(self) -> None:
        """
        Open a file dialog to select a file and update the file path edit field.

        The file dialog should be positioned below the file path edit field.
        """
        # Map the bottom left of file_path_edit to global coordinates
        edit_rect = self.file_path_edit.rect()
        global_point = self.file_path_edit.mapToGlobal(edit_rect.bottomLeft())
        # Create and show the QFileDialog at the desired position
        dialog = QFileDialog(self.dialog, "Select Text File")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("Text Files (*.txt);;All Files (*)")
        # Position the dialog below the file_path_edit field
        dialog.move(global_point)
        if dialog.exec():
            files = dialog.selectedFiles()
            if files:
                self.selected_file_path = files[0]
                self.file_path_edit.setText(self.selected_file_path)

    def _add_file_browser_widget(self) -> None:
        """
        Add the file browser widget to the dialog.  The file browser widget will
        be used to browse the file system for a file to import.
        """
        file_browser_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit(self.dialog)
        self.file_path_edit.setPlaceholderText("No file selected...")
        self.file_path_edit.setReadOnly(True)
        browse_button = QPushButton("Browse...")
        file_browser_layout.addWidget(self.file_path_edit)
        file_browser_layout.addWidget(browse_button)
        self.file_browser_widget = QWidget(self.dialog)
        self.file_browser_widget.setLayout(file_browser_layout)
        self.file_label = QLabel("Old English Text File:")
        self.layout.addWidget(self.file_label)
        self.layout.addWidget(self.file_browser_widget)

        browse_button.clicked.connect(self.open_file_dialog)

    def _add_button_box(self) -> None:
        """
        Add the button box to the dialog.  The button box will be used to accept
        or cancel the dialog.
        """
        self.button_box = QDialogButtonBox(self.dialog)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.create_project)
        self.button_box.rejected.connect(self.dialog.reject)
        self.layout.addWidget(self.button_box)

    def create_project(self, text: str, title: str) -> None:
        """
        Create a new project from the text, split into sentences, split
        sentences into tokens, and create sentence cards.

        - If the text is empty, do nothing.
        - If the text is not empty, create a new project from the text.

        Args:
            text: Old English text to process
            title: Project title

        """
        # Create project in the shared database
        project = Project.create(self.main_window.session, text, title)
        self.main_window._configure_project(project)
        self.main_window.setWindowTitle(f"Ænglisc Toolkit - {project.name}")
        self.main_window.show_message("Project created")

    def execute(self) -> None:
        """
        Execute the new project dialog.
        """
        self.build()
        if self.dialog.exec():
            title = self.title_edit.text()
            if not title.strip():
                self.main_window.show_error("Please enter a project title.")
                return

            # Get text based on input method
            if self.input_method_combo.currentIndex() == 0:  # Paste in text
                text = self.text_edit.toPlainText()
            else:  # Import from file
                if not self.selected_file_path:
                    self.main_window.show_error("Please select a file to import.")
                    return
                text = Path(self.file_path_edit.text()).read_text(encoding="utf-8")

            if text.strip():
                try:
                    self.create_project(text, title)
                except AlreadyExists:
                    self.main_window.show_error(
                        f'Project with title "{title!s}" already exists. Please '
                        "choose a different title or delete the existing project."
                    )
            else:
                self.main_window.show_error("Please enter or import Old English text.")


class OpenProjectDialog:
    """
    Open project dialog.  This gets opened when the user clicks the "Open Project..."
    menu item from the File menu.
    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 600
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 500

    def __init__(self, main_window: MainWindow) -> None:
        """
        Initialize open project dialog.
        """
        self.main_window = main_window

    def build(self) -> None:
        """
        Build the open project dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Open Project")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)

        # Add search box
        search_label = QLabel("Search:")
        self.search_box = QLineEdit(self.dialog)
        self.search_box.setPlaceholderText("Search projects...")
        self.search_box.textChanged.connect(self._filter_projects)
        search_layout = QHBoxLayout()
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        self.layout.addLayout(search_layout)

        # Create table widget
        self.project_table = QTableWidget(self.dialog)
        self.project_table.setColumnCount(3)
        self.project_table.setHorizontalHeaderLabels(
            ["Project Name", "Last Modified", "Created"]
        )
        self.project_table.setSortingEnabled(True)
        self.project_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.project_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.project_table.setAlternatingRowColors(True)
        self.project_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Configure column widths
        header = self.project_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self.layout.addWidget(self.project_table)
        self.load_project_list()
        self._add_button_box()

    def load_project_list(self) -> None:
        """
        Update the project list in the table widget by loading projects from the
        database.

        This looks up projects in the database and adds them to the table widget.
        If there are no projects, it shows a message and returns.
        If there are projects, it adds them to the table widget.
        """
        projects = load_projects_into_table(self.project_table, self.main_window)
        # Store all projects for filtering
        self.all_projects = projects

    def _filter_projects(self, search_text: str) -> None:
        """
        Filter the project table based on search text.

        Args:
            search_text: Text to search for in project names

        """
        filter_projects_table(self.project_table, search_text)

    def _open_new_project_dialog(self) -> None:
        """
        Open the NewProjectDialog and close the OpenProjectDialog.
        """
        self.dialog.reject()  # Close the OpenProjectDialog
        new_project_dialog = NewProjectDialog(self.main_window)
        new_project_dialog.execute()

    def _add_button_box(self) -> None:
        """
        Add the button box to the dialog.  The button box will be used to accept
        or cancel the dialog.
        """
        # Create a horizontal layout for the buttons
        button_layout = QHBoxLayout()

        # Add "New project" button on the left
        new_project_button = QPushButton("New project")
        new_project_button.clicked.connect(self._open_new_project_dialog)
        button_layout.addWidget(new_project_button)

        # Add stretch to push button box to the right
        button_layout.addStretch()

        # Add the standard button box on the right
        self.button_box = QDialogButtonBox(self.dialog)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.open_project)
        self.button_box.rejected.connect(self.dialog.reject)
        button_layout.addWidget(self.button_box)

        self.layout.addLayout(button_layout)

    def open_project(self) -> None:
        """
        Open an existing project.
        """
        # Get the selected row from the table.
        selected_row = self.project_table.currentRow()
        if selected_row >= 0:
            name_item = self.project_table.item(selected_row, 0)
            if name_item:
                self.project_id = name_item.data(Qt.ItemDataRole.UserRole)
                # Get the project from the database.
                project = cast(
                    "Project", self.main_window.session.get(Project, self.project_id)
                )
                if project is None:
                    self.main_window.show_warning("Project not found")
                    return
                # Configure the app for the project.
                self.main_window._configure_project(project)
                # Set the window title to the project name.
                self.main_window.setWindowTitle(f"Ænglisc Toolkit - {project.name}")
                self.main_window.show_message("Project opened")
                self.dialog.accept()

    def execute(self) -> None:
        """
        Open an existing project.
        """
        self.build()
        if self.dialog.exec():
            self.open_project()


class DeleteProjectDialog:
    """
    Delete project dialog. This gets opened when the user clicks the "Delete Project..."
    menu item from the File menu.
    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 600
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 500

    def __init__(self, main_window: MainWindow) -> None:
        """
        Initialize delete project dialog.
        """
        self.main_window = main_window
        self.selected_project_id: int | None = None

    def build(self) -> None:
        """
        Build the delete project dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Delete Project")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)

        # Add confirmation message
        message_label = QLabel(
            "Select a project to delete. This action cannot be undone.\n"
            "You can export the project before deleting it."
        )
        message_label.setWordWrap(True)
        self.layout.addWidget(message_label)

        # Add search box
        search_label = QLabel("Search:")
        self.search_box = QLineEdit(self.dialog)
        self.search_box.setPlaceholderText("Search projects...")
        self.search_box.textChanged.connect(self._filter_projects)
        search_layout = QHBoxLayout()
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        self.layout.addLayout(search_layout)

        # Create table widget
        self.project_table = QTableWidget(self.dialog)
        self.project_table.setColumnCount(3)
        self.project_table.setHorizontalHeaderLabels(
            ["Project Name", "Last Modified", "Created"]
        )
        self.project_table.setSortingEnabled(True)
        self.project_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.project_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.project_table.setAlternatingRowColors(True)
        self.project_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Connect selection change to enable/disable buttons
        self.project_table.itemSelectionChanged.connect(self._on_selection_changed)

        # Configure column widths
        header = self.project_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self.layout.addWidget(self.project_table)
        self.load_project_list()
        self._add_button_box()

    def load_project_list(self) -> None:
        """
        Update the project list in the table widget by loading projects from the
        database.
        """
        projects = load_projects_into_table(self.project_table, self.main_window)
        # Store all projects for filtering
        self.all_projects = projects

    def _filter_projects(self, search_text: str) -> None:
        """
        Filter the project table based on search text.

        Args:
            search_text: Text to search for in project names

        """
        filter_projects_table(self.project_table, search_text)

    def _on_selection_changed(self) -> None:
        """
        Handle selection change to enable/disable buttons.
        """
        selected_row = self.project_table.currentRow()
        has_selection = selected_row >= 0

        # Enable/disable buttons based on selection
        self.export_delete_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def _get_selected_project(self) -> Project | None:
        """
        Get the currently selected project.

        Returns:
            Selected Project or None if no selection

        """
        selected_row = self.project_table.currentRow()
        if selected_row < 0:
            return None

        name_item = self.project_table.item(selected_row, 0)
        if not name_item:
            return None

        project_id = name_item.data(Qt.ItemDataRole.UserRole)
        if project_id is None:
            return None

        return cast("Project", self.main_window.session.get(Project, project_id))

    def _export_and_delete(self) -> None:
        """
        Export the selected project and then delete it.
        """
        project = self._get_selected_project()
        if not project:
            self.main_window.show_warning("Please select a project to delete.")
            return

        # Export the project using export_project_json
        export_success = self.main_window.export_project_json(
            project_id=project.id, parent=self.dialog
        )

        # Only proceed with deletion if export was successful
        if export_success:
            self._delete_project(project)

    def _delete_project(self, project: Project | None = None) -> None:
        """
        Delete the selected project.

        Args:
            project: Project to delete. If None, gets selected project.

        """
        if project is None:
            project = self._get_selected_project()

        if not project:
            self.main_window.show_warning("Please select a project to delete.")
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self.dialog,
            "Confirm Deletion",
            f'Are you sure you want to delete the project "{project.name}"?\n\n'
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Check if this is the currently open project
        is_current_project = self.main_window.current_project_id == project.id

        # Delete the project
        try:
            self.main_window.session.delete(project)
            self.main_window.session.commit()
        except Exception as e:  # noqa: BLE001
            self.main_window.show_error(
                f"Failed to delete project:\n{e!s}", title="Delete Error"
            )
            return

        # If we deleted the current project, clear the UI
        if is_current_project:
            # Clear current project
            self.main_window.current_project_id = None

            # Clear sentence cards
            for i in reversed(range(self.main_window.content_layout.count())):
                widget = self.main_window.content_layout.itemAt(i).widget()
                if widget:
                    widget.setParent(None)

            self.main_window.sentence_cards = []
            self.main_window.autosave_service = None
            self.main_window.command_manager = None
            self.main_window.filter_service = None

            # Reset window title
            self.main_window.setWindowTitle("Ænglisc Toolkit")

            # Show appropriate dialog based on remaining projects
            remaining_projects = list(
                self.main_window.session.scalars(select(Project)).all()
            )
            if not remaining_projects:
                # No projects remaining, show NewProjectDialog
                self.dialog.accept()
                NewProjectDialog(self.main_window).execute()
            else:
                # Projects remain, show OpenProjectDialog
                self.dialog.accept()
                OpenProjectDialog(self.main_window).execute()

            self.main_window.show_message("Project deleted", duration=2000)
        else:
            # Just close the dialog and show success
            self.dialog.accept()
            self.main_window.show_information(
                f'Project "{project.name}" deleted successfully.',
                title="Delete Successful",
            )
            self.main_window.show_message("Project deleted", duration=2000)

    def _add_button_box(self) -> None:
        """
        Add the button box to the dialog with three buttons.
        """
        # Create custom button layout
        button_layout = QHBoxLayout()

        # Add "Cancel" button on the left
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.dialog.reject)
        button_layout.addWidget(cancel_button)

        # Add stretch to push other buttons to the right
        button_layout.addStretch()

        # Add "Export & Delete" button
        self.export_delete_button = QPushButton("Export & Delete")
        self.export_delete_button.setEnabled(False)  # Disabled until selection
        self.export_delete_button.clicked.connect(self._export_and_delete)
        button_layout.addWidget(self.export_delete_button)

        # Add "Delete" button
        self.delete_button = QPushButton("Delete")
        self.delete_button.setEnabled(False)  # Disabled until selection
        self.delete_button.clicked.connect(lambda: self._delete_project())
        button_layout.addWidget(self.delete_button)

        self.layout.addLayout(button_layout)

    def execute(self) -> None:
        """
        Execute the delete project dialog.
        """
        self.build()
        self.dialog.exec()


class SettingsDialog:
    """
    Settings dialog for backup configuration.
    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 400
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 200

    def __init__(self, main_window: MainWindow) -> None:
        """
        Initialize settings dialog.
        """
        self.main_window = main_window
        self.settings = QSettings()

    def build(self) -> None:
        """
        Build the settings dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Preferences")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)

        # Number of backups
        num_backups_label = QLabel("Number of backups to keep:")
        self.num_backups_spin = QSpinBox(self.dialog)
        self.num_backups_spin.setMinimum(1)
        self.num_backups_spin.setMaximum(100)
        num_backups_val = cast(
            "int", self.settings.value("backup/num_backups", 5, type=int)
        )
        num_backups = int(num_backups_val) if num_backups_val is not None else 5
        self.num_backups_spin.setValue(num_backups)
        self.layout.addWidget(num_backups_label)
        self.layout.addWidget(self.num_backups_spin)

        # Backup interval
        interval_label = QLabel("Backup interval (minutes):")
        self.interval_spin = QSpinBox(self.dialog)
        self.interval_spin.setMinimum(1)
        self.interval_spin.setMaximum(1440)  # 24 hours
        interval_val = cast(
            "int", self.settings.value("backup/interval_minutes", 720, type=int)
        )
        interval = int(interval_val) if interval_val is not None else 720
        self.interval_spin.setValue(interval)
        self.layout.addWidget(interval_label)
        self.layout.addWidget(self.interval_spin)

        # Button box
        self.button_box = QDialogButtonBox(self.dialog)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.dialog.reject)
        self.layout.addWidget(self.button_box)

    def save_settings(self) -> None:
        """Save settings to QSettings."""
        self.settings.setValue("backup/num_backups", self.num_backups_spin.value())
        self.settings.setValue("backup/interval_minutes", self.interval_spin.value())
        self.dialog.accept()

    def execute(self) -> None:
        """
        Execute the settings dialog.
        """
        self.build()
        self.dialog.exec()


class RestoreDialog:
    """
    Restore dialog for selecting a backup to restore.
    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 700
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 500

    def __init__(self, main_window: MainWindow) -> None:
        """
        Initialize restore dialog.
        """
        self.main_window = main_window

    def build(self) -> None:
        """
        Build the restore dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Restore Backup")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)

        # Create table widget
        self.backup_table = QTableWidget(self.dialog)
        self.backup_table.setColumnCount(4)
        self.backup_table.setHorizontalHeaderLabels(
            ["Backup Date/Time", "File Size", "Migration Version", "App Version"]
        )
        self.backup_table.setSortingEnabled(True)
        self.backup_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.backup_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.backup_table.setAlternatingRowColors(True)
        self.backup_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Configure column widths
        header = self.backup_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.layout.addWidget(self.backup_table)
        self.load_backup_list()
        self._add_button_box()

    def load_backup_list(self) -> None:
        """
        Load the list of available backups.
        """
        backup_service = BackupService()
        backups = backup_service.get_backup_list()

        # Disable sorting while populating
        self.backup_table.setSortingEnabled(False)
        self.backup_table.setRowCount(0)

        if not backups:
            self.main_window.show_information("No backups found.", title="No Backups")
            self.backup_table.setSortingEnabled(True)
            return

        self.backup_table.setRowCount(len(backups))
        for row, backup in enumerate(backups):
            # Backup Date/Time - convert from UTC to local time for display
            backup_time = backup["backup_timestamp"]
            # If timezone-aware (UTC), convert to local time; otherwise assume
            # already local
            if backup_time.tzinfo is not None:
                backup_time_local = backup_time.astimezone()
                # Remove timezone info for display (naive datetime)
                backup_time_local = backup_time_local.replace(tzinfo=None)
            else:
                backup_time_local = backup_time
            time_str = backup_time_local.strftime("%b %d, %Y %I:%M %p")
            time_item = DateTimeTableWidgetItem(time_str, backup_time_local)
            time_item.setData(Qt.ItemDataRole.UserRole, backup["backup_path"])
            self.backup_table.setItem(row, 0, time_item)

            # File Size
            size_str = f"{backup['file_size'] / 1024:.1f} KB"
            size_item = QTableWidgetItem(size_str)
            self.backup_table.setItem(row, 1, size_item)

            # Migration Version
            migration_version = backup.get("migration_version") or "Unknown"
            migration_item = QTableWidgetItem(migration_version)
            self.backup_table.setItem(row, 2, migration_item)

            # App Version
            app_version = backup.get("application_version") or "Unknown"
            app_item = QTableWidgetItem(app_version)
            self.backup_table.setItem(row, 3, app_item)

        # Re-enable sorting after population
        self.backup_table.setSortingEnabled(True)

    def _add_button_box(self) -> None:
        """
        Add the button box to the dialog.
        """
        self.button_box = QDialogButtonBox(self.dialog)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.restore_backup)
        self.button_box.rejected.connect(self.dialog.reject)
        self.layout.addWidget(self.button_box)

    def restore_backup(self) -> None:
        """
        Restore the selected backup.
        """
        # Get the selected row
        selected_row = self.backup_table.currentRow()
        if selected_row < 0:
            self.main_window.show_warning("Please select a backup to restore.")
            return

        time_item = self.backup_table.item(selected_row, 0)
        if not time_item:
            return

        backup_path = time_item.data(Qt.ItemDataRole.UserRole)
        if not backup_path:
            return

        # Confirm restore
        reply = QMessageBox.question(
            self.dialog,
            "Confirm Restore",
            "This will replace your current database with the selected backup.\n"
            "A backup of your current database will be created first.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Restore backup
        backup_service = BackupService()
        metadata = backup_service.restore_backup(Path(backup_path))

        if metadata:
            # Check for version mismatch
            backup_migration = metadata.get("migration_version")
            current_code_migration = get_current_code_migration_version()

            if backup_migration and current_code_migration:
                if backup_migration != current_code_migration:
                    self.main_window.show_warning(
                        f"The restored backup was created with migration version "
                        f"{backup_migration}, but your application expects version "
                        f"{current_code_migration}.\n\n"
                        "You may experience SQL errors. Consider downgrading your "
                        "application to match the backup version.",
                        title="Version Mismatch",
                    )

            settings = QSettings()
            if backup_migration:
                settings.setValue("migration/last_working_version", backup_migration)

            self.main_window.show_information(
                "Backup restored successfully. Please restart the application.",
                title="Restore Complete",
            )
            self.dialog.accept()
        else:
            self.main_window.show_error("Failed to restore backup.")

    def execute(self) -> None:
        """
        Execute the restore dialog.
        """
        self.build()
        self.dialog.exec()


class BackupsViewDialog:
    """
    Dialog to view backup information.
    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 800
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 600

    def __init__(self, main_window: MainWindow) -> None:
        """
        Initialize backups view dialog.
        """
        self.main_window = main_window

    def build(self) -> None:
        """
        Build the backups view dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Backups")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)

        # Create table widget
        self.backup_table = QTableWidget(self.dialog)
        self.backup_table.setColumnCount(5)
        self.backup_table.setHorizontalHeaderLabels(
            [
                "Backup Date/Time",
                "File Size",
                "Migration Version",
                "App Version",
                "Projects",
            ]
        )
        self.backup_table.setSortingEnabled(True)
        self.backup_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.backup_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.backup_table.setAlternatingRowColors(True)
        self.backup_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Configure column widths
        header = self.backup_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.layout.addWidget(self.backup_table)
        self.load_backup_list()
        self._add_button_box()

    def load_backup_list(self) -> None:
        """
        Load the list of available backups.
        """
        backup_service = BackupService()
        backups = backup_service.get_backup_list()

        # Disable sorting while populating
        self.backup_table.setSortingEnabled(False)
        self.backup_table.setRowCount(0)

        if not backups:
            self.main_window.show_information("No backups found.", title="No Backups")
            self.backup_table.setSortingEnabled(True)
            return

        self.backup_table.setRowCount(len(backups))
        for row, backup in enumerate(backups):
            # Backup Date/Time - convert from UTC to local time for display
            backup_time = backup["backup_timestamp"]
            # If timezone-aware (UTC), convert to local time; otherwise assume
            # already local
            if backup_time.tzinfo is not None:
                backup_time_local = backup_time.astimezone()
                # Remove timezone info for display (naive datetime)
                backup_time_local = backup_time_local.replace(tzinfo=None)
            else:
                backup_time_local = backup_time
            time_str = backup_time_local.strftime("%b %d, %Y %I:%M %p")
            time_item = DateTimeTableWidgetItem(time_str, backup_time_local)
            time_item.setData(Qt.ItemDataRole.UserRole, backup)
            self.backup_table.setItem(row, 0, time_item)

            # File Size
            size_str = f"{backup['file_size'] / 1024:.1f} KB"
            size_item = QTableWidgetItem(size_str)
            self.backup_table.setItem(row, 1, size_item)

            # Migration Version
            migration_version = backup.get("migration_version") or "Unknown"
            migration_item = QTableWidgetItem(migration_version)
            self.backup_table.setItem(row, 2, migration_item)

            # App Version
            app_version = backup.get("application_version") or "Unknown"
            app_item = QTableWidgetItem(app_version)
            self.backup_table.setItem(row, 3, app_item)

            # Number of Projects / Total Tokens
            projects = backup.get("projects", [])
            num_projects = len(projects)
            total_tokens = sum(p.get("token_count", 0) for p in projects)
            projects_str = f"{num_projects} project(s), {total_tokens} token(s)"
            projects_item = QTableWidgetItem(projects_str)
            self.backup_table.setItem(row, 4, projects_item)

        # Re-enable sorting after population
        self.backup_table.setSortingEnabled(True)

    def _add_button_box(self) -> None:
        """
        Add the button box to the dialog.
        """
        self.button_box = QDialogButtonBox(self.dialog)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.dialog.reject)
        self.layout.addWidget(self.button_box)

    def execute(self) -> None:
        """
        Execute the backups view dialog.
        """
        self.build()
        self.dialog.exec()


class MigrationFailureDialog:
    """
    Dialog shown when migration fails during startup.
    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 700
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 500

    def __init__(
        self,
        main_window: MainWindow,
        error: Exception,
        backup_app_version: str | None,
    ) -> None:
        """
        Initialize migration failure dialog.

        Args:
            main_window: Main window instance
            error: The exception that occurred during migration
            backup_app_version: Application version from the restored backup

        """
        self.main_window = main_window
        self.error = error
        self.backup_app_version = backup_app_version

    def build(self) -> None:
        """
        Build the migration failure dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Migration Failed")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)

        # Error message
        error_label = QLabel(
            "Database migration failed during startup.\n\n"
            "Your database has been automatically restored to the backup created "
            "before the migration attempt.\n\n"
        )
        if self.backup_app_version:
            error_label.setText(
                error_label.text()
                + f"To continue working, please downgrade to application version "
                f"{self.backup_app_version}.\n\n"
                f"The restored backup was created with application version "
                f"{self.backup_app_version}."
            )
        error_label.setWordWrap(True)
        self.layout.addWidget(error_label)

        # Stack trace
        trace_label = QLabel("Stack Trace:")
        self.layout.addWidget(trace_label)

        trace_text = QTextEdit(self.dialog)
        trace_text.setReadOnly(True)
        trace_str = "".join(
            traceback.format_exception(
                type(self.error), self.error, self.error.__traceback__
            )
        )
        trace_text.setPlainText(trace_str)
        trace_text.setMinimumHeight(200)
        self.layout.addWidget(trace_text)

        # Buttons
        button_layout = QHBoxLayout()

        save_button = QPushButton("Save Stack Trace")
        save_button.clicked.connect(self.save_stack_trace)
        button_layout.addWidget(save_button)

        copy_button = QPushButton("Copy to Clipboard")
        copy_button.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_button)

        button_layout.addStretch()

        exit_button = QPushButton("Exit Application")
        exit_button.clicked.connect(self.dialog.accept)
        button_layout.addWidget(exit_button)

        self.layout.addLayout(button_layout)

    def save_stack_trace(self) -> None:
        """Save stack trace to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self.dialog,
            "Save Stack Trace",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            # Format stack trace (should not fail)
            trace_str = "".join(
                traceback.format_exception(
                    type(self.error), self.error, self.error.__traceback__
                )
            )
            # Write to file - can fail with file system errors
            try:
                Path(file_path).write_text(trace_str, encoding="utf-8")
            except (OSError, PermissionError) as e:
                self.main_window.show_error(f"Failed to save stack trace: {e}")
                return

            self.main_window.show_information(
                f"Stack trace saved to:\n{file_path}", title="Saved"
            )

    def copy_to_clipboard(self) -> None:
        """Copy stack trace to clipboard."""
        clipboard = QApplication.clipboard()
        trace_str = "".join(
            traceback.format_exception(
                type(self.error), self.error, self.error.__traceback__
            )
        )
        clipboard.setText(trace_str)
        self.main_window.show_message("Stack trace copied to clipboard")

    def execute(self) -> None:
        """
        Execute the migration failure dialog.
        """
        self.build()
        self.dialog.exec()


class ImportProjectDialog:
    """
    Dialog shown after importing a project.

    Args:
        main_window: Main window instance
        project: The imported project
        was_renamed: Whether the project name was changed due to collision

    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 400
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 200

    def __init__(
        self,
        main_window: MainWindow,
        project: Project,
        was_renamed: bool,  # noqa: FBT001
    ) -> None:
        """
        Initialize import project dialog.

        Args:
            main_window: Main window instance
            project: The imported project
            was_renamed: Whether the project name was changed

        """
        self.main_window = main_window
        self.project = project
        self.was_renamed = was_renamed
        self.should_open = False

    def build(self) -> None:
        """
        Build the import project dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Import Successful")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)

        # Success message
        message = f"Project '{self.project.name}' imported successfully."
        if self.was_renamed:
            message += (
                "\n\nThe project name was changed to avoid a collision with an "
                "existing project."
            )
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        self.layout.addWidget(message_label)

        # Button box
        self.button_box = QDialogButtonBox(self.dialog)
        open_button = self.button_box.addButton(
            "Open Project", QDialogButtonBox.ButtonRole.AcceptRole
        )
        close_button = self.button_box.addButton(QDialogButtonBox.StandardButton.Close)
        open_button.clicked.connect(self._open_project)
        close_button.clicked.connect(self.dialog.reject)
        self.layout.addWidget(self.button_box)

    def _open_project(self) -> None:
        """Handle open project button click."""
        self.should_open = True
        self.dialog.accept()

    def execute(self) -> bool:
        """
        Execute the import project dialog.

        Returns:
            True if user chose to open project, False otherwise

        """
        self.build()
        self.dialog.exec()
        return self.should_open
