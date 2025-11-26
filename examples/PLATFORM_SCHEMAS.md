# Platform-Specific Schemas

This directory contains schema files optimized for different platforms:

## Available Schemas

### 1. `schema.yml` (Cross-Platform)
- **Root path regex**: `([A-Za-z]:)?/[A-Za-z0-9/_-]+`
- **Supports**: Both Unix (`/proj`) and Windows (`C:/proj`) absolute paths
- **Use case**: Applications that need to run on multiple platforms
- **Example root**: `/proj` or `C:/proj`

### 2. `schema_linux.yml` (Linux/Unix)
- **Root path regex**: `/[A-Za-z0-9/_-]+`
- **Supports**: Unix-style absolute paths only
- **Use case**: Linux/Unix-specific deployments
- **Example root**: `/proj`, `/mnt/projects`, `/home/user/work`
- **Validation**: Rejects Windows-style paths (e.g., `C:/proj`)

### 3. `schema_windows.yml` (Windows)
- **Root path regex**: `[A-Za-z]:/[A-Za-z0-9/_-]+`
- **Supports**: Windows-style absolute paths only
- **Use case**: Windows-specific deployments
- **Example root**: `C:/proj`, `D:/work`, `Z:/shared`
- **Validation**: Rejects Unix-style paths (e.g., `/proj`)

## Usage

### Compiling Platform-Specific Schemas

```bash
# For Linux environments
python -m path_manager.compiler examples/schema_linux.yml output.db

# For Windows environments
python -m path_manager.compiler examples/schema_windows.yml output.db

# For cross-platform
python -m path_manager.compiler examples/schema.yml output.db
```

### Using in Code

```python
from path_manager.compiler import compile_schema
from path_manager.resolver import PathResolver

# Choose the appropriate schema for your platform
import sys
if sys.platform == 'win32':
    schema_file = 'examples/schema_windows.yml'
    root = 'C:/projects'
else:
    schema_file = 'examples/schema_linux.yml'
    root = '/projects'

# Compile and use
compile_schema(schema_file, 'schema.db', format='sqlite')
resolver = PathResolver.from_file('schema.db')

# Resolve paths
path = resolver.get_path(
    'asset_render_image_versioned',
    root=root,
    proj='demo',
    asset='tree',
    ver='003',
    ext='jpg'
)
```

## Benefits of Platform-Specific Schemas

1. **Stricter Validation**: Platform-specific schemas provide stronger validation by rejecting invalid path formats for the target platform.

2. **Clearer Intent**: Using `schema_linux.yml` or `schema_windows.yml` makes it explicit which platform the deployment targets.

3. **Error Prevention**: Catches platform mismatches early (e.g., trying to use Windows paths on Linux).

4. **Documentation**: The schema choice serves as documentation of platform requirements.

## Testing

All schemas are tested for both SQLite and MsgPack storage backends:

```bash
# Run all platform-specific tests
pytest tests/test_compiler_and_stores.py::TestPlatformSpecificSchemas -v
pytest tests/test_resolver.py::TestPlatformSpecificResolvers -v

# Run all tests (76 total)
pytest tests/ -v
```

## Recommendations

- **Production Deployment**: Use platform-specific schemas (`schema_linux.yml` or `schema_windows.yml`) for production to ensure path validation matches your infrastructure.

- **Development**: Use `schema.yml` (cross-platform) if your team develops on mixed platforms.

- **CI/CD**: Compile the appropriate schema during deployment based on target platform.

## Field Differences

All other fields (`proj`, `asset`, `ver`, `ext`, etc.) are identical across all schema variants. Only the `root` field regex differs to accommodate platform-specific path formats.
