from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
)


class OptionDialog(QDialog):
    """Dialog for capturing option name/value pairs."""

    def __init__(self, parent=None, title: str = "Option", initial_option: str = "", initial_value: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)

        self.option_input = QLineEdit(initial_option)
        self.value_input = QLineEdit(initial_value)

        layout = QFormLayout(self)
        layout.addRow("Option:", self.option_input)
        layout.addRow("Value:", self.value_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    @property
    def option_name(self) -> str:
        return self.option_input.text()

    @property
    def option_value(self) -> str:
        return self.value_input.text()
