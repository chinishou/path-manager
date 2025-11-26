"""
PathResolver - Dynamic path generation and parsing.
"""

import re
import warnings
from pathlib import Path
from string import Template
from typing import Any

from .exceptions import ValidationError, AmbiguousPathError, AmbiguousPathWarning
from .stores import CompiledStore, SQLiteStore, MsgPackStore


class KindSpec:
    """
    Specification for a kind or directory.

    Attributes:
        name: Kind/directory name
        template: Path template string
        fields: Required field names
    """

    def __init__(self, name: str, template: str, fields: list[str]):
        self.name = name
        self.template = template
        self.fields = set(fields)
        self._tmpl_obj: Template | None = None

    @property
    def tmpl(self) -> Template:
        """Get string.Template object (lazy)."""
        if self._tmpl_obj is None:
            self._tmpl_obj = Template(self.template)
        return self._tmpl_obj


class ResolvedPath:
    """
    Lazy-evaluated path result.

    Provides methods to:
    - Get the actual path
    - Get template and fields
    - Parse actual paths
    - Check existence
    """

    def __init__(self, spec: KindSpec, ctx: dict[str, str], resolver: "PathResolver"):
        self._spec = spec
        self._ctx = ctx
        self._resolver = resolver
        self._path_cache: Path | None = None

    def get_path(self) -> Path:
        """
        Get the resolved path.

        Note: Returns path string in POSIX format (/) for cross-platform consistency.
        The Path object will use native separators when used for file operations.
        """
        if self._path_cache is None:
            s = self._spec.tmpl.substitute(self._ctx)
            # Always use POSIX format internally for consistency
            self._path_cache = Path(s)
        return self._path_cache

    def get_path_str(self) -> str:
        """Get the resolved path as POSIX string (always uses / separator)."""
        path = self.get_path()
        return path.as_posix()

    def get_template(self) -> str:
        """Get the original template string."""
        return self._spec.template

    def get_fields(self) -> dict[str, str]:
        """Get the field values used."""
        return self._ctx.copy()

    def parse(self, actual_path: Path | str) -> dict[str, str]:
        """
        Parse an actual path using this kind's template.

        Args:
            actual_path: Path to parse

        Returns:
            Dict of field values

        Raises:
            ValidationError: If path doesn't match template
        """
        return self._resolver.parse(self._spec.name, actual_path)

    def exists(self) -> bool:
        """Check if the path exists."""
        return self.get_path().exists()

    def mkdir(self, **kwargs):
        """Create directory."""
        return self.get_path().mkdir(**kwargs)

    def __str__(self) -> str:
        """String representation uses POSIX format for consistency."""
        return self.get_path_str()

    def __repr__(self) -> str:
        return f"ResolvedPath({self._spec.name}, {self._ctx})"


