# Schema Writing Guide

Complete guide for writing Path Manager schemas.

## Table of Contents

- [Schema Basics](#schema-basics)
- [Fields](#fields)
- [Directories](#directories)
- [Filenames](#filenames)
- [Kinds](#kinds)
- [Best Practices](#best-practices)
- [Common Patterns](#common-patterns)
- [Validation](#validation)

---

## Schema Basics

### Schema Structure

A Path Manager schema is a YAML file with four main sections:

```yaml
fields:      # Define reusable fields with regex validation
  # ...

directories: # Define directory tree structure
  # ...

filenames:   # Define filename templates
  # ...

kinds:       # Combine directories + filenames into path types
  # ...
```

### Minimal Schema

```yaml
fields:
  root:
    regex: "/[A-Za-z0-9/_-]+"
    example: "/proj"

  proj:
    regex: "[A-Za-z0-9_]+"
    example: "demo"

directories:
  name: root
  segment: "$root"
  children:
    - name: proj_root
      segment: "$proj"

filenames: {}

kinds:
  proj_root:
    directory: proj_root
    filename: null
```

---

## Fields

Fields are reusable variables with regex validation.

### Field Definition

```yaml
fields:
  field_name:
    regex: "regular_expression"
    example: "example_value"
```

**Required:**
- `regex`: Validation pattern (Python regex)
- `example`: Example value matching regex

### Field Types

#### 1. Simple Alphanumeric

```yaml
proj:
  regex: "[A-Za-z0-9_]+"
  example: "demo_proj"

asset:
  regex: "[A-Za-z0-9_-]+"
  example: "hero_asset"
```

#### 2. Numeric with Padding

```yaml
ver:
  regex: "[0-9]{3}"
  example: "003"

shot:
  regex: "[0-9]{4}"
  example: "0010"

frame:
  regex: "[0-9]{4}"
  example: "0001"
```

#### 3. Enumerations

```yaml
dept:
  regex: "modeling|rigging|animation|lighting"
  example: "modeling"

status:
  regex: "wip|review|approved|published"
  example: "wip"
```

#### 4. Hierarchical Codes

```yaml
seq:
  regex: "[A-Z]{2,3}[0-9]{2,3}"
  example: "SQ010"

shot:
  regex: "SH[0-9]{4}"
  example: "SH0010"
```

#### 5. Absolute Paths

```yaml
# Linux/Unix
root:
  regex: "/[A-Za-z0-9/_-]+"
  example: "/mnt/projects"

# Windows
root:
  regex: "[A-Za-z]:/[A-Za-z0-9/_-]+"
  example: "D:/projects"

# Cross-platform
root:
  regex: "([A-Za-z]:)?/[A-Za-z0-9/_-]+"
  example: "/proj"
```

#### 6. File Extensions

```yaml
ext:
  regex: "[a-z0-9]+"
  example: "jpg"

# Multiple extensions
ext:
  regex: "jpg|png|exr|tif"
  example: "exr"
```

#### 7. Dates and Timestamps

```yaml
date:
  regex: "[0-9]{8}"
  example: "20240115"

timestamp:
  regex: "[0-9]{8}_[0-9]{6}"
  example: "20240115_143022"

year:
  regex: "[0-9]{4}"
  example: "2024"
```

### Field Naming Conventions

- Use lowercase names
- Use underscores for multi-word names
- Be consistent across schema
- Avoid abbreviations unless standard

**Good:**
```yaml
asset_name:
  regex: "[A-Za-z0-9_]+"

version_number:
  regex: "[0-9]{3}"
```

**Bad:**
```yaml
AssetName:  # uppercase
  regex: "[A-Za-z0-9_]+"

ver_num:    # inconsistent abbreviation
  regex: "[0-9]{3}"
```

---

## Directories

Directories define the tree structure of your paths.

### Directory Structure

```yaml
directories:
  name: root_name        # Unique directory name
  segment: "$root"       # Path segment (literal or field)
  children:              # Optional child directories
    - name: child_name
      segment: "literal_or_$field"
      children: [...]
```

### Simple Linear Path

```yaml
directories:
  name: root
  segment: "$root"
  children:
    - name: proj_root
      segment: "$proj"
      children:
        - name: assets
          segment: "assets"
          children:
            - name: asset_root
              segment: "$asset"
```

**Generates:** `$root/$proj/assets/$asset`

### Branching Structure

```yaml
directories:
  name: root
  segment: "$root"
  children:
    - name: proj_root
      segment: "$proj"
      children:
        - name: assets
          segment: "assets"
          children:
            - name: asset_root
              segment: "$asset"

        - name: shots
          segment: "shots"
          children:
            - name: seq_root
              segment: "$seq"
              children:
                - name: shot_root
                  segment: "$shot"

        - name: library
          segment: "library"
```

**Generates multiple paths:**
- `$root/$proj/assets/$asset`
- `$root/$proj/shots/$seq/$shot`
- `$root/$proj/library`

### Deep Nesting

```yaml
directories:
  name: root
  segment: "$root"
  children:
    - name: proj_root
      segment: "$proj"
      children:
        - name: assets_root
          segment: "assets"
          children:
            - name: asset_root
              segment: "$asset"
              children:
                - name: asset_dept
                  segment: "$dept"
                  children:
                    - name: asset_work
                      segment: "work"

                    - name: asset_publish
                      segment: "publish"
                      children:
                        - name: asset_publish_ver
                          segment: "v$ver"
```

**Generates:**
- `$root/$proj/assets/$asset/$dept/work`
- `$root/$proj/assets/$asset/$dept/publish/v$ver`

### Directory Naming

- Use descriptive names
- Include field names for field-based directories
- Use hierarchy indicators (root, parent, child)

**Examples:**
```yaml
proj_root          # Project root directory
asset_root         # Asset root directory
asset_dept         # Department under asset
shot_render_exr    # EXR render directory under shot
```

---

## Filenames

Filename templates define file naming patterns.

### Filename Structure

```yaml
filenames:
  template_name:
    template: "pattern_with_$fields"
```

### Simple Filenames

```yaml
filenames:
  asset_file:
    template: "$asset.$ext"
    # Generates: tree.jpg

  versioned_file:
    template: "$asset.v$ver.$ext"
    # Generates: tree.v003.jpg
```

### Complex Filenames

```yaml
filenames:
  shot_render:
    template: "$shot.$task.v$ver.$frame.$ext"
    # Generates: 0010.comp.v003.0001.exr

  dated_backup:
    template: "$asset_$date.$ext"
    # Generates: tree_20240115.ma

  layered_output:
    template: "$asset.$layer.v$ver.$frame.$ext"
    # Generates: tree.beauty.v003.0001.exr
```

### Repeated Fields

Fields can appear multiple times:

```yaml
filenames:
  cache_file:
    template: "$asset/$asset_cache_v$ver.abc"
    # Generates: tree/tree_cache_v003.abc
```

**Note:** Repeated fields must have identical values.

### Literal Characters

Use any literal characters:

```yaml
filenames:
  maya_scene:
    template: "$asset_v$ver.ma"
    # Generates: tree_v003.ma

  nuke_script:
    template: "$shot_$task_v$ver.nk"
    # Generates: 0010_comp_v003.nk

  metadata:
    template: ".$asset.metadata.json"
    # Generates: .tree.metadata.json
```

---

## Kinds

Kinds combine directories and filenames to create complete path patterns.

### Kind Structure

```yaml
kinds:
  kind_name:
    directory: directory_name    # Required if filename provided
    filename: filename_template  # Optional (null for dirs)
```

### File Kinds

```yaml
kinds:
  asset_render_image:
    directory: asset_render_jpg
    filename: asset_file
    # Generates: $root/$proj/assets/$asset/render/jpg/$asset.jpg

  asset_render_versioned:
    directory: asset_render_jpg
    filename: versioned_file
    # Generates: $root/$proj/assets/$asset/render/jpg/$asset.v$ver.jpg
```

### Directory Kinds

```yaml
kinds:
  proj_root:
    directory: proj_root
    filename: null
    # Generates: $root/$proj

  asset_root:
    directory: asset_root
    filename: null
    # Generates: $root/$proj/assets/$asset
```

### Multiple Kinds, Same Directory

```yaml
kinds:
  # Low-res render
  asset_render_jpg:
    directory: asset_render_jpg
    filename: asset_file

  # High-res render
  asset_render_exr:
    directory: asset_render_exr
    filename: asset_file

  # Versioned render
  asset_render_versioned:
    directory: asset_render_jpg
    filename: versioned_file
```

### Kind Naming Conventions

Use descriptive, hierarchical names:

```yaml
# Good - describes what and where
asset_render_image
asset_model_maya
shot_render_exr
shot_comp_nuke

# Bad - too vague
asset_file
render
output
```

---

## Best Practices

### 1. Start with Fields

Define all fields before directories:

```yaml
# Good - fields first
fields:
  root:
    regex: "/[A-Za-z0-9/_-]+"
    example: "/proj"
  proj:
    regex: "[A-Za-z0-9_]+"
    example: "demo"

directories:
  name: root
  segment: "$root"
  # ...

# Bad - mixed order causes confusion
directories:
  name: root
  segment: "$root"

fields:
  root:
    regex: "/[A-Za-z0-9/_-]+"
```

### 2. Use Consistent Naming

```yaml
# Good - consistent patterns
fields:
  asset_name:
  asset_type:
  asset_category:

# Bad - inconsistent
fields:
  assetName:
  type:
  asset_cat:
```

### 3. Validate Early

Test field regexes before using:

```python
import re

regex = r"[A-Z]{2}[0-9]{3}"
test_values = ["SQ010", "sq010", "SQ10", "ABC123"]

for val in test_values:
    match = re.fullmatch(regex, val)
    print(f"{val}: {'✓' if match else '✗'}")
```

### 4. Document Examples

Always provide realistic examples:

```yaml
# Good - realistic example
shot:
  regex: "[0-9]{4}"
  example: "0010"

# Bad - lazy example
shot:
  regex: "[0-9]{4}"
  example: "0000"
```

### 5. Avoid Over-Nesting

```yaml
# Good - reasonable depth (4 levels)
$root/$proj/assets/$asset/publish/v$ver

# Bad - too deep (7+ levels)
$root/$show/$proj/$type/assets/$category/$asset/$dept/publish/v$ver
```

### 6. Plan for Growth

Leave room for future additions:

```yaml
directories:
  name: assets_root
  segment: "assets"
  children:
    - name: asset_chars
      segment: "chars"

    - name: asset_props
      segment: "props"

    - name: asset_envs
      segment: "envs"

    # Easy to add more asset types later
```

### 7. Use Platform-Specific Schemas

```yaml
# schema_linux.yml
fields:
  root:
    regex: "/[A-Za-z0-9/_-]+"
    example: "/mnt/projects"

# schema_windows.yml
fields:
  root:
    regex: "[A-Za-z]:/[A-Za-z0-9/_-]+"
    example: "D:/projects"
```

---

## Common Patterns

### VFX Pipeline

```yaml
fields:
  root:
    regex: "/[A-Za-z0-9/_-]+"
    example: "/mnt/projects"
  proj:
    regex: "[A-Za-z0-9_]+"
    example: "feature_film"
  seq:
    regex: "[A-Z]{2}[0-9]{3}"
    example: "SQ010"
  shot:
    regex: "[0-9]{4}"
    example: "0010"
  task:
    regex: "layout|anim|light|comp"
    example: "comp"
  ver:
    regex: "[0-9]{3}"
    example: "003"
  frame:
    regex: "[0-9]{4}"
    example: "0001"
  ext:
    regex: "exr|jpg|mov"
    example: "exr"

directories:
  name: root
  segment: "$root"
  children:
    - name: proj_root
      segment: "$proj"
      children:
        - name: shots
          segment: "shots"
          children:
            - name: seq_root
              segment: "$seq"
              children:
                - name: shot_root
                  segment: "$shot"
                  children:
                    - name: shot_task
                      segment: "$task"
                      children:
                        - name: shot_work
                          segment: "work"

                        - name: shot_publish
                          segment: "publish"

                        - name: shot_render
                          segment: "render"

filenames:
  shot_scene:
    template: "$shot_$task_v$ver.nk"

  shot_render:
    template: "$shot.$task.v$ver.$frame.$ext"

kinds:
  shot_work_scene:
    directory: shot_work
    filename: shot_scene

  shot_render_exr:
    directory: shot_render
    filename: shot_render
```

### Game Development

```yaml
fields:
  root:
    regex: "/[A-Za-z0-9/_-]+"
    example: "/game"
  world:
    regex: "[A-Za-z0-9_]+"
    example: "overworld"
  level:
    regex: "[A-Za-z0-9_]+"
    example: "forest_01"
  asset:
    regex: "[A-Za-z0-9_]+"
    example: "hero"
  texture_type:
    regex: "diffuse|normal|roughness|metallic"
    example: "diffuse"
  ext:
    regex: "png|tga|dds"
    example: "png"

directories:
  name: root
  segment: "$root"
  children:
    - name: levels
      segment: "levels"
      children:
        - name: world_root
          segment: "$world"
          children:
            - name: level_root
              segment: "$level"

    - name: assets
      segment: "assets"
      children:
        - name: asset_root
          segment: "$asset"
          children:
            - name: asset_textures
              segment: "textures"

            - name: asset_models
              segment: "models"

filenames:
  level_data:
    template: "$level.json"

  texture_file:
    template: "$asset_$texture_type.$ext"

kinds:
  level_data:
    directory: level_root
    filename: level_data

  asset_texture:
    directory: asset_textures
    filename: texture_file
```

### Asset Library

```yaml
fields:
  root:
    regex: "/[A-Za-z0-9/_-]+"
    example: "/library"
  category:
    regex: "textures|models|materials|hdris"
    example: "textures"
  subcategory:
    regex: "[A-Za-z0-9_]+"
    example: "wood"
  asset:
    regex: "[A-Za-z0-9_]+"
    example: "oak_planks"
  resolution:
    regex: "1k|2k|4k|8k"
    example: "4k"
  ext:
    regex: "jpg|png|exr|hdr"
    example: "jpg"

directories:
  name: root
  segment: "$root"
  children:
    - name: category_root
      segment: "$category"
      children:
        - name: subcategory_root
          segment: "$subcategory"
          children:
            - name: asset_root
              segment: "$asset"
              children:
                - name: asset_resolution
                  segment: "$resolution"

filenames:
  texture_file:
    template: "$asset.$ext"

kinds:
  library_texture:
    directory: asset_resolution
    filename: texture_file
```

---

## Validation

### Testing Your Schema

```python
from path_manager.compiler import SchemaCompiler

# Compile and check for errors
try:
    compiler = SchemaCompiler('schema.yml')
    compiler.compile()
    print("✓ Schema valid")
except Exception as e:
    print(f"✗ Schema error: {e}")

# Check for ambiguities
if compiler.ambiguities:
    print("\n⚠ Ambiguities detected:")
    for pattern, kinds in compiler.ambiguities.items():
        print(f"  {pattern}")
        for kind in kinds:
            print(f"    - {kind}")
```

### Common Validation Errors

#### Missing Field Regex

```yaml
# Error: Missing regex
fields:
  proj:
    example: "demo"

# Fix: Add regex
fields:
  proj:
    regex: "[A-Za-z0-9_]+"
    example: "demo"
```

#### Invalid Regex

```yaml
# Error: Unbalanced brackets
fields:
  ver:
    regex: "[0-9{3}"
    example: "003"

# Fix: Balance brackets
fields:
  ver:
    regex: "[0-9]{3}"
    example: "003"
```

#### Undefined Field in Template

```yaml
# Error: 'proj' field not defined
directories:
  name: root
  segment: "$proj"

# Fix: Define field
fields:
  proj:
    regex: "[A-Za-z0-9_]+"
    example: "demo"

directories:
  name: root
  segment: "$proj"
```

#### Circular Directory References

```yaml
# Error: Circular reference
directories:
  name: a
  segment: "a"
  children:
    - name: b
      segment: "b"
      children:
        - name: a  # Circular!
          segment: "a"
```

---

## Schema Migration

When updating schemas:

1. **Test thoroughly** before deploying
2. **Document changes** in commit messages
3. **Version schemas** for rollback
4. **Provide migration tools** if breaking changes

### Migration Example

```python
# migrate_paths.py
from path_manager.resolver import PathResolver

old_resolver = PathResolver.from_file('schema_v1.db')
new_resolver = PathResolver.from_file('schema_v2.db')

# Migrate paths
for old_path in find_all_paths():
    try:
        # Parse with old schema
        kind, fields = old_resolver.guess_one(old_path)

        # Generate with new schema
        new_path = new_resolver.get_path(kind, **fields)

        # Rename file
        os.rename(old_path, new_path)
        print(f"Migrated: {old_path} → {new_path}")

    except Exception as e:
        print(f"Failed: {old_path}: {e}")

old_resolver.close()
new_resolver.close()
```
