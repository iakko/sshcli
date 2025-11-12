from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
)

_SSH_OPTION_NAMES = [
    "HostName",
    "User",
    "Port",
    "IdentityFile",
    "IdentitiesOnly",
    "ProxyCommand",
    "ProxyJump",
    "LocalForward",
    "RemoteForward",
    "PermitLocalCommand",
    "ForwardAgent",
    "ForwardX11",
    "ServerAliveInterval",
    "ServerAliveCountMax",
    "PreferredAuthentications",
    "ControlMaster",
    "ControlPath",
    "ControlPersist",
    "StrictHostKeyChecking",
    "UserKnownHostsFile",
    "SendEnv",
    "SetEnv",
    "Compression",
    "LogLevel",
]


class OptionDialog(QDialog):
    """Dialog for capturing option name/value pairs."""

    def __init__(self, parent=None, title: str = "Option", initial_option: str = "", initial_value: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)

        self.option_input = QComboBox()
        self.option_input.setEditable(True)
        self.option_input.addItems(_SSH_OPTION_NAMES)
        if initial_option:
            self.option_input.setEditText(initial_option)
        self.value_input = QLineEdit(initial_value)

        layout = QFormLayout(self)
        layout.addRow("Option:", self.option_input)
        layout.addRow("Value:", self.value_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        self.setSizeGripEnabled(False)
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    @property
    def option_name(self) -> str:
        return self.option_input.currentText()

    @property
    def option_value(self) -> str:
        return self.value_input.text()
