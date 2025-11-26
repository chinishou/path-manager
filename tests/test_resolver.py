"""
Tests for PathResolver.
"""

import tempfile
from pathlib import Path
import warnings

import pytest

from path_manager.compiler import compile_schema
from path_manager.resolver import PathResolver, ResolvedPath
from path_manager.exceptions import ValidationError, AmbiguousPathError, AmbiguousPathWarning


@pytest.fixture
def schema_file():
    """Provide path to example schema.yml"""
    return Path(__file__).parent.parent / "examples" / "schema.yml"


@pytest.fixture
def compiled_sqlite(schema_file, tmp_path):
    """Provide compiled SQLite database."""
    db_path = tmp_path / "schema.db"
    compile_schema(schema_file, db_path, format="sqlite")
    return db_path


@pytest.fixture
def compiled_msgpack(schema_file, tmp_path):
    """Provide compiled MsgPack file."""
    msgpack_path = tmp_path / "schema.msgpack"
    compile_schema(schema_file, msgpack_path, format="msgpack")
    return msgpack_path


@pytest.fixture(params=["sqlite", "msgpack"])
def resolver(request, compiled_sqlite, compiled_msgpack):
    """Provide resolver with both storage backends."""
    if request.param == "sqlite":
        res = PathResolver.from_file(compiled_sqlite)
    else:
        res = PathResolver.from_file(compiled_msgpack)

    yield res
    res.close()


class TestPathResolverForward:
    """Test forward path resolution (kind + fields -> path)."""

    def test_resolve_kind_with_fields(self, resolver):
        """Test basic path resolution."""
        path = resolver.get_path(
            "asset_render_image_versioned",
            root="/proj",
            proj="demo",
            asset="tree",
            ver="003",
            ext="jpg"
        )

        assert str(path) == "/proj/demo/asset/tree/render/jpg/tree.v003.jpg"

    def test_resolve_directory(self, resolver):
        """Test resolving directory path."""
        path = resolver.get_path(
            "proj_root",
            root="/proj",
            proj="demo"
        )

        assert str(path) == "/proj/demo"

    def test_resolve_with_callable(self, resolver):
        """Test using callable syntax."""
        resolved = resolver(
            "asset_render_image_versioned",
            root="/proj",
            proj="demo",
            asset="tree",
            ver="003",
            ext="jpg"
        )

        assert isinstance(resolved, ResolvedPath)
        assert str(resolved.get_path()) == "/proj/demo/asset/tree/render/jpg/tree.v003.jpg"

    def test_missing_field(self, resolver):
        """Test error when required field is missing."""
        with pytest.raises(ValidationError, match="Missing fields"):
            resolver.get_path(
                "asset_render_image_versioned",
                root="/proj",
                proj="demo",
                # Missing: asset, ver, ext
            )

    def test_invalid_field_value(self, resolver):
        """Test validation error for invalid field value."""
        with pytest.raises(ValidationError, match="doesn't match regex"):
            resolver.get_path(
                "asset_render_image_versioned",
                root="/proj",
                proj="demo",
                asset="tree",
                ver="v003",  # Invalid: should be "003" (3 digits only)
                ext="jpg"
            )

    def test_unknown_kind(self, resolver):
        """Test error when kind doesn't exist."""
        with pytest.raises(KeyError, match="Unknown kind"):
            resolver.get_path("nonexistent_kind", root="/proj")


class TestResolvedPath:
    """Test ResolvedPath object."""

    def test_get_template(self, resolver):
        """Test getting original template."""
        resolved = resolver(
            "asset_render_image_versioned",
            root="/proj",
            proj="demo",
            asset="tree",
            ver="003",
            ext="jpg"
        )

        template = resolved.get_template()
        assert "$asset" in template
        assert "$ver" in template

    def test_get_fields(self, resolver):
        """Test getting field values."""
        resolved = resolver(
            "asset_render_image_versioned",
            root="/proj",
            proj="demo",
            asset="tree",
            ver="003",
            ext="jpg"
        )

        fields = resolved.get_fields()
        assert fields["asset"] == "tree"
        assert fields["ver"] == "003"

    def test_exists(self, resolver, tmp_path):
        """Test exists() method."""
        resolved = resolver(
            "proj_root",
            root=tmp_path.as_posix(),
            proj="test"
        )

        # Initially doesn't exist
        assert not resolved.exists()

        # Create it
        resolved.mkdir(parents=True)

        # Now exists
        assert resolved.exists()


class TestPathResolverReverse:
    """Test reverse path resolution (path -> kind + fields)."""

    def test_parse_with_known_kind(self, resolver):
        """Test parsing path with known kind."""
        path = "/proj/demo/asset/tree/render/jpg/tree.v003.jpg"

        fields = resolver.parse("asset_render_image_versioned", path)

        assert fields["root"] == "/proj"
        assert fields["proj"] == "demo"
        assert fields["asset"] == "tree"
        assert fields["ver"] == "003"
        assert fields["ext"] == "jpg"

    def test_parse_directory(self, resolver):
        """Test parsing directory path."""
        path = "/proj/demo"

        fields = resolver.parse("proj_root", path)

        assert fields["root"] == "/proj"
        assert fields["proj"] == "demo"

    def test_parse_mismatch(self, resolver):
        """Test error when path doesn't match template."""
        path = "/wrong/structure/here.jpg"

        with pytest.raises(ValidationError, match="doesn't match template"):
            resolver.parse("asset_render_image_versioned", path)

    def test_guess_single_match(self, resolver):
        """Test guessing kind when there's only one match."""
        path = "/proj/demo/asset/tree/render/jpg/tree.v003.jpg"

        candidates = resolver.guess(path, warn=False)

        # Should match asset_render_image_versioned
        assert len(candidates) >= 1

        kind_names = [k for k, _ in candidates]
        assert "asset_render_image_versioned" in kind_names

    def test_guess_with_warning(self, resolver):
        """Test that guess() warns on ambiguity."""
        # Create a path that might match multiple kinds
        # (depends on schema having ambiguous patterns)
        path = "/proj/demo/asset/tree/render/jpg/tree.jpg"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            candidates = resolver.guess(path, warn=True)

            # If ambiguous, should have warning
            if len(candidates) > 1:
                assert len(w) == 1
                assert issubclass(w[0].category, AmbiguousPathWarning)

    def test_guess_one_success(self, resolver):
        """Test guess_one with single match."""
        path = "/proj/demo/asset/tree/render/jpg/tree.v003.jpg"

        kind, fields = resolver.guess_one(path)

        assert kind == "asset_render_image_versioned"
        assert fields["asset"] == "tree"

    def test_guess_one_with_preference(self, resolver):
        """Test guess_one with preference when ambiguous."""
        # This would need an ambiguous path in the schema
        # For now, just test that prefer parameter works
        path = "/proj/demo/asset/tree/render/jpg/tree.v003.jpg"

        kind, fields = resolver.guess_one(path, prefer="asset_render_image_versioned")

        assert kind == "asset_render_image_versioned"

    def test_guess_no_match(self, resolver):
        """Test error when no kind matches."""
        path = "/completely/wrong/path.xyz"

        with pytest.raises(ValidationError, match="No kind matches"):
            resolver.guess_one(path)


class TestContextManager:
    """Test context manager support."""

    def test_resolver_context_manager(self, compiled_sqlite):
        """Test using resolver as context manager."""
        with PathResolver.from_file(compiled_sqlite) as resolver:
            path = resolver.get_path(
                "proj_root",
                root="/proj",
                proj="demo"
            )
            assert str(path) == "/proj/demo"

        # Should be closed after context
        # (Can't test this easily without checking internal state)
