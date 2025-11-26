"""
Tests for compiler and stores.
"""

import tempfile
from pathlib import Path

import pytest

from path_manager.compiler import SchemaCompiler, compile_schema
from path_manager.stores import SQLiteStore, MsgPackStore
from path_manager.exceptions import SchemaError


@pytest.fixture
def schema_file():
    """Provide path to example schema.yml"""
    return Path(__file__).parent.parent / "examples" / "schema.yml"


@pytest.fixture
def temp_dir():
    """Provide temporary directory for compiled files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestSchemaCompiler:
    """Test schema compilation."""

    def test_compile_schema(self, schema_file, temp_dir):
        """Test basic compilation."""
        compiler = SchemaCompiler(schema_file)
        compiler.compile()

        # Check fields
        assert "root" in compiler.fields
        assert compiler.fields["root"]["regex"] == "([A-Za-z]:)?/[A-Za-z0-9/_-]+"

        # Check directories
        assert "proj_root" in compiler.dirs
        assert compiler.dirs["proj_root"]["template"] == "$root/$proj"

        # Check kinds
        assert "asset_render_image_versioned" in compiler.kinds
        assert "$asset" in compiler.kinds["asset_render_image_versioned"]["template"]

    def test_missing_field_regex(self, temp_dir):
        """Test that missing regex in field raises error."""
        bad_schema = temp_dir / "bad_schema.yml"
        bad_schema.write_text("""
fields:
  root:
    example: "/proj"  # Missing regex!

directories:
  name: root
  segment: "$root"

filenames: {}
kinds: {}
""")

        with pytest.raises(SchemaError, match="missing required 'regex'"):
            SchemaCompiler(bad_schema)

    def test_extract_fields(self, schema_file):
        """Test field extraction from templates."""
        compiler = SchemaCompiler(schema_file)

        fields = compiler._extract_fields("$root/$proj/$asset.v$ver.$ext")
        assert set(fields) == {"root", "proj", "asset", "ver", "ext"}

        # Test ${var} syntax
        fields = compiler._extract_fields("${root}/${proj}/${asset}")
        assert set(fields) == {"root", "proj", "asset"}

    def test_normalize_pattern(self, schema_file):
        """Test pattern normalization for ambiguity detection."""
        compiler = SchemaCompiler(schema_file)

        pattern1 = compiler._normalize_pattern("$root/$proj/$asset.jpg")
        pattern2 = compiler._normalize_pattern("$root/$name/$file.jpg")

        # Both should normalize to same pattern
        assert pattern1 == "$var/$var/$var.jpg"
        assert pattern2 == "$var/$var/$var.jpg"


class TestSQLiteStore:
    """Test SQLite storage."""

    def test_compile_and_read_sqlite(self, schema_file, temp_dir):
        """Test full cycle: compile to SQLite, then read."""
        db_path = temp_dir / "schema.db"

        # Compile
        compile_schema(schema_file, db_path, format="sqlite")

        assert db_path.exists()

        # Read
        store = SQLiteStore(db_path)

        # Test get_kind
        kind = store.get_kind("asset_render_image_versioned")
        assert kind is not None
        assert "$asset" in kind["template"]
        assert "asset" in kind["fields"]

        # Test get_dir
        dir_spec = store.get_dir("proj_root")
        assert dir_spec is not None
        assert dir_spec["template"] == "$root/$proj"

        # Test get_field
        field = store.get_field("root")
        assert field is not None
        assert field["regex"] == "([A-Za-z]:)?/[A-Za-z0-9/_-]+"

        # Test iter_all_kinds
        kinds = list(store.iter_all_kinds())
        assert "asset_render_image_versioned" in kinds

        store.close()

    def test_sqlite_immutable_mode(self, schema_file, temp_dir):
        """Test that SQLite opens in immutable mode."""
        db_path = temp_dir / "schema.db"

        compile_schema(schema_file, db_path, format="sqlite")

        # Should be able to open in immutable mode
        store = SQLiteStore(db_path)

        # Verify it's working
        kind = store.get_kind("asset_render_image_versioned")
        assert kind is not None

        store.close()

    def test_sqlite_not_found(self, temp_dir):
        """Test error when database doesn't exist."""
        with pytest.raises(FileNotFoundError):
            SQLiteStore(temp_dir / "nonexistent.db")


class TestMsgPackStore:
    """Test MsgPack storage."""

    def test_compile_and_read_msgpack(self, schema_file, temp_dir):
        """Test full cycle: compile to MsgPack, then read."""
        msgpack_path = temp_dir / "schema.msgpack"

        # Compile
        compile_schema(schema_file, msgpack_path, format="msgpack")

        assert msgpack_path.exists()

        # Read
        store = MsgPackStore(msgpack_path)

        # Test get_kind
        kind = store.get_kind("asset_render_image_versioned")
        assert kind is not None
        assert "$asset" in kind["template"]
        assert "asset" in kind["fields"]

        # Test get_dir
        dir_spec = store.get_dir("proj_root")
        assert dir_spec is not None
        assert dir_spec["template"] == "$root/$proj"

        # Test get_field
        field = store.get_field("root")
        assert field is not None
        assert field["regex"] == "([A-Za-z]:)?/[A-Za-z0-9/_-]+"

        # Test iter_all_kinds
        kinds = list(store.iter_all_kinds())
        assert "asset_render_image_versioned" in kinds

        store.close()

    def test_msgpack_not_found(self, temp_dir):
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            MsgPackStore(temp_dir / "nonexistent.msgpack")


class TestStoreEquivalence:
    """Test that SQLite and MsgPack stores produce equivalent results."""

    def test_stores_equivalent(self, schema_file, temp_dir):
        """Test that both stores return same data."""
        sqlite_path = temp_dir / "schema.db"
        msgpack_path = temp_dir / "schema.msgpack"

        # Compile to both formats
        compile_schema(schema_file, sqlite_path, format="sqlite")
        compile_schema(schema_file, msgpack_path, format="msgpack")

        # Open both stores
        sqlite_store = SQLiteStore(sqlite_path)
        msgpack_store = MsgPackStore(msgpack_path)

        # Compare kinds
        for kind_name in sqlite_store.iter_all_kinds():
            sqlite_kind = sqlite_store.get_kind(kind_name)
            msgpack_kind = msgpack_store.get_kind(kind_name)

            assert sqlite_kind == msgpack_kind, f"Mismatch for kind: {kind_name}"

        # Compare directories
        test_dirs = ["root", "proj_root", "asset_root", "asset_render_jpg"]
        for dir_name in test_dirs:
            sqlite_dir = sqlite_store.get_dir(dir_name)
            msgpack_dir = msgpack_store.get_dir(dir_name)

            assert sqlite_dir == msgpack_dir, f"Mismatch for dir: {dir_name}"

        # Compare fields
        test_fields = ["root", "proj", "asset", "ver", "ext"]
        for field_name in test_fields:
            sqlite_field = sqlite_store.get_field(field_name)
            msgpack_field = msgpack_store.get_field(field_name)

            assert sqlite_field == msgpack_field, f"Mismatch for field: {field_name}"

        sqlite_store.close()
        msgpack_store.close()
