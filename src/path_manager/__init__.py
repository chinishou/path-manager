"""
Path Manager - 動態路徑管理系統

提供 schema-driven 的路徑管理，支援：
- 透過 schema 定義路徑結構
- 動態路徑產生與驗證
- 反向路徑解析
- 結構化目錄建立
"""

from .resolver import PathResolver, ResolvedPath
from .structure_manager import StructureManager
from .exceptions import (
    PathManagerError,
    SchemaError,
    ValidationError,
    AmbiguousPathError,
    AmbiguousPathWarning,
)

__version__ = "0.1.0"

__all__ = [
    "PathResolver",
    "ResolvedPath",
    "StructureManager",
    "PathManagerError",
    "SchemaError",
    "ValidationError",
    "AmbiguousPathError",
    "AmbiguousPathWarning",
]
