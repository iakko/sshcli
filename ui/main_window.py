from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional
import shlex

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QSizePolicy,
    QToolButton,
    QHBoxLayout,
    QStyle,
    QMenu,
    QLineEdit,
    QComboBox,
    QTextEdit,
    QDialog,
)

from sshcli import config as config_module
from sshcli.models import HostBlock
from .option_dialog import OptionDialog
from .text_prompt_dialog import TextPromptDialog


class MainWindow(QMainWindow):
    """Simple PyQt window that lists SSH host blocks via the core APIs."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SSH-UI: The sshcli frontend!")
        self.resize(900, 520)
        self._host_list: QListWidget
        self._options_table: QTableWidget
        self._status_label: QLabel
        self._blocks: List[HostBlock] = []
        self._visible_blocks: List[HostBlock] = []
        self._viewer_windows: List[QDialog] = []

        self._setup_ui()
        self.load_hosts()

    def _setup_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)

        layout.addWidget(self._build_button_panel(), alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._build_splitter())
        layout.addWidget(self._build_details_panel())
        layout.addWidget(self._build_status_label())

        layout.setStretch(0, 0)  # button column
        layout.setStretch(1, 1)  # splitter takes most height
        layout.setStretch(2, 0)  # details panel
        layout.setStretch(3, 0)  # status label

        self.setCentralWidget(central)

    def _build_button_panel(self) -> QWidget:
        container = QWidget()
        button_bar = QHBoxLayout(container)
        button_bar.setContentsMargins(0, 0, 0, 0)
        button_bar.setSpacing(6)

        button_bar.addWidget(self._make_tool_button("Refresh", QStyle.StandardPixmap.SP_BrowserReload, self.load_hosts))
        button_bar.addWidget(self._make_tool_button("Add", QStyle.StandardPixmap.SP_FileDialogNewFolder, self._add_host))
        button_bar.addWidget(self._make_tool_button("Duplicate", QStyle.StandardPixmap.SP_FileDialogStart, self._duplicate_host))
        button_bar.addWidget(self._make_tool_button("Delete", QStyle.StandardPixmap.SP_TrashIcon, self._delete_host))
        button_bar.addStretch()
        return container

    def _build_splitter(self) -> QSplitter:
        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_host_panel())
        splitter.addWidget(self._build_options_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        return splitter

    def _build_status_label(self) -> QLabel:
        self._status_label = QLabel("Ready")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        return self._status_label

    def _build_details_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        self._details_label = QLabel("No host selected")
        self._details_label.setWordWrap(True)
        info_row.addWidget(self._details_label, stretch=1)

        open_button = QPushButton("Open Config")
        open_button.clicked.connect(self._open_host_file)  # type: ignore[arg-type]
        info_row.addWidget(open_button)
        layout.addLayout(info_row)

        command_row = QHBoxLayout()
        command_row.setSpacing(6)
        command_label = QLabel("SSH command")
        command_row.addWidget(command_label)

        self._ssh_command_field = QLineEdit()
        self._ssh_command_field.setReadOnly(True)
        command_row.addWidget(self._ssh_command_field, stretch=1)

        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self._copy_ssh_command)  # type: ignore[arg-type]
        command_row.addWidget(copy_button)

        layout.addLayout(command_row)
        return container


    def _update_details_label(self, block: Optional[HostBlock]) -> None:
        if block is None:
            self._details_label.setText("No host selected")
            self._update_command_field(None)
            return
        hostnames = block.options.get("HostName", "")
        parts = [f"{block.source_file}:{block.lineno}"]
        if hostnames:
            parts.append(f"HostName: {hostnames}")
        parts.append(f"Options: {len(block.options)}")
        self._details_label.setText(" | ".join(parts))
        self._update_command_field(block)

    def _update_command_field(self, block: Optional[HostBlock]) -> None:
        if block is None:
            self._ssh_command_field.clear()
            return
        command = self._build_ssh_command(block)
        self._ssh_command_field.setText(command)

    def _build_ssh_command(self, block: HostBlock) -> str:
        options = block.options
        target_host = options.get("HostName") or (block.names_for_listing[0] if block.names_for_listing else block.patterns[0])
        user = options.get("User", "")
        tokens: List[str] = ["ssh"]

        identity = options.get("IdentityFile")
        if identity:
            tokens.extend(["-i", identity])

        port = options.get("Port")
        if port:
            tokens.extend(["-p", port])

        proxy_jump = options.get("ProxyJump")
        if proxy_jump:
            tokens.extend(["-J", proxy_jump])

        special_keys = {"HostName", "User", "Port", "IdentityFile", "ProxyJump"}
        for key, value in options.items():
            if key in special_keys or not value:
                continue
            tokens.extend(["-o", f"{key}={value}"])

        target = target_host or block.patterns[0]
        if user:
            target = f"{user}@{target}"
        tokens.append(target)

        return " ".join(shlex.quote(token) for token in tokens)

    def _copy_ssh_command(self) -> None:
        text = self._ssh_command_field.text()
        if not text:
            QMessageBox.information(self, "No Command", "No SSH command available to copy.")
            return
        QApplication.instance().clipboard().setText(text)


    def _build_host_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(4)

        filter_label = QLabel("Filter hosts")
        filter_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        filter_row.addWidget(filter_label)

        self._filter_mode = QComboBox()
        self._filter_mode.addItems(["Host", "Options", "Both"])
        self._filter_mode.currentIndexChanged.connect(lambda _state: self._apply_host_filter())
        filter_row.addWidget(self._filter_mode)

        self._host_filter = QLineEdit()
        self._host_filter.setPlaceholderText("Type to filter...")
        self._host_filter.textChanged.connect(self._apply_host_filter)  # type: ignore[arg-type]
        filter_row.addWidget(self._host_filter)

        layout.addLayout(filter_row)

        self._host_list = QListWidget()
        self._host_list.currentRowChanged.connect(self._show_host_details)  # type: ignore[arg-type]
        self._host_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._host_list)
        return panel

    def _build_options_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        button_row = QHBoxLayout()
        button_row.setSpacing(6)
        button_row.addWidget(self._make_tool_button("Add option", QStyle.StandardPixmap.SP_FileDialogNewFolder, self._add_option))
        button_row.addWidget(self._make_tool_button("Remove option", QStyle.StandardPixmap.SP_DialogCloseButton, self._remove_option))
        button_row.addStretch()
        layout.addLayout(button_row)

        self._options_table = QTableWidget(0, 2)
        self._options_table.setHorizontalHeaderLabels(["Option", "Value"])
        self._options_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._options_table.verticalHeader().setVisible(False)
        self._options_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._options_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._options_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._options_table.cellDoubleClicked.connect(self._edit_option)  # type: ignore[arg-type]
        self._options_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._options_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._options_table.customContextMenuRequested.connect(self._show_option_context_menu)  # type: ignore[arg-type]
        layout.addWidget(self._options_table)
        return panel

    def _make_button(self, label: str, slot: Callable[[], None]) -> QPushButton:
        button = QPushButton(label)
        button.clicked.connect(slot)  # type: ignore[arg-type]
        return button

    def _make_tool_button(self, text: str, icon: QStyle.StandardPixmap, slot: Callable[[], None]) -> QToolButton:
        button = QToolButton()
        button.setIcon(self.style().standardIcon(icon))
        button.setText(text)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setAutoRaise(True)
        button.clicked.connect(slot)  # type: ignore[arg-type]
        return button

    def load_hosts(self) -> None:
        """Fetch host blocks from the shared config logic and display them."""
        try:
            blocks = config_module.load_host_blocks()
        except Exception as exc:  # pragma: no cover - UI feedback
            QMessageBox.critical(self, "Error", f"Failed to load hosts:\n{exc}")
            self._status_label.setText("Failed to load hosts")
            return

        self._blocks = blocks
        self._populate_host_list()
        if blocks:
            self._host_list.setCurrentRow(0)
        else:
            self._options_table.setRowCount(0)
            self._update_details_label(None)

        count = len(blocks)
        self._status_label.setText(f"Loaded {count} host{'s' if count != 1 else ''}.")

    def _populate_host_list(self) -> None:
        self._host_list.clear()
        query = (self._host_filter.text() if hasattr(self, "_host_filter") else "").lower()
        mode_widget = getattr(self, "_filter_mode", None)
        mode = mode_widget.currentText().lower() if mode_widget else "host"
        filtered = [block for block in self._blocks if not query or self._matches_filter(block, query, mode)]
        self._visible_blocks = filtered
        for block in filtered:
            title = ", ".join(block.names_for_listing or block.patterns)
            detail = f"{block.source_file}:{block.lineno}"
            item = QListWidgetItem(title)
            item.setToolTip(detail)
            self._host_list.addItem(item)
        if not filtered:
            self._options_table.setRowCount(0)
            self._update_details_label(None)

    def _matches_filter(self, block: HostBlock, query: str, mode: str) -> bool:
        haystacks = [
            " ".join(block.patterns),
            ", ".join(block.names_for_listing or block.patterns),
            block.options.get("HostName", ""),
        ]
        if mode in ("options", "both"):
            haystacks.extend([key for key in block.options.keys()])
            haystacks.extend(block.options.values())
        if mode == "options":
            haystacks = haystacks[3:]  # only option entries
        return any(query in text.lower() for text in haystacks if text)

    def _apply_host_filter(self) -> None:
        selected = self._current_block()
        self._populate_host_list()
        if selected and selected in self._visible_blocks:
            self._host_list.setCurrentRow(self._visible_blocks.index(selected))
        elif self._visible_blocks:
            self._host_list.setCurrentRow(0)
        else:
            self._host_list.setCurrentRow(-1)
            self._update_details_label(None)

    def _show_host_details(self, index: int) -> None:
        if index < 0 or index >= len(self._visible_blocks):
            self._options_table.setRowCount(0)
            self._update_details_label(None)
            return
        block = self._visible_blocks[index]
        items = sorted(block.options.items(), key=lambda kv: kv[0].lower())
        self._options_table.setRowCount(len(items))
        for row, (key, value) in enumerate(items):
            key_item = QTableWidgetItem(key)
            key_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            value_item = QTableWidgetItem(value)
            value_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._options_table.setItem(row, 0, key_item)
            self._options_table.setItem(row, 1, value_item)
        self._update_details_label(block)

    def _current_block(self) -> Optional[HostBlock]:
        index = self._host_list.currentRow()
        if index < 0 or index >= len(self._visible_blocks):
            return None
        return self._visible_blocks[index]

    def _select_host_by_name(self, pattern: str) -> None:
        for idx, block in enumerate(self._visible_blocks):
            if pattern in block.patterns:
                self._host_list.setCurrentRow(idx)
                return
        # If filtered out, clear filter to show it
        if hasattr(self, "_host_filter") and self._host_filter.text():
            self._host_filter.blockSignals(True)
            self._host_filter.clear()
            self._host_filter.blockSignals(False)
            self._populate_host_list()
            for idx, block in enumerate(self._visible_blocks):
                if pattern in block.patterns:
                    self._host_list.setCurrentRow(idx)
                    return

    def _prompt_text(self, title: str, label: str, *, text: str = "", allow_empty: bool = False) -> Optional[str]:
        dialog = TextPromptDialog(self, title=title, label=label, default=text, allow_empty=allow_empty)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return None
        return dialog.value if dialog.value or allow_empty else None

    def _add_host(self) -> None:
        pattern = self._prompt_text("Add Host", "Host pattern:")
        if not pattern:
            return

        hostname = self._prompt_text("Add Host", "HostName (optional):", allow_empty=True)
        if hostname is None:
            return

        options = []
        if hostname:
            options.append(("HostName", hostname))

        target = Path(config_module.DEFAULT_HOME_SSH_CONFIG).expanduser()
        try:
            config_module.append_host_block(target, [pattern], options)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to add host:\n{exc}")
            return

        self.load_hosts()
        self._select_host_by_name(pattern)

    def _duplicate_host(self) -> None:
        block = self._current_block()
        if block is None:
            QMessageBox.warning(self, "No Host Selected", "Select a host to duplicate.")
            return

        new_pattern = self._prompt_text(
            "Duplicate Host",
            "New host pattern:",
            text=f"{block.patterns[0]}-copy",
        )
        if not new_pattern:
            return

        options = list(block.options.items())
        target = Path(config_module.DEFAULT_HOME_SSH_CONFIG).expanduser()
        try:
            config_module.append_host_block(target, [new_pattern], options)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to duplicate host:\n{exc}")
            return

        self.load_hosts()
        self._select_host_by_name(new_pattern)

    def _delete_host(self) -> None:
        block = self._current_block()
        if block is None:
            QMessageBox.warning(self, "No Host Selected", "Select a host to delete.")
            return

        response = QMessageBox.question(
            self,
            "Delete Host",
            f"Are you sure you want to delete host '{' '.join(block.patterns)}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        try:
            config_module.remove_host_block(Path(block.source_file), block)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to delete host:\n{exc}")
            return

        self.load_hosts()

    def _add_option(self) -> None:
        block = self._current_block()
        if block is None:
            QMessageBox.warning(self, "No Host Selected", "Select a host before adding options.")
            return

        dialog = OptionDialog(self, title="Add Option")
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        key = dialog.option_name.strip()
        value = dialog.option_value.strip()

        options = list(block.options.items())
        for idx, (existing_key, _) in enumerate(options):
            if existing_key.lower() == key.lower():
                options[idx] = (existing_key, value)
                break
        else:
            options.append((key, value))

        try:
            config_module.replace_host_block(Path(block.source_file), block, list(block.patterns), options)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to update host:\n{exc}")
            return

        self.load_hosts()
        self._select_host_by_name(block.patterns[0])

    def _edit_option(self, row: int, column: int) -> None:
        block = self._current_block()
        if block is None:
            return
        if row < 0 or row >= len(block.options):
            return

        items = sorted(block.options.items(), key=lambda kv: kv[0].lower())
        key, value = items[row]

        dialog = OptionDialog(self, title=f"Edit Option – {key}", initial_option=key, initial_value=value)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        new_key = dialog.option_name.strip()
        new_value = dialog.option_value.strip()

        options = list(block.options.items())
        updated = False
        for idx, (existing_key, _) in enumerate(options):
            if existing_key.lower() == key.lower():
                options[idx] = (new_key or key, new_value)
                updated = True
                break
        if not updated:
            options.append((new_key, new_value))

        try:
            config_module.replace_host_block(Path(block.source_file), block, list(block.patterns), options)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to update option:\n{exc}")
            return

        self.load_hosts()
        self._select_host_by_name(block.patterns[0])

    def _show_option_context_menu(self, pos) -> None:
        item = self._options_table.itemAt(pos)
        if item is None:
            return
        column = item.column()
        if column != 1:
            return
        menu = QMenu(self)
        menu.addAction("Copy value", lambda: self._copy_option_value(item.text()))
        menu.exec(self._options_table.viewport().mapToGlobal(pos))

    def _copy_option_value(self, value: str) -> None:
        clipboard = QApplication.instance().clipboard()
        clipboard.setText(value)

    def _remove_option(self) -> None:
        block = self._current_block()
        if block is None:
            QMessageBox.warning(self, "No Host Selected", "Select a host before removing options.")
            return
        row = self._options_table.currentRow()
        if row < 0 or row >= self._options_table.rowCount():
            QMessageBox.warning(self, "No Option Selected", "Select an option row to remove.")
            return

        option_key = self._options_table.item(row, 0).text()
        response = QMessageBox.question(
            self,
            "Remove Option",
            f"Are you sure you want to remove option '{option_key}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        options = [(k, v) for k, v in block.options.items() if k != option_key]
        try:
            config_module.replace_host_block(Path(block.source_file), block, list(block.patterns), options)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to remove option:\n{exc}")
            return

        self.load_hosts()
        self._select_host_by_name(block.patterns[0])

    def _open_host_file(self) -> None:
        block = self._current_block()
        if block is None:
            QMessageBox.information(self, "No Host Selected", "Select a host to open its config.")
            return
        path = Path(block.source_file)
        if not path.exists():
            QMessageBox.warning(self, "File Missing", f"{path} does not exist.")
            return
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(self, "Cannot Read", f"Failed to read {path}:\n{exc}")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(str(path))
        layout = QVBoxLayout(dialog)

        info_label = QLabel(f"Viewing: {path}")
        layout.addWidget(info_label)

        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        viewer.setFont(font)
        viewer.setText(text)
        layout.addWidget(viewer)

        dialog.resize(900, 600)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._register_viewer(dialog)
        dialog.show()

    def _register_viewer(self, dialog: QDialog) -> None:
        self._viewer_windows.append(dialog)

        def _cleanup(*_args) -> None:
            if dialog in self._viewer_windows:
                self._viewer_windows.remove(dialog)

        dialog.destroyed.connect(_cleanup)
