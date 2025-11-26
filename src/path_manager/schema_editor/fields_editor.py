"""
Fields editor widget
"""
from __future__ import annotations

from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableView, QHeaderView, QLineEdit, QLabel
)
from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QFont


class FieldsTableModel(QAbstractTableModel):
    """Table model for fields"""

    def __init__(self):
        super().__init__()
        self.fields: Dict[str, Dict[str, str]] = {}
        self.field_names: list[str] = []
        self.headers = ["Name", "Regex", "Example"]

    def rowCount(self, parent=QModelIndex()):
        return len(self.field_names)

    def columnCount(self, parent=QModelIndex()):
        return 3

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            field_name = self.field_names[index.row()]
            field_data = self.fields[field_name]

            if index.column() == 0:
                return field_name
            elif index.column() == 1:
                return field_data.get('regex', '')
            elif index.column() == 2:
                return field_data.get('example', '')

        elif role == Qt.ItemDataRole.FontRole:
            if index.column() == 0:
                font = QFont()
                font.setBold(True)
                return font

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None

    def flags(self, index):
        if index.column() == 0:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        field_name = self.field_names[index.row()]

        if index.column() == 1:
            self.fields[field_name]['regex'] = value
        elif index.column() == 2:
            self.fields[field_name]['example'] = value

        self.dataChanged.emit(index, index)
        return True

    def load_fields(self, fields: Dict[str, Dict[str, str]]):
        """Load fields data"""
        self.beginResetModel()
        self.fields = dict(fields)
        self.field_names = sorted(self.fields.keys())
        self.endResetModel()

    def add_field(self, name: str):
        """Add new field"""
        if name in self.fields:
            return False

        row = len(self.field_names)
        self.beginInsertRows(QModelIndex(), row, row)
        self.fields[name] = {'regex': '[A-Za-z0-9_]+', 'example': 'example'}
        self.field_names.append(name)
        self.field_names.sort()
        self.endInsertRows()
        return True

    def remove_field(self, row: int):
        """Remove field"""
        if row < 0 or row >= len(self.field_names):
            return False

        self.beginRemoveRows(QModelIndex(), row, row)
        field_name = self.field_names[row]
        del self.fields[field_name]
        del self.field_names[row]
        self.endRemoveRows()
        return True

    def get_fields(self) -> Dict[str, Dict[str, str]]:
        """Get all fields"""
        return dict(self.fields)


class FieldsEditor(QWidget):
    """Editor for fields section"""

    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("<h2>Fields Definition</h2>")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Description
        desc = QLabel(
            "定義可在路徑中使用的變數欄位，包含驗證用的正則表達式和示例值。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Search/Filter
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter fields...")
        self.search_box.textChanged.connect(self._on_search)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        search_layout.addStretch()
        layout.addLayout(search_layout)

        # Table
        self.model = FieldsTableModel()
        self.model.dataChanged.connect(self.modified.emit)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(0)  # Filter on name column

        self.table = QTableView()
        self.table.setModel(self.proxy_model)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        # Resize columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        add_btn = QPushButton("+ Add Field")
        add_btn.clicked.connect(self._add_field)
        button_layout.addWidget(add_btn)

        remove_btn = QPushButton("- Remove Field")
        remove_btn.clicked.connect(self._remove_field)
        button_layout.addWidget(remove_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _on_search(self, text: str):
        """Handle search text change"""
        self.proxy_model.setFilterFixedString(text)

    def _add_field(self):
        """Add new field"""
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            "Add Field",
            "Field name:"
        )

        if ok and name:
            if self.model.add_field(name):
                self.modified.emit()
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Field '{name}' already exists"
                )

    def _remove_field(self):
        """Remove selected field"""
        from PySide6.QtWidgets import QMessageBox

        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self, "Info", "Please select a field to remove")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete the selected field(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Convert proxy indexes to source indexes and sort descending
            rows = sorted(
                [self.proxy_model.mapToSource(idx).row() for idx in indexes],
                reverse=True
            )
            for row in rows:
                self.model.remove_field(row)
            self.modified.emit()

    def load_data(self, fields: Dict[str, Dict[str, str]]):
        """Load fields data"""
        self.model.load_fields(fields)

    def get_data(self) -> Dict[str, Dict[str, str]]:
        """Get fields data"""
        return self.model.get_fields()
