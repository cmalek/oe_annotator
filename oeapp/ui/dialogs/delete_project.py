from typing import TYPE_CHECKING, Final, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)

from oeapp.models.project import Project

from .new_project import NewProjectDialog
from .open_project import OpenProjectDialog
from .utils import filter_projects_table, load_projects_into_table

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


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

        return cast("Project", Project.get(self.main_window.session, project_id))

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

            # Reset window title
            self.main_window.setWindowTitle("Ænglisc Toolkit")

            # Show appropriate dialog based on remaining projects
            remaining_projects = Project.list(self.main_window.session)
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