class PathResolver:
    """
    Resolve paths dynamically from kind + fields.

    Supports both forward (generate) and reverse (parse) resolution.
    """

    def __init__(self, store: CompiledStore):
        """
        Initialize resolver.

        Args:
            store: Compiled schema store
        """
        self.store = store
        self._kind_cache: dict[str, KindSpec] = {}
        self._field_regex_cache: dict[str, str] = {}

    @classmethod
    def from_file(cls, path: str | Path) -> "PathResolver":
        """
        Create resolver from compiled file.

        Automatically detects format from extension:
        - .db -> SQLite
        - .msgpack -> MsgPack

        Args:
            path: Path to compiled file

        Returns:
            PathResolver instance
        """
        path = Path(path)

        if path.suffix == ".db":
            store = SQLiteStore(path)
        elif path.suffix == ".msgpack":
            store = MsgPackStore(path)
        else:
            raise ValueError(f"Unknown file format: {path.suffix}")

        return cls(store)

    def __call__(self, kind: str, **fields) -> ResolvedPath:
        """
        Resolve kind with fields to ResolvedPath.

        Args:
            kind: Kind or directory name
            **fields: Field values

        Returns:
            ResolvedPath object

        Example:
            resolved = resolver("asset_render", root="/proj", proj="demo", asset="tree")
            path = resolved.get_path()
        """
        spec = self._get_kind_spec(kind)
        ctx = self._build_context(spec, fields)
        return ResolvedPath(spec, ctx, self)

    def get_path(self, kind: str, **fields) -> Path:
        """
        Directly get Path object (convenience method).

        Args:
            kind: Kind or directory name
            **fields: Field values

        Returns:
            Path object

        Example:
            path = resolver.get_path("asset_render", root="/proj", proj="demo", asset="tree")
        """
        return self(kind, **fields).get_path()

    def _get_kind_spec(self, kind: str) -> KindSpec:
        """
        Get kind specification (with caching).

        Args:
            kind: Kind or directory name

        Returns:
            KindSpec object

        Raises:
            KeyError: If kind not found
        """
        if kind in self._kind_cache:
            return self._kind_cache[kind]

        # Try kinds first
        rec = self.store.get_kind(kind)

        # Fall back to directories
        if not rec:
            rec = self.store.get_dir(kind)

        if not rec:
            raise KeyError(f"Unknown kind or directory: {kind}")

        spec = KindSpec(kind, rec["template"], rec["fields"])
        self._kind_cache[kind] = spec

        return spec

    def _build_context(self, spec: KindSpec, fields: dict[str, Any]) -> dict[str, str]:
        """
        Build and validate field context.

        Args:
            spec: Kind specification
            fields: Field values

        Returns:
            Validated field dict (all values as strings)

        Raises:
            ValidationError: If validation fails
        """
        # Check for missing fields
        missing = spec.fields - fields.keys()
        if missing:
            raise ValidationError(
                f"Missing fields for kind '{spec.name}': {sorted(missing)}"
            )

        # Validate each field
        ctx = {}
        for name in spec.fields:
            value = str(fields[name])
            regex = self._get_field_regex(name)

            if regex and not re.fullmatch(regex, value):
                raise ValidationError(
                    f"Field '{name}' value '{value}' doesn't match regex: {regex}"
                )

            ctx[name] = value

        return ctx

    def _get_field_regex(self, name: str) -> str | None:
        """Get field regex (with caching)."""
        if name not in self._field_regex_cache:
            field_spec = self.store.get_field(name)
            if field_spec:
                self._field_regex_cache[name] = field_spec["regex"]
            else:
                self._field_regex_cache[name] = None

        return self._field_regex_cache[name]

    # --- Reverse resolution ---

    def parse(self, kind: str, path: Path | str) -> dict[str, str]:
        """
        Parse path using known kind.

        Args:
            kind: Kind or directory name
            path: Path to parse (will be converted to POSIX format)

        Returns:
            Dict of field values

        Raises:
            ValidationError: If path doesn't match template

        Example:
            fields = resolver.parse("asset_render", "/proj/demo/asset/tree/render/jpg/tree.v003.jpg")
            # → {"root": "/proj", "proj": "demo", "asset": "tree", ...}
        """
        spec = self._get_kind_spec(kind)

        # Convert to POSIX format for consistent matching
        if isinstance(path, Path):
            path_str = path.as_posix()
        else:
            path_str = Path(path).as_posix()

        return self._parse_with_template(spec, path_str)

    def _parse_with_template(self, spec: KindSpec, path_str: str) -> dict[str, str]:
        """
        Parse path using template.

        Args:
            spec: Kind specification
            path_str: Path string to parse (POSIX format)

        Returns:
            Dict of extracted field values

        Raises:
            ValidationError: If path doesn't match template
        """
        # Convert template to regex pattern
        pattern = self._template_to_regex(spec.template, spec.fields)

        # Match path
        match = re.fullmatch(pattern, path_str)

        if not match:
            raise ValidationError(
                f"Path '{path_str}' doesn't match template for '{spec.name}': {spec.template}"
            )

        # Extract fields
        fields = match.groupdict()

        # Validate extracted fields
        for name, value in fields.items():
            regex = self._get_field_regex(name)
            if regex and not re.fullmatch(regex, value):
                raise ValidationError(
                    f"Extracted field '{name}' value '{value}' doesn't match regex: {regex}"
                )

        return fields

    def _template_to_regex(self, template: str, field_names: set[str]) -> str:
        """
        Convert template to regex pattern.

        Handles repeated fields by using named groups for first occurrence
        and backreferences for subsequent occurrences.

        Args:
            template: Template string
            field_names: Field names in template

        Returns:
            Regex pattern string

        Example:
            "$root/$proj/$asset.jpg" -> r"(?P<root>[^/]+)/(?P<proj>[^/]+)/(?P<asset>[^/]+)\.jpg"
            "$asset/$asset.jpg" -> r"(?P<asset>[^/]+)/(?P=asset)\.jpg"
        """
        # Escape special regex chars except $
        pattern = re.escape(template)

        # Replace escaped $ with actual $
        pattern = pattern.replace(r"\$", "$")

        # Replace $var or ${var} with named groups (first occurrence) or backreferences (subsequent)
        for field_name in field_names:
            # Find all occurrences of this field
            field_pattern = rf'\$\{{?{field_name}\}}?'
            matches = list(re.finditer(field_pattern, pattern))

            if not matches:
                continue

            # Get field regex to determine matching pattern
            field_regex = self._get_field_regex(field_name)

            # Determine match pattern based on field regex
            # If field can contain '/', use non-greedy .+?
            # Otherwise use [^/]+ for path segments
            if field_regex and '/' in field_regex:
                match_pattern = '.+?'
            else:
                match_pattern = '[^/]+'

            # Replace from last to first to preserve positions
            for i, match in enumerate(reversed(matches)):
                if i == len(matches) - 1:  # First occurrence (iterating backwards)
                    # Create named group
                    replacement = rf'(?P<{field_name}>{match_pattern})'
                else:
                    # Use backreference for subsequent occurrences
                    replacement = rf'(?P={field_name})'

                pattern = pattern[:match.start()] + replacement + pattern[match.end():]

        return pattern

    def guess(self, path: Path | str, warn: bool = True) -> list[tuple[str, dict[str, str]]]:
        """
        Guess kind(s) from path.

        Args:
            path: Path to analyze (will be converted to POSIX format)
            warn: Issue warning if ambiguous (default True)

        Returns:
            List of (kind_name, fields) tuples

        Example:
            candidates = resolver.guess("/proj/demo/tree.jpg")
            # → [("asset_image", {...}), ("prop_image", {...})]
        """
        # Convert to POSIX format
        if isinstance(path, Path):
            path_str = path.as_posix()
        else:
            path_str = Path(path).as_posix()

        candidates = []

        for kind_name in self.store.iter_all_kinds():
            try:
                fields = self.parse(kind_name, path_str)
                candidates.append((kind_name, fields))
            except ValidationError:
                continue

        # Warn if ambiguous
        if len(candidates) > 1 and warn:
            kind_names = [k for k, _ in candidates]
            warnings.warn(
                f"Path '{path_str}' matches multiple kinds: {kind_names}\n"
                f"This ambiguity was detected during compilation.\n"
                f"Consider using parse(kind, path) with explicit kind.",
                AmbiguousPathWarning
            )

        return candidates

    def guess_one(
        self,
        path: Path | str,
        prefer: str | None = None
    ) -> tuple[str, dict[str, str]]:
        """
        Guess exactly one kind from path.

        Args:
            path: Path to analyze
            prefer: Preferred kind name if ambiguous

        Returns:
            (kind_name, fields) tuple

        Raises:
            ValidationError: No matching kind
            AmbiguousPathError: Multiple matches and no preference

        Example:
            kind, fields = resolver.guess_one("/proj/demo/tree.jpg", prefer="asset_image")
        """
        candidates = self.guess(path, warn=False)

        if not candidates:
            raise ValidationError(f"No kind matches path: {path}")

        if len(candidates) == 1:
            return candidates[0]

        # Ambiguous - try preference
        if prefer:
            for kind_name, fields in candidates:
                if kind_name == prefer:
                    return (kind_name, fields)

        # No valid preference
        kind_names = [k for k, _ in candidates]
        raise AmbiguousPathError(
            f"Path '{path}' matches multiple kinds: {kind_names}. "
            f"Use parse(kind, path) or specify 'prefer' parameter."
        )

    def close(self):
        """Close the underlying store."""
        self.store.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
