"""
Abstract base class for compiled schema storage.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator


class CompiledStore(ABC):
    """
    Abstract interface for compiled schema storage.

    Implementations must support lazy loading and concurrent read access.
    """

    @abstractmethod
    def get_kind(self, name: str) -> dict | None:
        """
        Get kind definition by name.

        Args:
            name: Kind name

        Returns:
            Dict with keys: template (str), fields (list[str])
            None if not found
        """
        pass

    @abstractmethod
    def get_dir(self, name: str) -> dict | None:
        """
        Get directory definition by name.

        Args:
            name: Directory name

        Returns:
            Dict with keys: template (str), fields (list[str])
            None if not found
        """
        pass

    @abstractmethod
    def get_field(self, name: str) -> dict | None:
        """
        Get field definition by name.

        Args:
            name: Field name

        Returns:
            Dict with keys: regex (str), example (str)
            None if not found
        """
        pass

    @abstractmethod
    def iter_all_kinds(self) -> Iterator[str]:
        """
        Iterate over all kind names.

        Used for guess_kinds() functionality.

        Yields:
            Kind names
        """
        pass

    @abstractmethod
    def get_ambiguities(self) -> dict[str, list[str]]:
        """
        Get ambiguity mapping.

        Returns:
            Dict mapping pattern signature to list of kind names
            Example: {"$var/$var/$var.jpg": ["asset_image", "prop_image"]}
        """
        pass

    @abstractmethod
    def close(self):
        """Close any open resources."""
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
