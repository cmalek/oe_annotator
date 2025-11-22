"""Main entry point for Ænglisc Toolkit application."""

# Set process name early on macOS (before any Qt imports)
# This ensures the menu bar shows the correct app name in development mode
import platform
import sys

from PySide6.QtCore import QCoreApplication, QTimer

if platform.system() == "Darwin":
    # Try to set process name before any other imports
    try:
        import setproctitle

        setproctitle.setproctitle("Ænglisc Toolkit")
    except ImportError:
        # Fallback: manipulate sys.argv[0] which sometimes helps
        # This doesn't always work, but it's worth trying
        if sys.argv and len(sys.argv) > 0:
            sys.argv[0] = "Ænglisc Toolkit"

from pathlib import Path

from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from oeapp import __version__
from oeapp.ui.main_window import MainWindow


def get_resource_path(relative_path: str) -> Path:
    """
    Get resource path for bundled application or development.

    Args:
        relative_path: Relative path from project root

    Returns:
        Path to resource file

    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running in PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running in development
        base_path = Path(__file__).parent.parent
    return base_path / relative_path


def main():
    """
    Run the Ænglisc Toolkit application.
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
        QSystemTrayIcon.Information,
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

    window = MainWindow()
    window.show()

    # Show startup dialog after window is displayed
    # Use QTimer to ensure it runs after the event loop starts

    QTimer.singleShot(0, window._show_startup_dialog)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
