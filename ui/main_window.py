from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
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
)

from sshcli import config as config_module
from sshcli.models import HostBlock
from .option_dialog import OptionDialog


class MainWindow(QMainWindow):
    """Simple PyQt window that lists SSH host blocks via the core APIs."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("sshcli – Hosts")
        self.resize(900, 520)
        self._host_list: QListWidget
        self._options_table: QTableWidget
        self._status_label: QLabel
        self._blocks: List[HostBlock] = []

        self._setup_ui()
        self.load_hosts()

    def _setup_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)

        button_bar = QVBoxLayout()
        button_bar.setSpacing(4)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_hosts)  # type: ignore[arg-type]
        button_bar.addWidget(refresh_button)

        add_host_button = QPushButton("+ Host")
        add_host_button.clicked.connect(self._add_host)  # type: ignore[arg-type]
        button_bar.addWidget(add_host_button)

        button_bar.addStretch()

        button_container = QWidget()
        button_container.setLayout(button_bar)

        layout.addWidget(button_container, alignment=Qt.AlignmentFlag.AlignLeft)

        self._status_label = QLabel("Ready")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self._host_list = QListWidget()
        self._host_list.currentRowChanged.connect(self._show_host_details)  # type: ignore[arg-type]
        self._host_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout.addWidget(self._host_list)
        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        add_option_button = QPushButton("+ Option")
        add_option_button.clicked.connect(self._add_option)  # type: ignore[arg-type]
        right_layout.addWidget(add_option_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self._options_table = QTableWidget(0, 2)
        self._options_table.setHorizontalHeaderLabels(["Option", "Value"])
        self._options_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._options_table.verticalHeader().setVisible(False)
        self._options_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._options_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._options_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._options_table.cellDoubleClicked.connect(self._edit_option)  # type: ignore[arg-type]
        self._options_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self._options_table)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)
        layout.addWidget(self._status_label)

        layout.setStretch(0, 0)  # button column
        layout.setStretch(1, 1)  # splitter takes available height
        layout.setStretch(2, 0)  # status label

        self.setCentralWidget(central)

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

        count = len(blocks)
        self._status_label.setText(f"Loaded {count} host{'s' if count != 1 else ''}.")

    def _populate_host_list(self) -> None:
        self._host_list.clear()
        for block in self._blocks:
            title = ", ".join(block.names_for_listing or block.patterns)
            detail = f"{block.source_file}:{block.lineno}"
            item = QListWidgetItem(title)
            item.setToolTip(detail)
            self._host_list.addItem(item)

    def _show_host_details(self, index: int) -> None:
        if index < 0 or index >= len(self._blocks):
            self._options_table.setRowCount(0)
            return
        block = self._blocks[index]
        items = sorted(block.options.items(), key=lambda kv: kv[0].lower())
        self._options_table.setRowCount(len(items))
        for row, (key, value) in enumerate(items):
            key_item = QTableWidgetItem(key)
            key_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            value_item = QTableWidgetItem(value)
            value_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._options_table.setItem(row, 0, key_item)
            self._options_table.setItem(row, 1, value_item)

    def _current_block(self) -> Optional[HostBlock]:
        index = self._host_list.currentRow()
        if index < 0 or index >= len(self._blocks):
            return None
        return self._blocks[index]

    def _select_host_by_name(self, pattern: str) -> None:
        for idx, block in enumerate(self._blocks):
            if pattern in block.patterns:
                self._host_list.setCurrentRow(idx)
                return

    def _add_host(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Host", "Host pattern:")
        if not ok or not name.strip():
            return
        pattern = name.strip()

        hostname, ok = QInputDialog.getText(self, "Add Host", "HostName (optional):")
        if not ok:
            return
        hostname = hostname.strip()

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
