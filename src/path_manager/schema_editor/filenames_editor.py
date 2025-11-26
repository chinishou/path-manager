"""
Filenames editor widget
"""
from __future__ import annotations

from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableView, QHeaderView, QLineEdit, QLabel
)
from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QFont


class FilenamesTableModel(QAbstractTableModel):
    """Table model for filenames"""

    def __init__(self):
        super().__init__()
        self.filenames: Dict[str, Dict[str, str]] = {}
        self.filename_names: list[str] = []
        self.headers = ["Name", "Template"]

    def rowCount(self, parent=QModelIndex()):
        return len(self.filename_names)

    def columnCount(self, parent=QModelIndex()):
        return 2

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            filename_name = self.filename_names[index.row()]
            filename_data = self.filenames[filename_name]

            if index.column() == 0:
                return filename_name
            elif index.column() == 1:
                return filename_data.get('template', '')

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

        filename_name = self.filename_names[index.row()]

        if index.column() == 1:
            self.filenames[filename_name]['template'] = value

        self.dataChanged.emit(index, index)
        return True

    def load_filenames(self, filenames: Dict[str, Dict[str, str]]):
        """Load filenames data"""
        self.beginResetModel()
        self.filenames = dict(filenames)
        self.filename_names = sorted(self.filenames.keys())
        self.endResetModel()

    def add_filename(self, name: str):
        """Add new filename"""
        if name in self.filenames:
            return False

        row = len(self.filename_names)
        self.beginInsertRows(QModelIndex(), row, row)
        self.filenames[name] = {'template': '$name.$ext'}
        self.filename_names.append(name)
        self.filename_names.sort()
        self.endInsertRows()
        return True

    def remove_filename(self, row: int):
        """Remove filename"""
        if row < 0 or row >= len(self.filename_names):
            return False

        self.beginRemoveRows(QModelIndex(), row, row)
        filename_name = self.filename_names[row]
        del self.filenames[filename_name]
        del self.filename_names[row]
        self.endRemoveRows()
        return True

    def get_filenames(self) -> Dict[str, Dict[str, str]]:
        """Get all filenames"""
        return dict(self.filenames)


class FilenamesEditor(QWidget):
    """Editor for filenames section"""

    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("<h2>Filename Templates</h2>")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Description
        desc = QLabel(
            "定義檔案名稱的模板，可使用 $變數 語法。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Search/Filter
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter filenames...")
        self.search_box.textChanged.connect(self._on_search)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        search_layout.addStretch()
        layout.addLayout(search_layout)

        # Table
        self.model = FilenamesTableModel()
        self.model.dataChanged.connect(self.modified.emit)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(0)

        self.table = QTableView()
        self.table.setModel(self.proxy_model)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        # Resize columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        add_btn = QPushButton("+ Add Filename")
        add_btn.clicked.connect(self._add_filename)
        button_layout.addWidget(add_btn)

        remove_btn = QPushButton("- Remove Filename")
        remove_btn.clicked.connect(self._remove_filename)
        button_layout.addWidget(remove_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _on_search(self, text: str):
        """Handle search text change"""
        self.proxy_model.setFilterFixedString(text)

    def _add_filename(self):
        """Add new filename"""
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            "Add Filename",
            "Filename template name:"
        )

        if ok and name:
            if self.model.add_filename(name):
                self.modified.emit()
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Filename '{name}' already exists"
                )

    def _remove_filename(self):
        """Remove selected filename"""
        from PySide6.QtWidgets import QMessageBox

        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self, "Info", "Please select a filename to remove")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete the selected filename(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            rows = sorted(
                [self.proxy_model.mapToSource(idx).row() for idx in indexes],
                reverse=True
            )
            for row in rows:
                self.model.remove_filename(row)
            self.modified.emit()

    def load_data(self, filenames: Dict[str, Dict[str, str]]):
        """Load filenames data"""
        self.model.load_filenames(filenames)

    def get_data(self) -> Dict[str, Dict[str, str]]:
        """Get filenames data"""
        return self.model.get_filenames()
