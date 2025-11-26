# Path Manager

Schema-driven dynamic path management system for production pipelines.

## Features

- 🎯 **Schema-Driven**: Define path structures once in YAML, use everywhere
- 🔄 **Bidirectional Resolution**: Generate paths from fields, extract fields from paths
- 🗃️ **Dual Storage Backends**: SQLite (with NFS-safe immutable mode) and indexed MsgPack
- 🖥️ **Platform-Specific Schemas**: Dedicated schemas for Linux, Windows, or cross-platform use
- ⚡ **Lazy Loading**: Load only needed schema parts for efficient memory usage
- 🔍 **Ambiguity Detection**: Compile-time detection of overlapping path patterns
- 📁 **Structure Manager**: Automated directory/file creation from structure definitions
- ✅ **Fully Tested**: 76 tests covering both storage backends and all platforms

## Installation

```bash
# Install from source
pip install -e .

# With development dependencies
pip install -e ".[dev]"
```

**Requirements**: Python >=3.10

## Quick Start

### 1. Define Schema

Choose the appropriate schema for your platform:

```yaml
# examples/schema_linux.yml (Linux/Unix)
fields:
  root:
    regex: "/[A-Za-z0-9/_-]+"
    example: "/proj"
  proj:
    regex: "[A-Za-z0-9_]+"
    example: "demo_proj"
  asset:
    regex: "[A-Za-z0-9_]+"
    example: "tree"
  ver:
    regex: "[0-9]{3}"
    example: "003"
  ext:
    regex: "[a-z0-9]+"
    example: "jpg"

directories:
  name: root
  segment: "$root"
  children:
    - name: proj_root
      segment: "$proj"
      children:
        - name: assets_root
          segment: "asset"
          children:
            - name: asset_root
              segment: "$asset"
              children:
                - name: asset_render
                  segment: "render"
                  children:
                    - name: asset_render_jpg
                      segment: "jpg"

filenames:
  asset_render_versioned:
    template: "$asset.v$ver.$ext"

kinds:
  asset_render_image_versioned:
    directory: asset_render_jpg
    filename: asset_render_versioned
```

### 2. Compile Schema

```bash
# Compile to SQLite (recommended for production)
python -m path_manager.compiler examples/schema_linux.yml schema.db --format sqlite

# Or compile to MsgPack (zero-dependency alternative)
python -m path_manager.compiler examples/schema_linux.yml schema.msgpack --format msgpack
```

### 3. Use in Code

```python
from path_manager.resolver import PathResolver

# Load compiled schema
resolver = PathResolver.from_file('schema.db')

# Forward resolution: Generate path from fields
path = resolver.get_path(
    'asset_render_image_versioned',
    root='/proj',
    proj='demo',
    asset='tree',
    ver='003',
    ext='jpg'
)
print(path.as_posix())
# Output: /proj/demo/asset/tree/render/jpg/tree.v003.jpg

# Reverse resolution: Extract fields from path
fields = resolver.parse(
    'asset_render_image_versioned',
    '/proj/demo/asset/tree/render/jpg/tree.v003.jpg'
)
print(fields)
# Output: {'root': '/proj', 'proj': 'demo', 'asset': 'tree', 'ver': '003', 'ext': 'jpg'}

# Guess kind from path (when kind unknown)
kind, fields = resolver.guess_one('/proj/demo/asset/tree/render/jpg/tree.v003.jpg')
print(kind)
# Output: asset_render_image_versioned

resolver.close()
```

## Platform-Specific Schemas

Path Manager provides three schema variants:

| Schema | Platform | Root Regex | Example Root |
|--------|----------|------------|--------------|
| `schema.yml` | Cross-platform | `([A-Za-z]:)?/[A-Za-z0-9/_-]+` | `/proj` or `C:/proj` |
| `schema_linux.yml` | Linux/Unix only | `/[A-Za-z0-9/_-]+` | `/proj`, `/mnt/data` |
| `schema_windows.yml` | Windows only | `[A-Za-z]:/[A-Za-z0-9/_-]+` | `C:/proj`, `D:/work` |

### Platform Selection

```python
import sys
from path_manager.compiler import compile_schema
from path_manager.resolver import PathResolver

# Auto-select schema based on platform
if sys.platform == 'win32':
    schema_file = 'examples/schema_windows.yml'
    root = 'C:/projects'
else:
    schema_file = 'examples/schema_linux.yml'
    root = '/projects'

# Compile and use
compile_schema(schema_file, 'schema.db', format='sqlite')
resolver = PathResolver.from_file('schema.db')

path = resolver.get_path('proj_root', root=root, proj='demo')
print(path.as_posix())
```

**Benefits of Platform-Specific Schemas:**
- Stricter validation (reject invalid path formats early)
- Clear deployment intent
- Better error messages
- Production-ready validation

See [examples/PLATFORM_SCHEMAS.md](examples/PLATFORM_SCHEMAS.md) for detailed documentation.

## Advanced Features

### ResolvedPath Object

```python
# Callable syntax returns ResolvedPath object
resolved = resolver(
    'asset_render_image_versioned',
    root='/proj',
    proj='demo',
    asset='tree',
    ver='003',
    ext='jpg'
)

# Access path
print(str(resolved))  # POSIX format
print(resolved.get_path())  # Path object

# Get metadata
print(resolved.get_template())  # "$root/$proj/asset/$asset/render/jpg/$asset.v$ver.$ext"
print(resolved.get_fields())    # {'root': '/proj', 'proj': 'demo', ...}

# File operations
if not resolved.exists():
    resolved.mkdir(parents=True)
```

### Structure Manager

Automate directory/file creation from structure definitions:

