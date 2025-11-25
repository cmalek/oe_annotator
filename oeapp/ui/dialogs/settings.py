from typing import TYPE_CHECKING, Final, cast

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QSpinBox, QVBoxLayout

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


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
