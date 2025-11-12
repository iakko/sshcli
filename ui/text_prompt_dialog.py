from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit


class TextPromptDialog(QDialog):
    """Simple text input dialog without min/max controls."""

    def __init__(self, parent=None, *, title: str, label: str, default: str = "", allow_empty: bool = False) -> None:
        super().__init__(parent)
        self.allow_empty = allow_empty
        self.setWindowTitle(title)

        self.input = QLineEdit(default)

        layout = QFormLayout(self)
        layout.addRow(label, self.input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        # Explicitly set only the close button and title
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        
        self.setSizeGripEnabled(False)
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    def _accept(self) -> None:
        text = self.input.text().strip()
        if text or self.allow_empty:
            self.accept()
        else:
            self.input.setFocus()

    @property
    def value(self) -> str:
        return self.input.text().strip()
