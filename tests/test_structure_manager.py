"""
Tests for StructureManager.
"""

from pathlib import Path

import pytest

from path_manager.compiler import compile_schema
from path_manager.resolver import PathResolver
from path_manager.structure_manager import StructureManager
from path_manager.exceptions import SchemaError


@pytest.fixture
def schema_file():
    """Provide path to example schema.yml"""
    return Path(__file__).parent.parent / "examples" / "schema.yml"


@pytest.fixture
def structures_file():
    """Provide path to example structures.yml"""
    return Path(__file__).parent.parent / "examples" / "structures.yml"


@pytest.fixture
def resolver(schema_file, tmp_path):
    """Provide resolver with compiled schema."""
    db_path = tmp_path / "schema.db"
    compile_schema(schema_file, db_path, format="sqlite")

    res = PathResolver.from_file(db_path)
    yield res
    res.close()


@pytest.fixture
def manager(resolver, structures_file):
    """Provide StructureManager instance."""
    return StructureManager(resolver, structures_file)


class TestStructureManager:
    """Test StructureManager functionality."""

    def test_list_structures(self, manager):
        """Test listing available structures."""
        structures = manager.list_structures()

        assert "project_basic" in structures
        assert "asset_complete" in structures

    def test_get_structure_info(self, manager):
        """Test getting structure definition."""
        info = manager.get_structure_info("project_basic")

        assert "node" in info
        assert info["node"]["directory"] == "proj_root"

    def test_create_project_structure(self, manager, tmp_path):
        """Test creating project directory structure."""
        created = manager.create(
            "project_basic",
            root=str(tmp_path),
            proj="test_proj"
        )

        # Check that directories were created
        proj_root = tmp_path / "test_proj"
        assert proj_root.exists()

        ref_dir = proj_root / "ref"
        assert ref_dir.exists()

        ref_2d = ref_dir / "2d"
        assert ref_2d.exists()

        ref_3d = ref_dir / "3d"
        assert ref_3d.exists()

        client_dir = proj_root / "client"
        assert client_dir.exists()

        work_dir = proj_root / "work"
        assert work_dir.exists()

        # Check return value
        assert len(created) > 0
        assert all(isinstance(p, Path) for p in created)

    def test_create_asset_structure(self, manager, tmp_path):
        """Test creating asset directory structure."""
        created = manager.create(
            "asset_complete",
            root=str(tmp_path),
            proj="test_proj",
            asset="test_asset"
        )

        # Check directories
        asset_root = tmp_path / "test_proj" / "asset" / "test_asset"
        assert asset_root.exists()

        model_dir = asset_root / "model"
        assert model_dir.exists()

        render_dir = asset_root / "render"
        assert render_dir.exists()

        jpg_dir = render_dir / "jpg"
        assert jpg_dir.exists()

        exr_dir = render_dir / "exr"
        assert exr_dir.exists()

    def test_dry_run(self, manager, tmp_path, capsys):
        """Test dry run mode."""
        created = manager.create(
            "project_basic",
            root=str(tmp_path),
            proj="test_proj",
            dry_run=True
        )

        # Nothing should be created
        proj_root = tmp_path / "test_proj"
        assert not proj_root.exists()

        # Should print what would be created
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "mkdir" in captured.out

    def test_unknown_structure(self, manager):
        """Test error when structure doesn't exist."""
        with pytest.raises(KeyError, match="Unknown structure"):
            manager.create("nonexistent_structure", root="/tmp")

    def test_context_conditions(self, manager, tmp_path):
        """Test metadata-driven conditional creation."""
        # Create a test structures.yml with conditions
        structures_with_conditions = tmp_path / "structures_cond.yml"
        structures_with_conditions.write_text("""
structures:
  conditional_test:
    node:
      name: proj_root
      directory: proj_root
      children:
        - name: dev_only
          directory: proj_ref
          meta:
            condition: "is_dev"
        - name: always
          directory: proj_client
""")

        manager_cond = StructureManager(manager.resolver, structures_with_conditions)

        # Create without dev context
        created = manager_cond.create(
            "conditional_test",
            context={},
            root=str(tmp_path / "no_dev"),
            proj="test"
        )

        # dev_only should not be created
        dev_dir = tmp_path / "no_dev" / "test" / "ref"
        assert not dev_dir.exists()

        # always should be created
        always_dir = tmp_path / "no_dev" / "test" / "client"
        assert always_dir.exists()

        # Create with dev context
        created = manager_cond.create(
            "conditional_test",
            context={"is_dev": True},
            root=str(tmp_path / "with_dev"),
            proj="test"
        )

        # Now dev_only should be created
        dev_dir = tmp_path / "with_dev" / "test" / "ref"
        assert dev_dir.exists()


class TestStructureManagerErrors:
    """Test error handling."""

    def test_missing_structures_file(self, resolver, tmp_path):
        """Test error when structures file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            StructureManager(resolver, tmp_path / "nonexistent.yml")

    def test_invalid_structures_format(self, resolver, tmp_path):
        """Test error when structures file is invalid."""
        bad_file = tmp_path / "bad.yml"
        bad_file.write_text("invalid: true")  # Missing 'structures' key

        with pytest.raises(SchemaError, match="Missing 'structures' key"):
            StructureManager(resolver, bad_file)
