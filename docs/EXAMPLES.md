# Usage Examples

Practical examples for common Path Manager use cases.

## Table of Contents

- [Basic Usage](#basic-usage)
- [VFX Pipeline Examples](#vfx-pipeline-examples)
- [Game Development Examples](#game-development-examples)
- [Platform-Specific Usage](#platform-specific-usage)
- [Advanced Patterns](#advanced-patterns)
- [Error Handling](#error-handling)
- [Integration Examples](#integration-examples)

---

## Basic Usage

### Example 1: Simple Path Generation

```python
from path_manager.compiler import compile_schema
from path_manager.resolver import PathResolver

# Compile schema once
compile_schema('schema.yml', 'schema.db', format='sqlite')

# Use resolver
with PathResolver.from_file('schema.db') as resolver:
    # Generate path
    path = resolver.get_path(
        'asset_render_image',
        root='/proj',
        proj='demo',
        asset='tree',
        ext='jpg'
    )

    print(path.as_posix())
    # Output: /proj/demo/asset/tree/render/jpg/tree.jpg
```

### Example 2: Path Parsing

```python
from path_manager.resolver import PathResolver

with PathResolver.from_file('schema.db') as resolver:
    # Parse existing path
    fields = resolver.parse(
        'asset_render_image',
        '/proj/demo/asset/tree/render/jpg/tree.jpg'
    )

    print(fields)
    # Output: {'root': '/proj', 'proj': 'demo', 'asset': 'tree', 'ext': 'jpg'}

    # Use extracted fields
    asset_name = fields['asset']
    project = fields['proj']
```

### Example 3: Automatic Kind Detection

```python
from path_manager.resolver import PathResolver

with PathResolver.from_file('schema.db') as resolver:
    # Unknown kind - let resolver figure it out
    path = '/proj/demo/asset/tree/render/jpg/tree.v003.jpg'

    kind, fields = resolver.guess_one(path)

    print(f"Kind: {kind}")
    print(f"Fields: {fields}")
    # Output:
    # Kind: asset_render_image_versioned
    # Fields: {'root': '/proj', 'proj': 'demo', 'asset': 'tree', 'ver': '003', 'ext': 'jpg'}
```

---

## VFX Pipeline Examples

### Example 4: Shot-Based Asset Publishing

```python
from pathlib import Path
from path_manager.resolver import PathResolver

class AssetPublisher:
    def __init__(self, schema_path: str):
        self.resolver = PathResolver.from_file(schema_path)

    def publish_render(self, shot: str, version: int, frame: int) -> Path:
        """Publish a rendered frame."""
        resolved = self.resolver(
            'shot_render_exr',
            root='/mnt/projects',
            proj='feature_film',
            seq='S01',
            shot=shot,
            ver=f'{version:03d}',
            frame=f'{frame:04d}'
        )

        # Ensure directory exists
        resolved.get_path().parent.mkdir(parents=True, exist_ok=True)

        return resolved.get_path()

    def get_latest_version(self, shot: str) -> int:
        """Find latest published version."""
        # Parse existing files to find max version
        render_dir = self.resolver.get_path(
            'shot_render_dir',
            root='/mnt/projects',
            proj='feature_film',
            seq='S01',
            shot=shot
        )

        versions = []
        if render_dir.exists():
            for file in render_dir.glob('*.exr'):
                try:
                    fields = self.resolver.parse('shot_render_exr', file)
                    versions.append(int(fields['ver']))
                except:
                    continue

        return max(versions) if versions else 0

    def close(self):
        self.resolver.close()

# Usage
publisher = AssetPublisher('schema.db')

# Publish new version
latest = publisher.get_latest_version('0010')
new_version = latest + 1

for frame in range(1, 101):
    output_path = publisher.publish_render('0010', new_version, frame)
    print(f"Rendering to: {output_path}")
    # ... render frame ...

publisher.close()
```

### Example 5: Batch Path Conversion

```python
from path_manager.resolver import PathResolver
import json

def convert_legacy_paths(legacy_paths: list[str], output_file: str):
    """Convert legacy paths to new structure."""

    with PathResolver.from_file('schema.db') as resolver:
        converted = {}

        for old_path in legacy_paths:
            # Try to parse with new schema
            try:
                kind, fields = resolver.guess_one(old_path)

                # Generate new path
                new_path = resolver.get_path(kind, **fields)

                converted[old_path] = {
                    'new_path': str(new_path),
                    'kind': kind,
                    'fields': fields
                }
            except Exception as e:
                converted[old_path] = {'error': str(e)}

        # Save mapping
        with open(output_file, 'w') as f:
            json.dump(converted, f, indent=2)

# Usage
legacy_paths = [
    '/old/proj/demo/assets/tree/render.jpg',
    '/old/proj/demo/assets/rock/model.ma',
]

convert_legacy_paths(legacy_paths, 'path_mapping.json')
```

### Example 6: Automated Dailies Generation

```python
from path_manager.resolver import PathResolver
from path_manager.structure_manager import StructureManager
from datetime import datetime

class DailiesGenerator:
    def __init__(self, schema_db: str, structures_yml: str):
        self.resolver = PathResolver.from_file(schema_db)
        self.manager = StructureManager(self.resolver, structures_yml)

    def setup_dailies_structure(self, date: str = None) -> dict:
        """Create directory structure for dailies."""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        created = self.manager.create(
            'dailies_structure',
            root='/mnt/projects',
            proj='feature_film',
            date=date
        )

        return {
            'date': date,
            'paths': [str(p) for p in created]
        }

    def collect_shots(self, sequence: str, shots: list[str]) -> list[dict]:
        """Collect latest renders for shots."""
        results = []

        for shot in shots:
            # Find latest version
            shot_dir = self.resolver.get_path(
                'shot_render_dir',
                root='/mnt/projects',
                proj='feature_film',
                seq=sequence,
                shot=shot
            )

            if shot_dir.exists():
                versions = []
                for exr in shot_dir.glob('*.exr'):
                    fields = self.resolver.parse('shot_render_exr', exr)
                    versions.append({
                        'version': int(fields['ver']),
                        'path': exr
                    })

                if versions:
                    latest = max(versions, key=lambda x: x['version'])
                    results.append({
                        'shot': shot,
                        'version': latest['version'],
                        'path': latest['path']
                    })

        return results

    def close(self):
        self.resolver.close()

# Usage
dailies = DailiesGenerator('schema.db', 'structures.yml')

# Setup structure
info = dailies.setup_dailies_structure()
print(f"Created dailies structure for {info['date']}")

# Collect shots
shots = dailies.collect_shots('S01', ['0010', '0020', '0030'])
for shot in shots:
    print(f"{shot['shot']} v{shot['version']:03d}: {shot['path']}")

dailies.close()
```

---

## Game Development Examples

### Example 7: Asset Bundle Organization

```python
from path_manager.resolver import PathResolver
from pathlib import Path
import shutil

class AssetBundleManager:
    def __init__(self, schema_db: str):
        self.resolver = PathResolver.from_file(schema_db)

    def organize_texture(self, asset_name: str, texture_type: str,
                        source_file: Path) -> Path:
        """Organize texture into proper location."""

        # Determine target path
        target = self.resolver(
            'game_asset_texture',
            root='/game/assets',
            category='characters',
            asset=asset_name,
            texture_type=texture_type,
            ext=source_file.suffix[1:]  # Remove leading dot
        )

        # Ensure directory exists
        target.mkdir(parents=True)

        # Copy file
        dest = target.get_path()
        shutil.copy2(source_file, dest)

        return dest

    def get_asset_manifest(self, asset_name: str) -> dict:
        """Get all files for an asset."""

        asset_dir = self.resolver.get_path(
            'game_asset_dir',
            root='/game/assets',
            category='characters',
            asset=asset_name
        )

        manifest = {
            'asset': asset_name,
            'textures': [],
            'models': [],
            'animations': []
        }

        if asset_dir.exists():
            # Collect textures
            for tex in asset_dir.glob('textures/*'):
                fields = self.resolver.parse('game_asset_texture', tex)
                manifest['textures'].append(fields)

            # Similar for models, animations, etc.

        return manifest

    def close(self):
        self.resolver.close()

# Usage
manager = AssetBundleManager('game_schema.db')

# Organize textures
manager.organize_texture('hero', 'diffuse', Path('hero_diffuse.png'))
manager.organize_texture('hero', 'normal', Path('hero_normal.png'))

# Get manifest
manifest = manager.get_asset_manifest('hero')
print(f"Asset 'hero' has {len(manifest['textures'])} textures")

manager.close()
```

### Example 8: Level Data Management

```python
from path_manager.resolver import PathResolver
import json

class LevelManager:
    def __init__(self, schema_db: str):
        self.resolver = PathResolver.from_file(schema_db)

    def save_level(self, level_name: str, data: dict) -> Path:
        """Save level data."""

        level_path = self.resolver(
            'game_level_data',
            root='/game/levels',
            world='main',
            level=level_name
        )

        # Ensure directory exists
        level_path.mkdir(parents=True)

        # Save data
        data_file = level_path.get_path()
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)

        return data_file

    def load_level(self, level_name: str) -> dict:
        """Load level data."""

        level_path = self.resolver.get_path(
            'game_level_data',
            root='/game/levels',
            world='main',
            level=level_name
        )

        with open(level_path) as f:
            return json.load(f)

    def list_levels(self, world: str = 'main') -> list[str]:
        """List all levels in a world."""

        world_dir = self.resolver.get_path(
            'game_world_dir',
            root='/game/levels',
            world=world
        )

        levels = []
        if world_dir.exists():
            for level_file in world_dir.glob('*.json'):
                fields = self.resolver.parse('game_level_data', level_file)
                levels.append(fields['level'])

        return sorted(levels)

    def close(self):
        self.resolver.close()

# Usage
manager = LevelManager('game_schema.db')

# Save level
level_data = {
    'name': 'forest_01',
    'spawn_points': [...],
    'entities': [...]
}
manager.save_level('forest_01', level_data)

# List all levels
levels = manager.list_levels('main')
print(f"Available levels: {levels}")

manager.close()
```

---

## Platform-Specific Usage

### Example 9: Cross-Platform Project

```python
import sys
from pathlib import Path
from path_manager.compiler import compile_schema
from path_manager.resolver import PathResolver

class ProjectManager:
    def __init__(self, project_name: str):
        self.project_name = project_name

        # Auto-detect platform and use appropriate schema
        if sys.platform == 'win32':
            schema = 'schema_windows.yml'
            self.root = f'D:/projects/{project_name}'
        else:
            schema = 'schema_linux.yml'
            self.root = f'/mnt/projects/{project_name}'

        # Compile schema if needed
        db_path = Path('schema.db')
        if not db_path.exists():
            compile_schema(schema, db_path, format='sqlite')

        self.resolver = PathResolver.from_file(db_path)

    def get_asset_path(self, asset_name: str) -> Path:
        """Get platform-appropriate asset path."""
        return self.resolver.get_path(
            'asset_root',
            root=self.root,
            proj=self.project_name,
            asset=asset_name
        )

    def close(self):
        self.resolver.close()

# Works on both Windows and Linux
manager = ProjectManager('my_game')
asset_path = manager.get_asset_path('hero')
print(f"Asset path: {asset_path}")
# Windows: D:/projects/my_game/asset/hero
# Linux: /mnt/projects/my_game/asset/hero
manager.close()
```

### Example 10: Network Path Handling

```python
from path_manager.resolver import PathResolver
import platform

class NetworkPathManager:
    def __init__(self, schema_db: str):
        self.resolver = PathResolver.from_file(schema_db)
        self.is_windows = platform.system() == 'Windows'

    def get_network_path(self, kind: str, **fields) -> str:
        """Get network path in platform-specific format."""

        path = self.resolver.get_path(kind, **fields)
        path_str = path.as_posix()

        if self.is_windows:
            # Convert /mnt/share to \\server\share
            if path_str.startswith('/mnt/'):
                share_path = path_str[5:]  # Remove /mnt/
                return f'\\\\server\\{share_path}'.replace('/', '\\')

        return path_str

    def close(self):
        self.resolver.close()

# Usage
manager = NetworkPathManager('schema.db')

network_path = manager.get_network_path(
    'shared_asset',
    root='/mnt/shared',
    proj='demo',
    asset='tree'
)

print(network_path)
# Windows: \\server\shared\demo\asset\tree
# Linux: /mnt/shared/demo/asset/tree

manager.close()
```

---

## Advanced Patterns

### Example 11: Path Validation Decorator

```python
from functools import wraps
from path_manager.resolver import PathResolver
from path_manager.exceptions import ValidationError

def validate_asset_path(kind: str):
    """Decorator to validate asset paths."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, path, *args, **kwargs):
            # Validate path matches expected kind
            try:
                fields = self.resolver.parse(kind, path)
            except ValidationError as e:
                raise ValueError(f"Invalid path for {kind}: {e}")

            # Call original function with parsed fields
            return func(self, path, fields, *args, **kwargs)
        return wrapper
    return decorator

class AssetProcessor:
    def __init__(self, schema_db: str):
        self.resolver = PathResolver.from_file(schema_db)

    @validate_asset_path('asset_render_image_versioned')
    def process_render(self, path, fields):
        """Process rendered image."""
        print(f"Processing {fields['asset']} version {fields['ver']}")
        # ... process image ...

    @validate_asset_path('asset_model_maya')
    def process_model(self, path, fields):
        """Process Maya model."""
        print(f"Processing model {fields['asset']} version {fields['ver']}")
        # ... process model ...

    def close(self):
        self.resolver.close()

# Usage
processor = AssetProcessor('schema.db')

# Valid path
processor.process_render('/proj/demo/asset/tree/render/jpg/tree.v003.jpg')

# Invalid path raises ValueError
try:
    processor.process_render('/invalid/path.jpg')
except ValueError as e:
    print(f"Error: {e}")

processor.close()
```

### Example 12: Dynamic Schema Selection

```python
from path_manager.resolver import PathResolver
from typing import Dict, Any

class MultiProjectResolver:
    def __init__(self, project_schemas: Dict[str, str]):
        """
        project_schemas: {project_name: schema_db_path}
        """
        self.resolvers = {
            proj: PathResolver.from_file(schema)
            for proj, schema in project_schemas.items()
        }

    def get_path(self, project: str, kind: str, **fields) -> Any:
        """Get path for specific project."""
        if project not in self.resolvers:
            raise ValueError(f"Unknown project: {project}")

        return self.resolvers[project].get_path(kind, **fields)

    def parse(self, project: str, kind: str, path: str) -> Dict[str, str]:
        """Parse path for specific project."""
        if project not in self.resolvers:
            raise ValueError(f"Unknown project: {project}")

        return self.resolvers[project].parse(kind, path)

    def close_all(self):
        """Close all resolvers."""
        for resolver in self.resolvers.values():
            resolver.close()

# Usage
multi_resolver = MultiProjectResolver({
    'film_project': 'film_schema.db',
    'game_project': 'game_schema.db',
    'commercial': 'commercial_schema.db'
})

# Different projects, different schemas
film_path = multi_resolver.get_path(
    'film_project',
    'shot_render',
    root='/film',
    seq='S01',
    shot='0010'
)

game_path = multi_resolver.get_path(
    'game_project',
    'level_data',
    root='/game',
    level='forest_01'
)

multi_resolver.close_all()
```

---

## Error Handling

### Example 13: Robust Path Operations

```python
from path_manager.resolver import PathResolver
from path_manager.exceptions import (
    ValidationError,
    AmbiguousPathError,
    PathManagerError
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SafePathResolver:
    def __init__(self, schema_db: str):
        self.resolver = PathResolver.from_file(schema_db)

    def safe_get_path(self, kind: str, **fields) -> tuple[bool, Any]:
        """Safely get path with error handling."""
        try:
            path = self.resolver.get_path(kind, **fields)
            return True, path
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return False, str(e)
        except ValueError as e:
            logger.error(f"Unknown kind '{kind}': {e}")
            return False, str(e)
        except PathManagerError as e:
            logger.error(f"Path manager error: {e}")
            return False, str(e)

    def safe_parse(self, kind: str, path: str) -> tuple[bool, Any]:
        """Safely parse path with error handling."""
        try:
            fields = self.resolver.parse(kind, path)
            return True, fields
        except ValidationError as e:
            logger.warning(f"Path doesn't match kind '{kind}': {e}")

            # Try to guess the correct kind
            try:
                actual_kind, fields = self.resolver.guess_one(path)
                logger.info(f"Path matches kind '{actual_kind}' instead")
                return True, {'kind': actual_kind, 'fields': fields}
            except:
                return False, str(e)
        except PathManagerError as e:
            logger.error(f"Parse error: {e}")
            return False, str(e)

    def close(self):
        self.resolver.close()

# Usage
safe_resolver = SafePathResolver('schema.db')

# Safe path generation
success, result = safe_resolver.safe_get_path(
    'asset_render',
    root='/proj',
    proj='demo',
    asset='tree'
)

if success:
    print(f"Path: {result}")
else:
    print(f"Failed: {result}")

# Safe path parsing
success, result = safe_resolver.safe_parse(
    'wrong_kind',
    '/proj/demo/asset/tree.jpg'
)

if success and 'kind' in result:
    print(f"Correct kind: {result['kind']}")
    print(f"Fields: {result['fields']}")

safe_resolver.close()
```

---

## Integration Examples

### Example 14: Flask API Integration

```python
from flask import Flask, jsonify, request
from path_manager.resolver import PathResolver
from path_manager.exceptions import ValidationError

app = Flask(__name__)
resolver = PathResolver.from_file('schema.db')

@app.route('/api/path/generate', methods=['POST'])
def generate_path():
    """Generate path from kind and fields."""
    try:
        data = request.json
        kind = data.get('kind')
        fields = data.get('fields', {})

        path = resolver.get_path(kind, **fields)

        return jsonify({
            'success': True,
            'path': path.as_posix()
        })

    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/path/parse', methods=['POST'])
def parse_path():
    """Parse path to extract fields."""
    try:
        data = request.json
        kind = data.get('kind')
        path = data.get('path')

        fields = resolver.parse(kind, path)

        return jsonify({
            'success': True,
            'fields': fields
        })

    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/path/guess', methods=['POST'])
def guess_kind():
    """Guess kind from path."""
    try:
        data = request.json
        path = data.get('path')

        kind, fields = resolver.guess_one(path)

        return jsonify({
            'success': True,
            'kind': kind,
            'fields': fields
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404

if __name__ == '__main__':
    app.run(debug=True)
```

### Example 15: CLI Tool Integration

```python
#!/usr/bin/env python3
"""
Command-line tool for path management.
"""

import argparse
import json
import sys
from path_manager.resolver import PathResolver
from path_manager.exceptions import ValidationError

def main():
    parser = argparse.ArgumentParser(description='Path Manager CLI')
    parser.add_argument('--schema', required=True, help='Schema database path')

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate path')
    gen_parser.add_argument('--kind', required=True, help='Kind name')
    gen_parser.add_argument('--fields', required=True, help='Fields as JSON')

    # Parse command
    parse_parser = subparsers.add_parser('parse', help='Parse path')
    parse_parser.add_argument('--kind', required=True, help='Kind name')
    parse_parser.add_argument('--path', required=True, help='Path to parse')

    # Guess command
    guess_parser = subparsers.add_parser('guess', help='Guess kind from path')
    guess_parser.add_argument('--path', required=True, help='Path to analyze')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Load resolver
    resolver = PathResolver.from_file(args.schema)

    try:
        if args.command == 'generate':
            fields = json.loads(args.fields)
            path = resolver.get_path(args.kind, **fields)
            print(path.as_posix())

        elif args.command == 'parse':
            fields = resolver.parse(args.kind, args.path)
            print(json.dumps(fields, indent=2))

        elif args.command == 'guess':
            kind, fields = resolver.guess_one(args.path)
            result = {'kind': kind, 'fields': fields}
            print(json.dumps(result, indent=2))

    except ValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(2)

    finally:
        resolver.close()

if __name__ == '__main__':
    main()
```

**Usage:**
```bash
# Generate path
python path_cli.py --schema schema.db generate \
    --kind asset_render \
    --fields '{"root":"/proj","proj":"demo","asset":"tree","ext":"jpg"}'

# Parse path
python path_cli.py --schema schema.db parse \
    --kind asset_render \
    --path "/proj/demo/asset/tree/render/jpg/tree.jpg"

# Guess kind
python path_cli.py --schema schema.db guess \
    --path "/proj/demo/asset/tree/render/jpg/tree.jpg"
```
