"""
StructureManager - Automated directory structure creation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    raise ImportError(
        "pyyaml is required for StructureManager. "
        "Install it with: pip install pyyaml"
    )

from .resolver import PathResolver
from .exceptions import SchemaError


class StructureManager:
    """
    Manage structured directory/file creation.

    Uses structures.yml to define what directories and files
    should be created for different scenarios (projects, assets, etc.)
    """

    def __init__(self, resolver: PathResolver, structures_path: str | Path):
        """
        Initialize structure manager.

        Args:
            resolver: PathResolver instance
            structures_path: Path to structures.yml
        """
        self.resolver = resolver
        self.structures_path = Path(structures_path)

        if not self.structures_path.exists():
            raise FileNotFoundError(f"Structures file not found: {structures_path}")

        # Load structures
        with open(self.structures_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if "structures" not in config:
            raise SchemaError("Missing 'structures' key in structures.yml")

        self.structures = config["structures"]

    def create(
        self,
        struct_name: str,
        context: dict[str, Any] | None = None,
        dry_run: bool = False,
        **fields
    ) -> list[Path]:
        """
        Create directory structure.

        Args:
            struct_name: Structure name from structures.yml
            context: Execution context for metadata conditions
            dry_run: If True, only print what would be created
            **fields: Field values for path resolution

        Returns:
            List of created paths

        Example:
            created = manager.create(
                "project_basic",
                context={"is_dev_mode": True},
                root="/proj",
                proj="demo"
            )
        """
        if struct_name not in self.structures:
            raise KeyError(f"Unknown structure: {struct_name}")

        context = context or {}
        created = []

        root_node = self.structures[struct_name]["node"]
        self._create_node(root_node, fields, context, created, dry_run)

        return created

    def _create_node(
        self,
        node: dict,
        fields: dict,
        context: dict,
        created: list[Path],
        dry_run: bool
    ):
        """
        Recursively create nodes.

        Args:
            node: Node definition from structures.yml
            fields: Field values
            context: Execution context
            created: List to accumulate created paths
            dry_run: Dry run flag
        """
        meta = node.get("meta", {})

        # Check condition (metadata-driven control)
        condition = meta.get("condition")
        if condition and not context.get(condition, False):
            return  # Skip this node

        # Create directory
        if "directory" in node:
            dpath = self.resolver.get_path(node["directory"], **fields)

            if dry_run:
                print(f"[DRY RUN] mkdir: {dpath}")
            else:
                # Get permissions from metadata
                permissions = meta.get("permissions")
                if permissions:
                    mode = int(permissions, 8)
                    dpath.mkdir(parents=True, exist_ok=True, mode=mode)
                else:
                    dpath.mkdir(parents=True, exist_ok=True)

            created.append(dpath)

        # Create file
        if "kind" in node:
            fpath = self.resolver.get_path(node["kind"], **fields)
            create_mode = node.get("create", "file")

            if create_mode == "file":
                if dry_run:
                    print(f"[DRY RUN] touch: {fpath}")
                else:
                    fpath.parent.mkdir(parents=True, exist_ok=True)

                    # Check for template source
                    template_source = meta.get("template_source")
                    if template_source:
                        # Copy from template
                        template_path = Path(template_source)
                        if template_path.exists():
                            fpath.write_text(template_path.read_text())
                        else:
                            # Create empty if template not found
                            fpath.touch(exist_ok=True)
                    else:
                        # Create empty file
                        fpath.touch(exist_ok=True)

                created.append(fpath)

        # Process children (sorted by priority)
        children = node.get("children", [])

        # Sort by priority (if specified in metadata)
        children = sorted(
            children,
            key=lambda c: c.get("meta", {}).get("priority", 0)
        )

        for child in children:
            self._create_node(child, fields, context, created, dry_run)

    def list_structures(self) -> list[str]:
        """
        List available structure names.

        Returns:
            List of structure names
        """
        return list(self.structures.keys())

    def get_structure_info(self, struct_name: str) -> dict:
        """
        Get structure definition.

        Args:
            struct_name: Structure name

        Returns:
            Structure definition dict

        Raises:
            KeyError: If structure not found
        """
        if struct_name not in self.structures:
            raise KeyError(f"Unknown structure: {struct_name}")

        return self.structures[struct_name]
