"""
Directories editor widget - Tree-based editor
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeView, QLabel, QDialog, QFormLayout, QLineEdit,
    QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QAbstractItemModel, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem


class DirectoryTreeModel(QStandardItemModel):
    """Tree model for directory structure"""

    def __init__(self):
        super().__init__()
        self.setHorizontalHeaderLabels(["Name", "Segment"])

    def load_tree(self, root_node: Optional[Dict[str, Any]]):
        """Load directory tree"""
        self.clear()
        self.setHorizontalHeaderLabels(["Name", "Segment"])

        if root_node:
            self._add_node(self.invisibleRootItem(), root_node)

    def _add_node(self, parent_item: QStandardItem, node: Dict[str, Any]):
        """Recursively add node to tree"""
        name_item = QStandardItem(node.get('name', ''))
        segment_item = QStandardItem(node.get('segment', ''))

        # Store node data
        name_item.setData(node, Qt.ItemDataRole.UserRole)

        parent_item.appendRow([name_item, segment_item])

        # Add children
        for child in node.get('children', []):
            self._add_node(name_item, child)

    def get_tree(self) -> Optional[Dict[str, Any]]:
        """Get directory tree"""
        if self.rowCount() == 0:
            return None

        root_item = self.item(0, 0)
        return self._get_node(root_item)

    def _get_node(self, item: QStandardItem) -> Dict[str, Any]:
        """Recursively get node data"""
        segment_item = self.item(item.row(), 1) if item.parent() else self.item(0, 1)

        node = {
            'name': item.text(),
            'segment': segment_item.text() if segment_item else '',
            'children': []
        }

        # Get children
        for row in range(item.rowCount()):
            child_item = item.child(row, 0)
            node['children'].append(self._get_node(child_item))

        return node


class DirectoryDialog(QDialog):
    """Dialog for editing directory node"""

    def __init__(self, parent=None, name="", segment=""):
        super().__init__(parent)
        self.setWindowTitle("Edit Directory Node")
        self.resize(400, 150)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit(name)
        self.segment_edit = QLineEdit(segment)

        layout.addRow("Name:", self.name_edit)
        layout.addRow("Segment:", self.segment_edit)

        # Help text
        help_label = QLabel(
            "使用 $變數名 引用欄位，或輸入固定字串"
        )
        help_label.setWordWrap(True)
        layout.addRow("", help_label)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_values(self):
        """Get dialog values"""
        return self.name_edit.text(), self.segment_edit.text()


class DirectoriesEditor(QWidget):
    """Editor for directories section"""

    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("<h2>Directory Structure</h2>")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Description
        desc = QLabel(
            "定義階層式的目錄結構，使用 $變數 引用欄位。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Tree view
        self.model = DirectoryTreeModel()
        self.model.itemChanged.connect(self.modified.emit)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setAlternatingRowColors(True)
        self.tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.tree.expandAll()

        # Resize columns
        self.tree.header().setSectionResizeMode(0, self.tree.header().ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, self.tree.header().ResizeMode.ResizeToContents)

        layout.addWidget(self.tree)

        # Buttons
        button_layout = QHBoxLayout()

        set_root_btn = QPushButton("Set Root")
        set_root_btn.clicked.connect(self._set_root)
        button_layout.addWidget(set_root_btn)

        add_child_btn = QPushButton("+ Add Child")
        add_child_btn.clicked.connect(self._add_child)
        button_layout.addWidget(add_child_btn)

        edit_btn = QPushButton("✏ Edit")
        edit_btn.clicked.connect(self._edit_node)
        button_layout.addWidget(edit_btn)

        remove_btn = QPushButton("- Remove")
        remove_btn.clicked.connect(self._remove_node)
        button_layout.addWidget(remove_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _set_root(self):
        """Set root directory"""
        dialog = DirectoryDialog(self, "root", "$root")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, segment = dialog.get_values()
            if name and segment:
                node = {'name': name, 'segment': segment, 'children': []}
                self.model.load_tree(node)
                self.tree.expandAll()
                self.modified.emit()

    def _add_child(self):
        """Add child to selected node"""
        indexes = self.tree.selectedIndexes()
        if not indexes:
            QMessageBox.information(
                self,
                "Info",
                "Please select a parent node first"
            )
            return

        parent_index = indexes[0]

        dialog = DirectoryDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, segment = dialog.get_values()
            if name and segment:
                name_item = QStandardItem(name)
                segment_item = QStandardItem(segment)

                parent_item = self.model.itemFromIndex(parent_index)
                parent_item.appendRow([name_item, segment_item])

                self.tree.expand(parent_index)
                self.modified.emit()

    def _edit_node(self):
        """Edit selected node"""
        indexes = self.tree.selectedIndexes()
        if not indexes:
            QMessageBox.information(self, "Info", "Please select a node to edit")
            return

        index = indexes[0]
        item = self.model.itemFromIndex(index)

        # Get current values
        name = item.text()
        segment_item = self.model.item(item.row(), 1) if item.parent() else self.model.item(0, 1)
        segment = segment_item.text() if segment_item else ""

        dialog = DirectoryDialog(self, name, segment)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name, new_segment = dialog.get_values()
            if new_name and new_segment:
                item.setText(new_name)
                if segment_item:
                    segment_item.setText(new_segment)
                self.modified.emit()

    def _remove_node(self):
        """Remove selected node"""
        indexes = self.tree.selectedIndexes()
        if not indexes:
            QMessageBox.information(self, "Info", "Please select a node to remove")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this node and all its children?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            index = indexes[0]
            self.model.removeRow(index.row(), index.parent())
            self.modified.emit()

    def load_data(self, directories: Optional[Dict[str, Any]]):
        """Load directory structure"""
        self.model.load_tree(directories)
        self.tree.expandAll()

    def get_data(self) -> Optional[Dict[str, Any]]:
        """Get directory structure"""
        return self.model.get_tree()
