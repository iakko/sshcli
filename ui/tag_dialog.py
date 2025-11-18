from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TagDialog(QDialog):
    """Dialog for editing host tags and their colors."""

    def __init__(
        self,
        parent=None,
        *,
        title: str = "Edit Tags",
        current_tags: Optional[List[str]] = None,
        all_tags: Optional[List[str]] = None,
        tag_definitions: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)

        self._tags: List[str] = list(current_tags) if current_tags else []
        self._all_tags: List[str] = all_tags or []
        self._tag_definitions: Dict[str, str] = dict(tag_definitions or {})

        self._setup_ui()

        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setSizeGripEnabled(False)
        self.adjustSize()
        self.setMinimumWidth(420)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Assigned Tags:"))
        self._tags_display_widget = QWidget()
        self._tags_display_layout = QHBoxLayout(self._tags_display_widget)
        self._tags_display_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_display_layout.setSpacing(4)
        layout.addWidget(self._tags_display_widget)

        layout.addWidget(QLabel("Available Tags:"))
        self._available_list = QListWidget()
        self._available_list.itemDoubleClicked.connect(  # type: ignore[arg-type]
            lambda item: self._add_tag_from_available(item.text())
        )
        layout.addWidget(self._available_list)

        add_selected = QPushButton("Add Selected Tag")
        add_selected.clicked.connect(self._add_selected_available_tag)  # type: ignore[arg-type]
        layout.addWidget(add_selected)

        layout.addWidget(QLabel("Create New Tag:"))
        new_tag_row = QHBoxLayout()
        new_tag_row.setSpacing(4)
        self._tag_input = QLineEdit()
        self._tag_input.setPlaceholderText("Tag name…")
        self._tag_input.returnPressed.connect(self._create_and_assign_tag)  # type: ignore[arg-type]
        new_tag_row.addWidget(self._tag_input, stretch=1)

        self._color_combo = QComboBox()
        self._populate_color_options()
        new_tag_row.addWidget(self._color_combo)

        create_button = QPushButton("Create & Assign")
        create_button.clicked.connect(self._create_and_assign_tag)  # type: ignore[arg-type]
        new_tag_row.addWidget(create_button)
        layout.addLayout(new_tag_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._setup_autocomplete()
        self._refresh_assigned_tags()
        self._refresh_available_tags()

    def _populate_color_options(self) -> None:
        self._color_combo.clear()
        colors = [
            ("Default", ""),
            ("Red", "#ef4444"),
            ("Orange", "#f97316"),
            ("Amber", "#f59e0b"),
            ("Yellow", "#eab308"),
            ("Green", "#10b981"),
            ("Teal", "#14b8a6"),
            ("Blue", "#3b82f6"),
            ("Indigo", "#6366f1"),
            ("Purple", "#a855f7"),
            ("Pink", "#ec4899"),
            ("Gray", "#6b7280"),
        ]
        for label, value in colors:
            self._color_combo.addItem(label, userData=value)
            if value:
                idx = self._color_combo.count() - 1
                self._color_combo.setItemData(idx, QColor(value), Qt.ItemDataRole.BackgroundRole)
                self._color_combo.setItemData(idx, QColor("#ffffff"), Qt.ItemDataRole.ForegroundRole)

    def _setup_autocomplete(self) -> None:
        suggestions = sorted(set(self._tag_definitions.keys()))
        if suggestions:
            completer = QCompleter(suggestions)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self._tag_input.setCompleter(completer)

    def _refresh_assigned_tags(self) -> None:
        while self._tags_display_layout.count():
            item = self._tags_display_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._tags:
            for tag in self._tags:
                badge = self._create_tag_badge(tag)
                self._tags_display_layout.addWidget(badge)
        else:
            placeholder = QLabel("(no tags)")
            placeholder.setStyleSheet("color: #888888; font-style: italic;")
            self._tags_display_layout.addWidget(placeholder)

        self._tags_display_layout.addStretch()

    def _refresh_available_tags(self) -> None:
        self._available_list.clear()
        assigned_lower = {tag.lower() for tag in self._tags}
        available = sorted(
            tag for tag in self._tag_definitions.keys() if tag.lower() not in assigned_lower
        )
        for tag in available:
            item = QListWidgetItem(tag)
            color = self._tag_definitions.get(tag, "")
            if color:
                qcolor = QColor(color)
                item.setBackground(qcolor)
                item.setForeground(QColor("#ffffff") if self._is_dark(qcolor) else QColor("#000000"))
            self._available_list.addItem(item)

    def _create_tag_badge(self, tag: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel(tag)
        color = self._tag_definitions.get(self._resolve_tag_key(tag), "")
        if color:
            label.setStyleSheet(
                f"QLabel {{ background-color: {color}; color: #ffffff; padding: 3px 6px; border-radius: 4px; }}"
            )
        else:
            label.setStyleSheet(
                "QLabel { background-color: #e0e0e0; color: #333333; padding: 3px 6px; border-radius: 4px; }"
            )
        layout.addWidget(label)

        remove_button = QPushButton("×")
        remove_button.setFixedSize(20, 20)
        remove_button.setStyleSheet(
            "QPushButton { border: none; background: transparent; font-size: 14px; }"
        )
        remove_button.clicked.connect(lambda: self._remove_tag(tag))
        layout.addWidget(remove_button)
        return widget

    def _add_tag_from_available(self, tag: str) -> None:
        if not tag:
            return
        if any(t.lower() == tag.lower() for t in self._tags):
            return
        self._tags.append(tag)
        self._refresh_assigned_tags()
        self._refresh_available_tags()

    def _add_selected_available_tag(self) -> None:
        item = self._available_list.currentItem()
        if item is None:
            return
        self._add_tag_from_available(item.text())

    def _create_and_assign_tag(self) -> None:
        tag = self._tag_input.text().strip()
        if not tag:
            return
        if any(t.lower() == tag.lower() for t in self._tags):
            self._tag_input.clear()
            return
        existing_key = self._resolve_tag_key(tag)
        canonical = existing_key if existing_key is not None else tag
        if existing_key is None:
            color = self._color_combo.currentData(Qt.ItemDataRole.UserRole) or ""
            self._tag_definitions[canonical] = color
        self._tags.append(canonical)
        self._tag_input.clear()
        self._refresh_assigned_tags()
        self._refresh_available_tags()

    def _remove_tag(self, tag: str) -> None:
        self._tags = [t for t in self._tags if t != tag]
        self._refresh_assigned_tags()
        self._refresh_available_tags()

    def _resolve_tag_key(self, tag: str) -> Optional[str]:
        for existing in self._tag_definitions.keys():
            if existing.lower() == tag.lower():
                return existing
        return None

    @staticmethod
    def _is_dark(color: QColor) -> bool:
        # Simple luminance check for contrast
        luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
        return luminance < 0.6

    @property
    def tags(self) -> List[str]:
        return self._tags

    @property
    def tag_definitions(self) -> Dict[str, str]:
        return dict(self._tag_definitions)
