from typing import TYPE_CHECKING, Final

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from oeapp.services import BackupService

from .utils import DateTimeTableWidgetItem

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


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
