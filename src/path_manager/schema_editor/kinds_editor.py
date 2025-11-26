"""
Kinds editor widget - with dropdown for directory and filename
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableView, QHeaderView, QLineEdit, QLabel,
    QComboBox, QStyledItemDelegate
)
from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QFont


class ComboBoxDelegate(QStyledItemDelegate):
    """Delegate for combo box in table"""

    def __init__(self, items: List[str], parent=None):
        super().__init__(parent)
        self.items = items

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.items)
        return editor

    def setEditorData(self, editor, index):
        value = index.data(Qt.ItemDataRole.EditRole)
        idx = editor.findText(value)
        if idx >= 0:
            editor.setCurrentIndex(idx)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)

    def updateItems(self, items: List[str]):
        """Update available items"""
        self.items = items


class KindsTableModel(QAbstractTableModel):
    """Table model for kinds"""

    def __init__(self):
        super().__init__()
        self.kinds: Dict[str, Dict[str, str]] = {}
        self.kind_names: list[str] = []
        self.headers = ["Name", "Directory", "Filename"]

        self.directory_names: List[str] = []
        self.filename_names: List[str] = []

    def rowCount(self, parent=QModelIndex()):
        return len(self.kind_names)

    def columnCount(self, parent=QModelIndex()):
        return 3

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            kind_name = self.kind_names[index.row()]
            kind_data = self.kinds[kind_name]

            if index.column() == 0:
                return kind_name
            elif index.column() == 1:
                return kind_data.get('directory', '')
            elif index.column() == 2:
                return kind_data.get('filename', '')

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

        kind_name = self.kind_names[index.row()]

        if index.column() == 1:
            self.kinds[kind_name]['directory'] = value
        elif index.column() == 2:
            self.kinds[kind_name]['filename'] = value

        self.dataChanged.emit(index, index)
        return True

    def load_kinds(self, kinds: Dict[str, Dict[str, str]],
                   directory_names: List[str], filename_names: List[str]):
        """Load kinds data"""
        self.beginResetModel()
        self.kinds = dict(kinds)
        self.kind_names = sorted(self.kinds.keys())
        self.directory_names = directory_names
        self.filename_names = filename_names
        self.endResetModel()

    def add_kind(self, name: str):
        """Add new kind"""
        if name in self.kinds:
            return False

        row = len(self.kind_names)
        self.beginInsertRows(QModelIndex(), row, row)
        self.kinds[name] = {'directory': '', 'filename': ''}
        self.kind_names.append(name)
        self.kind_names.sort()
        self.endInsertRows()
        return True

    def remove_kind(self, row: int):
        """Remove kind"""
        if row < 0 or row >= len(self.kind_names):
            return False

        self.beginRemoveRows(QModelIndex(), row, row)
        kind_name = self.kind_names[row]
        del self.kinds[kind_name]
        del self.kind_names[row]
        self.endRemoveRows()
        return True

    def get_kinds(self) -> Dict[str, Dict[str, str]]:
        """Get all kinds"""
        return dict(self.kinds)


class KindsEditor(QWidget):
    """Editor for kinds section"""

    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("<h2>Kinds Definition</h2>")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Description
        desc = QLabel(
            "組合目錄和檔名模板，定義完整的路徑種類。支援搜尋和過濾，適合管理大量kinds。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Search/Filter
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter kinds...")
        self.search_box.textChanged.connect(self._on_search)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)

        # Stats
        self.stats_label = QLabel()
        search_layout.addStretch()
        search_layout.addWidget(self.stats_label)
        layout.addLayout(search_layout)

        # Table
        self.model = KindsTableModel()
        self.model.dataChanged.connect(self.modified.emit)
        self.model.modelReset.connect(self._update_stats)
        self.model.rowsInserted.connect(self._update_stats)
        self.model.rowsRemoved.connect(self._update_stats)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(0)

        self.table = QTableView()
        self.table.setModel(self.proxy_model)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        # Set delegates for combo boxes
        self.dir_delegate = ComboBoxDelegate([])
        self.filename_delegate = ComboBoxDelegate([])
        self.table.setItemDelegateForColumn(1, self.dir_delegate)
        self.table.setItemDelegateForColumn(2, self.filename_delegate)

        # Resize columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        add_btn = QPushButton("+ Add Kind")
        add_btn.clicked.connect(self._add_kind)
        button_layout.addWidget(add_btn)

        remove_btn = QPushButton("- Remove Kind")
        remove_btn.clicked.connect(self._remove_kind)
        button_layout.addWidget(remove_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _on_search(self, text: str):
        """Handle search text change"""
        self.proxy_model.setFilterFixedString(text)
        self._update_stats()

    def _update_stats(self):
        """Update statistics label"""
        total = self.model.rowCount()
        visible = self.proxy_model.rowCount()
        if visible < total:
            self.stats_label.setText(f"Showing {visible} of {total} kinds")
        else:
            self.stats_label.setText(f"Total: {total} kinds")

    def _add_kind(self):
        """Add new kind"""
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            "Add Kind",
            "Kind name:"
        )

        if ok and name:
            if self.model.add_kind(name):
                self.modified.emit()
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Kind '{name}' already exists"
                )

    def _remove_kind(self):
        """Remove selected kind"""
        from PySide6.QtWidgets import QMessageBox

        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self, "Info", "Please select a kind to remove")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete the selected kind(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            rows = sorted(
                [self.proxy_model.mapToSource(idx).row() for idx in indexes],
                reverse=True
            )
            for row in rows:
                self.model.remove_kind(row)
            self.modified.emit()

    def load_data(self, kinds: Dict[str, Dict[str, str]],
                  directories: Optional[Dict[str, Any]],
                  filenames: Dict[str, Dict[str, str]]):
        """Load kinds data"""
        # Extract directory names
        dir_names = []
        if directories:
            dir_names = self._extract_dir_names(directories)

        # Extract filename names
        filename_names = sorted(filenames.keys())

        # Update delegates
        self.dir_delegate.updateItems([''] + dir_names)
        self.filename_delegate.updateItems([''] + filename_names)

        # Load data
        self.model.load_kinds(kinds, dir_names, filename_names)

    def _extract_dir_names(self, node: Dict[str, Any], names: Optional[List[str]] = None) -> List[str]:
        """Recursively extract directory names"""
        if names is None:
            names = []

        names.append(node['name'])

        for child in node.get('children', []):
            self._extract_dir_names(child, names)

        return names

    def get_data(self) -> Dict[str, Dict[str, str]]:
        """Get kinds data"""
        return self.model.get_kinds()
