from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from oeapp.models.project import Project

if TYPE_CHECKING:
    from datetime import datetime

    from oeapp.ui.main_window import MainWindow


def load_projects_into_table(
    project_table: QTableWidget,
    main_window: MainWindow,
) -> list[Project]:
    """
    Load projects from database into a table widget.  The table widget is
    populated with the project name, last modified date, and created date, and
    is sorted by is sorted by last modified date in descending order.

    Args:
        project_table: Table widget to populate
        main_window: Main window instance for session access

    Returns:
        List of Project objects that were loaded

    """
    # Disable sorting while populating to avoid issues
    project_table.setSortingEnabled(False)
    project_table.setRowCount(0)

    projects = Project.list(main_window.session)
    # Sort projects by updated_at in descending order.  We don't expect there
    # to be thousands of projects, so this is a simple list sort.  If we
    # ever need to sort by updated_at in a more efficient way, we can use a
    # SQLAlchemy query.
    projects.sort(key=lambda x: x.updated_at, reverse=True)
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
