"""PyQt UI package for sshcli."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow

__all__ = ["MainWindow", "main"]


def main() -> int:
    """Entry point used by the `sshui` console script."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
