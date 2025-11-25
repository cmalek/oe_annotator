from typing import TYPE_CHECKING, Final, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)

from oeapp.models.project import Project

from .new_project import NewProjectDialog
from .utils import filter_projects_table, load_projects_into_table

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


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
                    "Project", Project.get(self.main_window.session, self.project_id)
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
