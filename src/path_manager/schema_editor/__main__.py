"""
Entry point for Schema Editor
"""
import sys

try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    print("Error: PySide6 is required for the schema editor.")
    print("Install it with: pip install PySide6")
    sys.exit(1)

from .main_window import SchemaEditorWindow


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Path Manager Schema Editor")
    app.setOrganizationName("Path Manager")

    window = SchemaEditorWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
