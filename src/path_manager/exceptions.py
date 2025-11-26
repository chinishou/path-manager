"""
Custom exceptions for path_manager.
"""
from __future__ import annotations


class PathManagerError(Exception):
    """Base exception for all path_manager errors."""
    pass


class SchemaError(PathManagerError):
    """Raised when schema definition is invalid."""
    pass


class ValidationError(PathManagerError):
    """Raised when field value validation fails."""
    pass


class AmbiguousPathError(PathManagerError):
    """Raised when a path matches multiple kinds and disambiguation is required."""
    pass


class AmbiguousPathWarning(UserWarning):
    """Warning issued when a path matches multiple kinds."""
    pass
