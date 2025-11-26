"""
Main window for Schema Editor
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

try:
    from PySide6.QtWidgets import (
        QMainWindow, QTabWidget, QWidget, QVBoxLayout,
        QMenuBar, QMenu, QFileDialog, QMessageBox, QStatusBar,
        QToolBar
    )
    from PySide6.QtGui import QAction, QKeySequence
    from PySide6.QtCore import Qt
except ImportError:
    raise ImportError(
        "PySide6 is required for the schema editor. "
        "Install it with: pip install PySide6"
    )

import yaml

from .fields_editor import FieldsEditor
from .directories_editor import DirectoriesEditor
from .filenames_editor import FilenamesEditor
from .kinds_editor import KindsEditor


class SchemaEditorWindow(QMainWindow):
    """Main window for schema editing"""

    def __init__(self):
        super().__init__()

        self.current_file: Optional[Path] = None
        self.modified = False

        # Schema data
        self.schema = {
            'fields': {},
            'directories': None,
            'filenames': {},
            'kinds': {}
        }

        self._init_ui()
        self._create_menus()
        self._create_toolbar()
        self._create_statusbar()

    def _init_ui(self):
        """Initialize UI components"""
        self.setWindowTitle("Path Manager - Schema Editor")
        self.resize(1200, 800)

        # Central widget with tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create editors
        self.fields_editor = FieldsEditor(self)
        self.directories_editor = DirectoriesEditor(self)
        self.filenames_editor = FilenamesEditor(self)
        self.kinds_editor = KindsEditor(self)

        # Add tabs
        self.tabs.addTab(self.fields_editor, "Fields (欄位)")
        self.tabs.addTab(self.directories_editor, "Directories (目錄)")
        self.tabs.addTab(self.filenames_editor, "Filenames (檔名)")
        self.tabs.addTab(self.kinds_editor, "Kinds (種類)")

        # Connect modification signals
        for editor in [self.fields_editor, self.directories_editor,
                      self.filenames_editor, self.kinds_editor]:
            editor.modified.connect(self._on_modified)

    def _create_menus(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_schema)
        file_menu.addAction(new_action)

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_schema)
        file_menu.addAction(open_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_schema)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_schema_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        # Schema menu
        schema_menu = menubar.addMenu("&Schema")

        validate_action = QAction("&Validate", self)
        validate_action.setShortcut(QKeySequence("Ctrl+Shift+V"))
        validate_action.triggered.connect(self.validate_schema)
        schema_menu.addAction(validate_action)

        load_example_action = QAction("Load &Example", self)
        load_example_action.triggered.connect(self.load_example)
        schema_menu.addAction(load_example_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        """Create toolbar"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Add actions
        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_schema)
        toolbar.addAction(new_action)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_schema)
        toolbar.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_schema)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        validate_action = QAction("Validate", self)
        validate_action.triggered.connect(self.validate_schema)
        toolbar.addAction(validate_action)

    def _create_statusbar(self):
        """Create status bar"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")

    def new_schema(self):
        """Create new schema"""
        if not self._check_save_changes():
            return

        self.schema = {
            'fields': {},
            'directories': None,
            'filenames': {},
            'kinds': {}
        }
        self.current_file = None
        self.modified = False

        self._update_editors()
        self._update_title()
        self.statusbar.showMessage("New schema created")

    def open_schema(self):
        """Open schema file"""
        if not self._check_save_changes():
            return

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Schema",
            "",
            "YAML Files (*.yml *.yaml);;All Files (*)"
        )

        if filename:
            self._load_file(Path(filename))

    def save_schema(self):
        """Save schema"""
        if self.current_file is None:
            return self.save_schema_as()

        return self._save_file(self.current_file)

    def save_schema_as(self):
        """Save schema as new file"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Schema As",
            "",
            "YAML Files (*.yml *.yaml);;All Files (*)"
        )

        if filename:
            return self._save_file(Path(filename))
        return False

    def validate_schema(self):
        """Validate current schema"""
        self._collect_data()

        errors = []

        # Validate fields
        if not self.schema['fields']:
            errors.append("至少需要定義一個欄位")

        # Validate directories
        if self.schema['directories'] is None:
            errors.append("需要定義目錄結構")

        # Validate kinds
        for kind_name, kind_spec in self.schema['kinds'].items():
            if not kind_spec.get('directory'):
                errors.append(f"種類 '{kind_name}' 未指定目錄")
            if not kind_spec.get('filename'):
                # Directory-only kind is OK
                pass

        if errors:
            QMessageBox.warning(
                self,
                "Validation Errors",
                "\n".join(errors)
            )
        else:
            QMessageBox.information(
                self,
                "Validation Success",
                "✓ Schema validation passed"
            )

    def load_example(self):
        """Load example schema"""
        if not self._check_save_changes():
            return

        self.schema = {
            'fields': {
                'root': {'regex': '/[A-Za-z0-9/_-]+', 'example': '/proj'},
                'proj': {'regex': '[A-Za-z0-9_]+', 'example': 'demo_proj'},
                'asset': {'regex': '[A-Za-z0-9_]+', 'example': 'tree'},
                'ver': {'regex': '[0-9]{3}', 'example': '003'},
                'ext': {'regex': '[a-z0-9]+', 'example': 'jpg'}
            },
            'directories': {
                'name': 'root',
                'segment': '$root',
                'children': [
                    {
                        'name': 'proj_root',
                        'segment': '$proj',
                        'children': [
                            {
                                'name': 'assets_root',
                                'segment': 'asset',
                                'children': [
                                    {
                                        'name': 'asset_root',
                                        'segment': '$asset',
                                        'children': [
                                            {
                                                'name': 'asset_render',
                                                'segment': 'render',
                                                'children': [
                                                    {
                                                        'name': 'asset_render_jpg',
                                                        'segment': 'jpg',
                                                        'children': []
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            'filenames': {
                'asset_render_versioned': {
                    'template': '$asset.v$ver.$ext'
                }
            },
            'kinds': {
                'asset_render_image_versioned': {
                    'directory': 'asset_render_jpg',
                    'filename': 'asset_render_versioned'
                }
            }
        }

        self.current_file = None
        self.modified = False

        self._update_editors()
        self._update_title()
        self.statusbar.showMessage("Example schema loaded")

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Schema Editor",
            "<h3>Path Manager - Schema Editor</h3>"
            "<p>Visual editor for Path Manager schema files.</p>"
            "<p>Version: 0.1.0</p>"
            "<p>Built with PySide6</p>"
        )

    def _load_file(self, filepath: Path):
        """Load schema from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.schema = yaml.safe_load(f)

            self.current_file = filepath
            self.modified = False

            self._update_editors()
            self._update_title()
            self.statusbar.showMessage(f"Loaded: {filepath.name}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading File",
                f"Failed to load {filepath}:\n{str(e)}"
            )

    def _save_file(self, filepath: Path) -> bool:
        """Save schema to file"""
        try:
            self._collect_data()

            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(self.schema, f, indent=2, allow_unicode=True)

            self.current_file = filepath
            self.modified = False

            self._update_title()
            self.statusbar.showMessage(f"Saved: {filepath.name}")
            return True

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Saving File",
                f"Failed to save {filepath}:\n{str(e)}"
            )
            return False

    def _update_editors(self):
        """Update all editors with current schema data"""
        self.fields_editor.load_data(self.schema.get('fields', {}))
        self.directories_editor.load_data(self.schema.get('directories'))
        self.filenames_editor.load_data(self.schema.get('filenames', {}))
        self.kinds_editor.load_data(
            self.schema.get('kinds', {}),
            self.schema.get('directories'),
            self.schema.get('filenames', {})
        )

    def _collect_data(self):
        """Collect data from all editors"""
        self.schema['fields'] = self.fields_editor.get_data()
        self.schema['directories'] = self.directories_editor.get_data()
        self.schema['filenames'] = self.filenames_editor.get_data()
        self.schema['kinds'] = self.kinds_editor.get_data()

    def _update_title(self):
        """Update window title"""
        title = "Path Manager - Schema Editor"
        if self.current_file:
            title += f" - {self.current_file.name}"
        if self.modified:
            title += " *"
        self.setWindowTitle(title)

    def _on_modified(self):
        """Handle modification signal"""
        self.modified = True
        self._update_title()

    def _check_save_changes(self) -> bool:
        """Check if user wants to save changes"""
        if not self.modified:
            return True

        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "Do you want to save changes?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Save:
            return self.save_schema()
        elif reply == QMessageBox.StandardButton.Discard:
            return True
        else:
            return False

    def closeEvent(self, event):
        """Handle window close event"""
        if self._check_save_changes():
            event.accept()
        else:
            event.ignore()
