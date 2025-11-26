"""
Schema compiler - converts schema.yml to compiled storage.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    raise ImportError(
        "pyyaml is required for schema compilation. "
        "Install it with: pip install pyyaml"
    )

from .exceptions import SchemaError
from .stores.msgpack_store import MsgPackWriter


class SchemaCompiler:
    """
    Compile schema.yml to compiled storage format.
    """

    def __init__(self, schema_path: str | Path):
        """
        Initialize compiler.

        Args:
            schema_path: Path to schema.yml file
        """
        self.schema_path = Path(schema_path)
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")

        # Load schema
        with open(self.schema_path, "r", encoding="utf-8") as f:
            self.schema = yaml.safe_load(f)

        # Validate schema
        self._validate_schema()

        # Compiled data
        self.fields = {}
        self.dirs = {}
        self.kinds = {}
        self.ambiguities = {}

    def _validate_schema(self):
        """Validate schema structure."""
        required_keys = ["fields", "directories", "filenames", "kinds"]

        for key in required_keys:
            if key not in self.schema:
                raise SchemaError(f"Missing required key in schema: {key}")

        # Check all fields have regex
        for name, spec in self.schema["fields"].items():
            if "regex" not in spec:
                raise SchemaError(f"Field '{name}' missing required 'regex'")

    def compile(self):
        """
        Compile schema to internal representation.
        """
        # Compile fields
        self._compile_fields()

        # Compile directories
        self._compile_directories()

        # Compile kinds
        self._compile_kinds()

        # Detect ambiguities
        self._detect_ambiguities()

    def _compile_fields(self):
        """Compile field definitions."""
        for name, spec in self.schema["fields"].items():
            self.fields[name] = {
                "regex": spec["regex"],
                "example": spec.get("example", "")
            }

    def _compile_directories(self):
        """Compile directory tree to flat mapping."""
        root = self.schema["directories"]
        self._walk_directory_tree(root, "")

    def _walk_directory_tree(self, node: dict, parent_template: str):
        """
        Recursively walk directory tree and build templates.

        Args:
            node: Current node
            parent_template: Accumulated template from parent
        """
        name = node["name"]
        segment = node["segment"]

        # Build template for this node
        if parent_template:
            template = f"{parent_template}/{segment}"
        else:
            template = segment

        # Extract fields from template
        fields = self._extract_fields(template)

        # Store directory
        self.dirs[name] = {
            "template": template,
            "fields": fields
        }

        # Process children
        for child in node.get("children", []):
            self._walk_directory_tree(child, template)

    def _compile_kinds(self):
        """Compile kind definitions."""
        filenames = self.schema["filenames"]

        for kind_name, spec in self.schema["kinds"].items():
            dir_name = spec["directory"]
            filename_name = spec["filename"]

            # Get directory template
            if dir_name not in self.dirs:
                raise SchemaError(
                    f"Kind '{kind_name}' references unknown directory: {dir_name}"
                )
            dir_template = self.dirs[dir_name]["template"]

            # Get filename template
            if filename_name not in filenames:
                raise SchemaError(
                    f"Kind '{kind_name}' references unknown filename: {filename_name}"
                )
            filename_template = filenames[filename_name]["template"]

            # Combine
            template = f"{dir_template}/{filename_template}"

            # Extract fields
            fields = self._extract_fields(template)

            self.kinds[kind_name] = {
                "template": template,
                "fields": fields
            }

    def _extract_fields(self, template: str) -> list[str]:
        """
        Extract field names from template.

        Args:
            template: Template string with $var or ${var} syntax

        Returns:
            List of field names
        """
        # Match $var or ${var}
        pattern = r'\$\{?(\w+)\}?'
        matches = re.findall(pattern, template)
        return list(dict.fromkeys(matches))  # Preserve order, remove duplicates

    def _detect_ambiguities(self):
        """
        Detect ambiguous patterns.

        Ambiguity occurs when multiple kinds have the same pattern signature.
        Pattern signature: template with all variables replaced by $var
        """
        pattern_groups = defaultdict(list)

        # Group kinds by pattern signature
        for kind_name, spec in self.kinds.items():
            sig = self._normalize_pattern(spec["template"])
            pattern_groups[sig].append(kind_name)

        # Keep only ambiguous patterns (>1 kind)
        for sig, kind_names in pattern_groups.items():
            if len(kind_names) > 1:
                self.ambiguities[sig] = sorted(kind_names)

    def _normalize_pattern(self, template: str) -> str:
        """
        Normalize template to pattern signature.

        Args:
            template: Template string

        Returns:
            Normalized pattern (all variables replaced with $var)

        Example:
            "$root/$proj/$asset.jpg" -> "$var/$var/$var.jpg"
        """
        return re.sub(r'\$\{?(\w+)\}?', '$var', template)

    def write_sqlite(self, output_path: str | Path):
        """
        Write compiled schema to SQLite database.

        Args:
            output_path: Output database path
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing file
        if output_path.exists():
            output_path.unlink()

        # Create database
        conn = sqlite3.connect(str(output_path))
        cursor = conn.cursor()

        # Create schema
        cursor.execute("""
            CREATE TABLE fields (
                name TEXT PRIMARY KEY,
                regex TEXT NOT NULL,
                example TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE kinds (
                name TEXT PRIMARY KEY,
                template TEXT NOT NULL,
                fields_json TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE dirs (
                name TEXT PRIMARY KEY,
                template TEXT NOT NULL,
                fields_json TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE ambiguities (
                pattern TEXT PRIMARY KEY,
                kind_names TEXT NOT NULL
            )
        """)

        cursor.execute("CREATE INDEX idx_kinds_template ON kinds(template)")

        # Insert data
        for name, spec in self.fields.items():
            cursor.execute(
                "INSERT INTO fields (name, regex, example) VALUES (?, ?, ?)",
                (name, spec["regex"], spec["example"])
            )

        for name, spec in self.dirs.items():
            cursor.execute(
                "INSERT INTO dirs (name, template, fields_json) VALUES (?, ?, ?)",
                (name, spec["template"], json.dumps(spec["fields"]))
            )

        for name, spec in self.kinds.items():
            cursor.execute(
                "INSERT INTO kinds (name, template, fields_json) VALUES (?, ?, ?)",
                (name, spec["template"], json.dumps(spec["fields"]))
            )

        for pattern, kind_names in self.ambiguities.items():
            cursor.execute(
                "INSERT INTO ambiguities (pattern, kind_names) VALUES (?, ?)",
                (pattern, json.dumps(kind_names))
            )

        conn.commit()
        conn.close()

        # Set to read-only
        output_path.chmod(0o444)

        print(f"✓ Compiled to SQLite: {output_path}")
        self._print_stats()

    def write_msgpack(self, output_path: str | Path):
        """
        Write compiled schema to indexed MsgPack file.

        Args:
            output_path: Output file path
        """
        writer = MsgPackWriter(output_path)

        # Write fields
        for name, spec in self.fields.items():
            writer.add_field(name, spec)

        # Write dirs
        for name, spec in self.dirs.items():
            writer.add_dir(name, spec)

        # Write kinds
        for name, spec in self.kinds.items():
            writer.add_kind(name, spec)

        # Write ambiguities
        writer.set_ambiguities(self.ambiguities)

        # Finalize
        writer.finalize()

        print(f"✓ Compiled to MsgPack: {output_path}")
        self._print_stats()

    def _print_stats(self):
        """Print compilation statistics."""
        print(f"  Fields: {len(self.fields)}")
        print(f"  Directories: {len(self.dirs)}")
        print(f"  Kinds: {len(self.kinds)}")

        if self.ambiguities:
            print(f"  ⚠️  Ambiguities detected: {len(self.ambiguities)}")
            for pattern, kind_names in self.ambiguities.items():
                print(f"     {pattern}: {kind_names}")


def compile_schema(
    schema_path: str | Path,
    output_path: str | Path,
    format: str = "sqlite"
):
    """
    Compile schema.yml to compiled storage.

    Args:
        schema_path: Path to schema.yml
        output_path: Output file path
        format: Output format ("sqlite" or "msgpack")
    """
    compiler = SchemaCompiler(schema_path)
    compiler.compile()

    if format == "sqlite":
        compiler.write_sqlite(output_path)
    elif format == "msgpack":
        compiler.write_msgpack(output_path)
    else:
        raise ValueError(f"Unknown format: {format}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compile schema.yml")
    parser.add_argument("schema", help="Path to schema.yml")
    parser.add_argument("--format", choices=["sqlite", "msgpack"], default="sqlite")
    parser.add_argument("--output", "-o", required=True, help="Output file path")

    args = parser.parse_args()

    compile_schema(args.schema, args.output, args.format)
