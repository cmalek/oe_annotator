import sys

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtGui import QFontDatabase, QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from oeapp import __version__
from oeapp.utils import get_resource_path

from .main_window import MainWindow

FONTS = [
    "assets/Maranatha.ttf",
    "assets/Anvers-Bold.ttf",
    "assets/Anvers-Regular.ttf",
    "assets/Anvers-SemiBold.ttf",
]


def create_application() -> QApplication:
    """
    Create the application.
    """
    QCoreApplication.setOrganizationName("Chris Malek")  # Can be any string
    QCoreApplication.setApplicationName("Ænglisc Toolkit")  # Name in the menu bar

    app = QApplication(sys.argv)
    # Create the icon
    icon_path = get_resource_path("assets/logo.icns")
    icon = QIcon(str(icon_path))
    # Create the tray
    tray = QSystemTrayIcon()
    tray.setIcon(icon)
    tray.setVisible(True)
    tray.showMessage(
        "Ænglisc Toolkit",
        "Welcome to Ænglisc Toolkit",
        QSystemTrayIcon.MessageIcon.Information,
        5000,
    )

    # Set the organization and application name
    app.setApplicationName("Ænglisc Toolkit")
    app.setApplicationVersion(__version__)

    # Set display name for macOS menu bar
    # Note: Process name should already be set at module level for best results
    QGuiApplication.setApplicationDisplayName("Ænglisc Toolkit")

    # Set application icon
    logo_path = get_resource_path("assets/logo.png")
    if logo_path.exists():
        app.setWindowIcon(QIcon(str(logo_path)))

    # Load Maranatha font
    for font in FONTS:
        font_path = get_resource_path(font)
        if font_path.exists():
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id != -1:
                # Font loaded successfully
                # Query the font families to get the exact names of the loaded fonts
                families = QFontDatabase.applicationFontFamilies(font_id)  # noqa: F841

    window = MainWindow()
    window.show()

    # Show startup dialog after window is displayed
    # Use QTimer to ensure it runs after the event loop starts

    QTimer.singleShot(0, window._show_startup_dialog)
    return app
