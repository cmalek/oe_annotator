from pathlib import Path
from typing import TYPE_CHECKING, Final

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from oeapp.services import BackupService, MigrationService

from .utils import DateTimeTableWidgetItem

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


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
        migration_service = MigrationService()
        backup_service = BackupService()
        metadata = backup_service.restore_backup(Path(backup_path))

        if metadata:
            # Check for version mismatch
            backup_migration = metadata.get("migration_version")
            current_code_migration = migration_service.code_migration_version()

            if (
                backup_migration
                and current_code_migration
                and backup_migration != current_code_migration
            ):
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
