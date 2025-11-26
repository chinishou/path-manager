# API Reference

Complete API reference for Path Manager.

## Table of Contents

- [Compiler API](#compiler-api)
- [Resolver API](#resolver-api)
- [ResolvedPath API](#resolvedpath-api)
- [Store API](#store-api)
- [Structure Manager API](#structure-manager-api)
- [Exceptions](#exceptions)

---

## Compiler API

### `compile_schema()`

High-level function to compile a schema file.

```python
from path_manager.compiler import compile_schema

compile_schema(
    schema_path: str | Path,
    output_path: str | Path,
    format: str = 'sqlite'
) -> None
```

**Parameters:**
- `schema_path`: Path to YAML schema file
- `output_path`: Path for compiled output
- `format`: Output format - `'sqlite'` or `'msgpack'`

**Example:**
```python
compile_schema('schema.yml', 'schema.db', format='sqlite')
compile_schema('schema.yml', 'schema.msgpack', format='msgpack')
```

---

### `SchemaCompiler`

Low-level class for schema compilation.

```python
from path_manager.compiler import SchemaCompiler

compiler = SchemaCompiler(schema_path: str | Path)
```

#### Methods

##### `compile()`

Compile the schema and perform validation.

```python
compiler.compile() -> None
```

**Raises:**
- `SchemaError`: If schema validation fails

**Example:**
```python
compiler = SchemaCompiler('schema.yml')
compiler.compile()
```

##### `save_sqlite()`

Save compiled schema to SQLite database.

```python
compiler.save_sqlite(db_path: str | Path) -> None
```

##### `save_msgpack()`

Save compiled schema to MsgPack file.

```python
compiler.save_msgpack(msgpack_path: str | Path) -> None
```

##### `save_json()`

Save compiled schema to JSON file (for debugging).

```python
compiler.save_json(json_path: str | Path) -> None
```

#### Properties

##### `fields`

Dictionary of field definitions.

```python
compiler.fields -> dict[str, dict]
# Example: {'root': {'regex': '/[A-Za-z0-9/_-]+', 'example': '/proj'}}
```

##### `dirs`

Dictionary of directory definitions.

```python
compiler.dirs -> dict[str, dict]
# Example: {'proj_root': {'template': '$root/$proj', 'fields': ['root', 'proj']}}
```

##### `kinds`

Dictionary of kind definitions.

```python
compiler.kinds -> dict[str, dict]
# Example: {'asset_render': {'template': '...', 'fields': [...]}}
```

##### `ambiguities`

Dictionary of detected ambiguities.

```python
compiler.ambiguities -> dict[str, list[str]]
# Example: {'$root/$proj/$asset.jpg': ['asset_render', 'asset_texture']}
```

---

## Resolver API

### `PathResolver`

Main class for path resolution.

```python
from path_manager.resolver import PathResolver
```

#### Class Methods

##### `from_file()`

Create resolver from compiled schema file.

```python
PathResolver.from_file(
    path: str | Path,
    store_type: str = 'auto'
) -> PathResolver
```

**Parameters:**
- `path`: Path to compiled schema (`.db` or `.msgpack`)
- `store_type`: Store type - `'auto'`, `'sqlite'`, or `'msgpack'`

**Example:**
```python
resolver = PathResolver.from_file('schema.db')
resolver = PathResolver.from_file('schema.msgpack')
```

#### Instance Methods

##### `get_path()`

Generate path from kind and fields (returns Path object).

```python
resolver.get_path(
    kind: str,
    **fields: Any
) -> Path
```

**Parameters:**
- `kind`: Kind name
- `**fields`: Field values as keyword arguments

**Returns:** `pathlib.Path` object

**Raises:**
- `ValidationError`: If fields don't match regex or are missing
- `ValueError`: If kind doesn't exist

**Example:**
```python
path = resolver.get_path(
    'asset_render_image',
    root='/proj',
    proj='demo',
    asset='tree',
    ext='jpg'
)
# Returns: Path('/proj/demo/asset/tree/render/jpg/tree.jpg')
```

##### `__call__()` (Callable Syntax)

Generate path and return ResolvedPath object.

```python
resolver(kind: str, **fields: Any) -> ResolvedPath
```

**Parameters:** Same as `get_path()`

**Returns:** `ResolvedPath` object

**Example:**
```python
resolved = resolver(
    'asset_render_image',
    root='/proj',
    proj='demo',
    asset='tree',
    ext='jpg'
)
# Returns: ResolvedPath object
```

##### `parse()`

Extract fields from path (reverse resolution).

```python
resolver.parse(
    kind: str,
    path: str | Path
) -> dict[str, str]
```

**Parameters:**
- `kind`: Expected kind name
- `path`: Path to parse

**Returns:** Dictionary of field name → value

**Raises:**
- `ValidationError`: If path doesn't match kind pattern

**Example:**
```python
fields = resolver.parse(
    'asset_render_image',
    '/proj/demo/asset/tree/render/jpg/tree.jpg'
)
# Returns: {'root': '/proj', 'proj': 'demo', 'asset': 'tree', 'ext': 'jpg'}
```

##### `guess()`

Find all kinds matching a path.

```python
resolver.guess(
    path: str | Path,
    warn: bool = True
) -> list[tuple[str, dict[str, str]]]
```

**Parameters:**
- `path`: Path to analyze
- `warn`: Warn if multiple matches found

**Returns:** List of (kind_name, fields) tuples

**Example:**
```python
matches = resolver.guess('/proj/demo/asset/tree.jpg')
for kind, fields in matches:
    print(f"{kind}: {fields}")
```

##### `guess_one()`

Find best matching kind for a path.

```python
resolver.guess_one(
    path: str | Path,
    prefer: str | None = None
) -> tuple[str, dict[str, str]]
```

**Parameters:**
- `path`: Path to analyze
- `prefer`: Preferred kind name (used if ambiguous)

**Returns:** Tuple of (kind_name, fields)

**Raises:**
- `ValidationError`: If no kind matches

**Example:**
```python
kind, fields = resolver.guess_one(
    '/proj/demo/asset/tree.jpg',
    prefer='asset_render_image'
)
```

##### `close()`

Close underlying store and release resources.

```python
resolver.close() -> None
```

#### Context Manager Support

```python
with PathResolver.from_file('schema.db') as resolver:
    path = resolver.get_path('proj_root', root='/proj', proj='demo')
    # ... use resolver ...
# Automatically closed
```

---

## ResolvedPath API

Object representing a resolved path with metadata.

```python
from path_manager.resolver import ResolvedPath
```

### Methods

#### `get_path()`

Get the path as a Path object.

```python
resolved.get_path() -> Path
```

**Returns:** `pathlib.Path` object

#### `get_path_str()`

Get the path as a POSIX string.

```python
resolved.get_path_str() -> str
```

**Returns:** Path string with forward slashes

#### `__str__()`

String representation (POSIX format).

```python
str(resolved) -> str
```

**Returns:** Same as `get_path_str()`

#### `as_posix()`

Get POSIX path string.

```python
resolved.as_posix() -> str
```

**Returns:** Path with forward slashes

#### `get_template()`

Get the template used to generate this path.

```python
resolved.get_template() -> str
```

**Returns:** Template string (e.g., `"$root/$proj/asset/$asset.jpg"`)

#### `get_fields()`

Get the field values used.

```python
resolved.get_fields() -> dict[str, str]
```

**Returns:** Dictionary of field name → value

#### `exists()`

Check if path exists on filesystem.

```python
resolved.exists() -> bool
```

#### `mkdir()`

Create directory.

```python
resolved.mkdir(
    mode: int = 0o777,
    parents: bool = False,
    exist_ok: bool = False
) -> None
```

**Parameters:** Same as `pathlib.Path.mkdir()`

#### `parse()`

Parse another path using the same kind.

```python
resolved.parse(path: str | Path) -> dict[str, str]
```

**Parameters:**
- `path`: Path to parse

**Returns:** Dictionary of field name → value

---

## Store API

Low-level storage backend API.

### `CompiledStore` (Abstract Base)

```python
from path_manager.stores.base import CompiledStore
```

All stores implement this interface.

#### Methods

##### `get_kind()`

```python
store.get_kind(name: str) -> dict | None
```

##### `get_dir()`

```python
store.get_dir(name: str) -> dict | None
```

##### `get_field()`

```python
store.get_field(name: str) -> dict | None
```

##### `iter_all_kinds()`

```python
store.iter_all_kinds() -> Iterator[str]
```

##### `get_ambiguities()`

```python
store.get_ambiguities() -> dict[str, list[str]]
```

##### `close()`

```python
store.close() -> None
```

### `SQLiteStore`

SQLite storage backend.

```python
from path_manager.stores import SQLiteStore

store = SQLiteStore(db_path: str | Path)
```

**Features:**
- Opens with `immutable=1` flag for NFS safety
- Supports concurrent reads
- B-tree indexes for fast lookups

### `MsgPackStore`

MsgPack storage backend.

```python
from path_manager.stores import MsgPackStore

store = MsgPackStore(file_path: str | Path)
```

**Features:**
- Memory-mapped I/O
- Indexed for fast lookups
- No SQLite dependency

---

## Structure Manager API

### `StructureManager`

Automate directory/file creation.

```python
from path_manager.structure_manager import StructureManager

manager = StructureManager(
    resolver: PathResolver,
    structures_file: str | Path
)
```

#### Methods

##### `list_structures()`

List available structure definitions.

```python
manager.list_structures() -> list[str]
```

**Returns:** List of structure names

##### `get_structure_info()`

Get structure definition.

```python
manager.get_structure_info(name: str) -> dict
```

**Parameters:**
- `name`: Structure name

**Returns:** Structure definition dictionary

**Raises:**
- `ValueError`: If structure doesn't exist

##### `create()`

Create directory/file structure.

```python
manager.create(
    structure_name: str,
    context: dict | None = None,
    dry_run: bool = False,
    **fields: Any
) -> list[Path]
```

**Parameters:**
- `structure_name`: Name of structure to create
- `context`: Context dict for conditional creation
- `dry_run`: Preview without creating
- `**fields`: Field values

**Returns:** List of created paths

**Example:**
```python
created = manager.create(
    'project_basic',
    root='/proj',
    proj='new_project'
)

# With context
created = manager.create(
    'project_dev',
    context={'is_dev': True},
    root='/proj',
    proj='dev_project'
)

# Dry run
manager.create(
    'project_basic',
    root='/proj',
    proj='test',
    dry_run=True
)
```

---

## Exceptions

### `PathManagerError`

Base exception class.

```python
from path_manager.exceptions import PathManagerError
```

### `SchemaError`

Raised for schema validation errors.

```python
from path_manager.exceptions import SchemaError
```

**Common causes:**
- Missing required fields
- Invalid YAML syntax
- Missing field regex definitions
- Invalid directory tree structure

### `ValidationError`

Raised for field validation errors.

```python
from path_manager.exceptions import ValidationError
```

**Common causes:**
- Field value doesn't match regex
- Missing required fields
- Path doesn't match kind pattern

### `AmbiguousPathError`

Raised when path matches multiple kinds.

```python
from path_manager.exceptions import AmbiguousPathError
```

**Attributes:**
- `path`: The ambiguous path
- `candidates`: List of matching kind names

### `AmbiguousPathWarning`

Warning for ambiguous paths.

```python
from path_manager.exceptions import AmbiguousPathWarning
```

---

## Type Hints

Path Manager supports full type hints:

```python
from typing import Any
from pathlib import Path
from path_manager.resolver import PathResolver, ResolvedPath

def process_asset(
    resolver: PathResolver,
    asset_name: str,
    version: int
) -> ResolvedPath:
    return resolver(
        'asset_render_image_versioned',
        root='/proj',
        proj='demo',
        asset=asset_name,
        ver=f"{version:03d}",
        ext='jpg'
    )
```

---

## Performance Notes

### Lazy Loading

Both stores support lazy loading - only requested data is loaded:

```python
# Only loads 'asset_render_image' kind
kind = store.get_kind('asset_render_image')
```

### Connection Pooling

For multi-threaded applications, create one resolver per thread:

```python
import threading

def worker():
    with PathResolver.from_file('schema.db') as resolver:
        # Use resolver in this thread
        pass

threads = [threading.Thread(target=worker) for _ in range(10)]
```

### Memory Usage

- SQLite: Minimal memory (query-based)
- MsgPack: Memory-mapped (OS manages memory)

---

## Version Compatibility

- Python: >=3.10
- pathlib: Standard library
- pyyaml: >=6.0
- msgpack: >=1.0.0

For older Python versions (3.9), use `from __future__ import annotations`.