```python
from path_manager.structure_manager import StructureManager

# Load structures.yml
manager = StructureManager(resolver, 'examples/structures.yml')

# Create project structure
created = manager.create(
    'project_basic',
    root='/proj',
    proj='new_project'
)

# Conditional creation based on context
created = manager.create(
    'project_dev',
    context={'is_dev': True},  # Only create dev directories
    root='/proj',
    proj='new_project'
)

# Dry run to preview
manager.create(
    'project_basic',
    root='/proj',
    proj='test',
    dry_run=True
)
```

### Context Manager Support

```python
# Automatic resource cleanup
with PathResolver.from_file('schema.db') as resolver:
    path = resolver.get_path('proj_root', root='/proj', proj='demo')
    print(path)
# Resolver automatically closed
```

### Ambiguity Handling

```python
# Get all matching kinds
candidates = resolver.guess('/proj/demo/asset/tree.jpg', warn=True)
for kind, fields in candidates:
    print(f"{kind}: {fields}")

# Prefer specific kind when ambiguous
kind, fields = resolver.guess_one(
    '/proj/demo/asset/tree.jpg',
    prefer='asset_render_image'
)
```

## Storage Backends

### SQLite (Recommended for Production)

- **NFS-Safe**: Opens with `immutable=1` flag for concurrent reads
- **Efficient**: B-tree indexes for fast lookups
- **Lazy Loading**: Query-based access
- **Read-Only**: Prevents accidental modifications

```python
from path_manager.stores import SQLiteStore

store = SQLiteStore('schema.db')
kind = store.get_kind('asset_render_image_versioned')
store.close()
```

### MsgPack (Zero-Dependency Alternative)

- **Portable**: Single binary file
- **Fast**: Memory-mapped I/O
- **Indexed**: Quick field/kind/dir lookups
- **No SQLite Dependency**: Pure Python with msgpack

```python
from path_manager.stores import MsgPackStore

store = MsgPackStore('schema.msgpack')
kind = store.get_kind('asset_render_image_versioned')
store.close()
```

## Architecture

```
┌─────────────┐
│ schema.yml  │  Define once
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Compiler   │  Compile-time validation
└──────┬──────┘  - Extract fields
       │         - Expand directory trees
       │         - Detect ambiguities
       │
       ├────────────┬────────────┐
       ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ SQLite   │  │ MsgPack  │  │  JSON    │
│ (NFS)    │  │ (mmap)   │  │ (debug)  │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │            │            │
     └────────────┴────────────┘
                  │
                  ▼
          ┌──────────────┐
          │   Resolver   │  Runtime
          └──────┬───────┘  - Forward: kind+fields → path
                 │          - Reverse: path → kind+fields
                 │          - Lazy loading
                 ▼
         ┌──────────────┐
         │ Application  │
         └──────────────┘
```

## Testing

```bash
# Run all tests (76 tests)
pytest tests/ -v

# Run specific test suites
pytest tests/test_compiler_and_stores.py -v
pytest tests/test_resolver.py -v
pytest tests/test_structure_manager.py -v

# Run platform-specific tests
pytest tests/test_compiler_and_stores.py::TestPlatformSpecificSchemas -v
pytest tests/test_resolver.py::TestPlatformSpecificResolvers -v

# Test coverage
pytest tests/ --cov=path_manager --cov-report=html
```

## Performance

- **Compilation**: One-time cost, typically <1s for typical schemas
- **Lazy Loading**: Only loads required kinds/dirs/fields
- **Memory Efficient**: Minimal memory footprint
- **NFS-Safe**: Concurrent reads without locking issues

## Production Deployment

### Recommended Setup

1. **Compile during CI/CD**:
   ```bash
   python -m path_manager.compiler schema_linux.yml /shared/schema.db --format sqlite
   chmod 444 /shared/schema.db  # Read-only
   ```

2. **Deploy to NFS**:
   - SQLite with `immutable=1` flag (automatic)
   - Read-only permissions
   - All clients load same compiled schema

3. **Version Control**:
   - Commit `schema.yml` to git
   - Tag schema versions
   - Compiled files are artifacts (don't commit)

### Multi-Person Schema Editing

For teams, use git workflow:

```bash
# Developer workflow
git checkout -b feature/add-sequence-paths
# Edit schema.yml
git commit -m "Add sequence path kinds"
git push origin feature/add-sequence-paths

# CI/CD automatically compiles on merge to main
# Deploys compiled schema.db to production NFS
```

## API Reference

### Compiler

```python
from path_manager.compiler import compile_schema, SchemaCompiler

# High-level function
compile_schema(
    schema_path='schema.yml',
    output_path='schema.db',
    format='sqlite'  # or 'msgpack'
)

# Low-level API
compiler = SchemaCompiler('schema.yml')
compiler.compile()
compiler.save_sqlite('schema.db')
compiler.save_msgpack('schema.msgpack')
```

### Resolver

```python
from path_manager.resolver import PathResolver

# Create resolver
resolver = PathResolver.from_file('schema.db')

# Forward resolution
path = resolver.get_path(kind, **fields)
resolved = resolver(kind, **fields)  # Returns ResolvedPath

# Reverse resolution
fields = resolver.parse(kind, path)
candidates = resolver.guess(path, warn=True)
kind, fields = resolver.guess_one(path, prefer=None)

# Cleanup
resolver.close()
```

### ResolvedPath

```python
resolved = resolver(kind, **fields)

# Path access
resolved.get_path()       # → Path object
resolved.get_path_str()   # → POSIX string
str(resolved)             # → POSIX string

# Metadata
resolved.get_template()   # → Original template
resolved.get_fields()     # → Field values

# Operations
resolved.exists()         # → bool
resolved.mkdir(**kwargs)  # Create directory
resolved.parse(path)      # Parse another path with same kind
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
