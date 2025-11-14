from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TagDialog(QDialog):
    """Dialog for editing host tags and color."""

    def __init__(
        self,
        parent=None,
        *,
        title: str = "Edit Tags",
        current_tags: Optional[List[str]] = None,
        current_color: Optional[str] = None,
        all_tags: Optional[List[str]] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        
        # Store current state
        self._tags: List[str] = list(current_tags) if current_tags else []
        self._color: Optional[str] = current_color
        self._all_tags: List[str] = all_tags or []
        
        self._setup_ui()
        
        # Set window flags to remove min/max buttons
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        
        self.setSizeGripEnabled(False)
        self.adjustSize()
        self.setMinimumWidth(400)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Current tags display section
        layout.addWidget(QLabel("Current Tags:"))
        self._tags_display_widget = QWidget()
        self._tags_display_layout = QHBoxLayout(self._tags_display_widget)
        self._tags_display_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_display_layout.setSpacing(4)
        layout.addWidget(self._tags_display_widget)
        
        # Tag input section
        tag_input_layout = QHBoxLayout()
        tag_input_layout.setSpacing(4)
        
        self._tag_input = QLineEdit()
        self._tag_input.setPlaceholderText("Enter tag name...")
        self._tag_input.returnPressed.connect(self._add_tag)
        tag_input_layout.addWidget(self._tag_input, stretch=1)
        
        add_button = QPushButton("Add")
        add_button.clicked.connect(self._add_tag)
        tag_input_layout.addWidget(add_button)
        
        layout.addLayout(tag_input_layout)
        
        # Color picker section
        color_layout = QFormLayout()
        self._color_combo = QComboBox()
        self._color_combo.setEditable(True)
        self._populate_color_options()
        if self._color:
            self._color_combo.setEditText(self._color)
        color_layout.addRow("Color:", self._color_combo)
        layout.addLayout(color_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Initial display of tags
        self._update_tags_display()
        
        # Set up autocomplete after UI is created
        self._setup_autocomplete()

    def _populate_color_options(self) -> None:
        """Populate the color dropdown with predefined color options."""
        colors = [
            "",  # No color
            "red",
            "green",
            "blue",
            "yellow",
            "orange",
            "purple",
            "cyan",
            "magenta",
            "gray",
        ]
        self._color_combo.addItems(colors)

    def _setup_autocomplete(self) -> None:
        """Set up autocomplete for the tag input field."""
        if self._all_tags:
            completer = QCompleter(self._all_tags)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self._tag_input.setCompleter(completer)

    def _update_tags_display(self) -> None:
        """Update the display of current tags."""
        # Clear existing widgets
        while self._tags_display_layout.count():
            item = self._tags_display_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add tag badges
        if self._tags:
            for tag in self._tags:
                tag_widget = self._create_tag_badge(tag)
                self._tags_display_layout.addWidget(tag_widget)
        else:
            no_tags_label = QLabel("(no tags)")
            no_tags_label.setStyleSheet("color: #888888; font-style: italic;")
            self._tags_display_layout.addWidget(no_tags_label)
        
        # Add stretch to push tags to the left
        self._tags_display_layout.addStretch()

    def _create_tag_badge(self, tag: str) -> QWidget:
        """Create a tag badge widget with a remove button."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Tag label
        tag_label = QLabel(tag)
        tag_label.setStyleSheet("""
            QLabel {
                background-color: #e0e0e0;
                color: #333333;
                padding: 4px 6px;
                border-radius: 3px;
                font-size: 11px;
            }
        """)
        layout.addWidget(tag_label)
        
        # Remove button
        remove_button = QPushButton("×")
        remove_button.setFixedSize(20, 20)
        remove_button.setStyleSheet("""
            QPushButton {
                background-color: #d0d0d0;
                color: #333333;
                border: none;
                border-radius: 3px;
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
        """)
        remove_button.clicked.connect(lambda: self._remove_tag(tag))
        layout.addWidget(remove_button)
        
        return widget

    def _add_tag(self) -> None:
        """Add a tag from the input field."""
        tag = self._tag_input.text().strip()
        if not tag:
            return
        
        # Check if tag already exists (case-insensitive)
        if any(t.lower() == tag.lower() for t in self._tags):
            self._tag_input.clear()
            self._tag_input.setFocus()
            return
        
        # Add the tag
        self._tags.append(tag)
        self._tag_input.clear()
        self._tag_input.setFocus()
        self._update_tags_display()

    def _remove_tag(self, tag: str) -> None:
        """Remove a tag from the list."""
        self._tags = [t for t in self._tags if t != tag]
        self._update_tags_display()

    @property
    def tags(self) -> List[str]:
        """Get the current list of tags."""
        return self._tags

    @property
    def color(self) -> Optional[str]:
        """Get the current color value."""
        color_text = self._color_combo.currentText().strip()
        return color_text if color_text else None
