# Schema Editor GUI

Professional PySide6-based visual editor for Path Manager schema files.

## Features

### 🎯 Design Philosophy

- **Performance First**: Handles 100+ kinds efficiently with QTableView Model/View architecture
- **Search & Filter**: Built-in search for all sections
- **Professional UX**: Keyboard shortcuts, auto-save prompts, validation
- **Offline Ready**: No network dependencies required

### 📝 Fields Editor

- Table-based editing with sortable columns
- Real-time search/filter
- Inline editing for regex and examples
- Validation for regex patterns

### 📁 Directory Structure Editor

- Tree-based visualization (QTreeView)
- Add/edit/remove nodes with dialogs
- Hierarchical display with expand/collapse
- Visual representation of directory relationships

### 📄 Filename Templates Editor

- Table-based editing
- Search and filter support
- Template syntax validation
- Quick add/remove

### 🎯 Kinds Editor (Optimized for 100+ entries)

- **High-performance table view** with virtual scrolling
- **Dropdown selection** for directories and filenames
- **Search/filter** - shows "X of Y kinds" when filtering
- **Sortable columns** - click headers to sort
- **Bulk operations** - select multiple kinds to delete

## Installation

### Install with GUI support:

```bash
# Install path-manager with GUI dependencies
pip install -e ".[gui]"

# Or install PySide6 separately
pip install PySide6
```

## Usage

### Launch Editor

```bash
# Method 1: Using installed script
path-schema-editor

# Method 2: Using Python module
python -m path_manager.schema_editor

# Method 3: From Python code
from path_manager.schema_editor import SchemaEditorWindow
from PySide6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
window = SchemaEditorWindow()
window.show()
sys.exit(app.exec())
```

### Workflow

#### 1. Create New Schema or Open Existing

**New Schema:**
- File → New (Ctrl+N)
- Start with empty schema

**Open Existing:**
- File → Open (Ctrl+O)
- Select `.yml` or `.yaml` file
- Schema loads into all tabs

**Load Example:**
- Schema → Load Example
- Loads built-in demo schema

#### 2. Edit Fields

- Switch to "Fields (欄位)" tab
- Click "+ Add Field" to create new field
- Edit regex and example inline
- Use search box to filter fields

**Example:**
```yaml
fields:
  proj:
    regex: "[A-Za-z0-9_]+"
    example: "demo_proj"
```

#### 3. Build Directory Structure

- Switch to "Directories (目錄)" tab
- Click "Set Root" to create root node
- Select parent node, click "+ Add Child"
- Use "✏ Edit" to modify nodes
- Use "- Remove" to delete (with children)

**Tips:**
- Use `$field_name` to reference fields
- Use literal strings for fixed paths
- Tree automatically expands to show structure

#### 4. Define Filename Templates

- Switch to "Filenames (檔名)" tab
- Click "+ Add Filename"
- Edit template using `$variable` syntax
- Use search to find templates quickly

#### 5. Create Kinds (For 100+ entries)

- Switch to "Kinds (種類)" tab
- Click "+ Add Kind"
- Click in Directory/Filename columns to select from dropdown
- Use search box to filter kinds (shows "X of Y kinds")
- Click column headers to sort

**Performance features:**
- Virtual scrolling handles 1000+ kinds smoothly
- Search updates count in real-time
- Dropdowns only show valid directories/filenames

#### 6. Validate Schema

- Schema → Validate (Ctrl+Shift+V)
- Checks for:
  - At least one field defined
  - Directory structure exists
  - Kinds have valid directory/filename references
- Shows errors or success message

#### 7. Save Schema

**Save:**
- File → Save (Ctrl+S)
- Saves to current file
- If new, prompts for filename

**Save As:**
- File → Save As (Ctrl+Shift+S)
- Choose new filename
- Sets as current file

**Auto-prompt:**
- Window close checks for unsaved changes
- Save / Discard / Cancel options

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| New | Ctrl+N |
| Open | Ctrl+O |
| Save | Ctrl+S |
| Save As | Ctrl+Shift+S |
| Validate | Ctrl+Shift+V |
| Quit | Ctrl+Q |

## Managing Large Schemas

### For 100+ Kinds:

1. **Use Search Effectively**
   - Type in search box as you work
   - Search is case-insensitive
   - Filters in real-time

2. **Sort by Column**
   - Click "Name" to sort alphabetically
   - Click "Directory" to group by directory
   - Click "Filename" to group by template

3. **Batch Operations**
   - Ctrl+Click to select multiple rows
   - Delete multiple kinds at once

4. **Validation**
   - Run validation before saving
   - Catches missing references early

### Performance Tips:

- Table uses virtual scrolling (no lag with 1000+ rows)
- Search is instant (Qt's proxy model)
- Dropdowns are cached (no rebuild on each edit)

## Example Session

```bash
# 1. Launch editor
path-schema-editor

# 2. Load example or open existing schema
Schema → Load Example

# 3. Customize fields
- Edit "proj" regex to match your naming convention
- Add "shot", "task", "version" fields

# 4. Build directory tree
- Set root to "$root"
- Add "$proj" → "shots" → "$shot" → "$task"

# 5. Add filename templates
- shot_work: "$shot_$task_v$ver.ma"
- shot_render: "$shot.$task.v$ver.####.exr"

# 6. Create kinds (even 100+)
- Add one by one or batch create
- Use dropdowns for selection
- Search to verify

# 7. Validate
Schema → Validate

# 8. Save
File → Save As → my_schema.yml
```

## Integrating with Path Manager

After editing schema:

```bash
# 1. Compile schema
python -m path_manager.compiler my_schema.yml my_schema.db

# 2. Use in production
from path_manager.resolver import PathResolver

resolver = PathResolver.from_file('my_schema.db')
path = resolver.get_path('shot_work',
                         root='/proj',
                         proj='feature_film',
                         shot='0010',
                         task='lighting',
                         ver='003')
```

## Troubleshooting

### Editor won't launch

**Error: "PySide6 is required"**
```bash
pip install PySide6
```

### Schema won't load

**Invalid YAML:**
- Check YAML syntax
- Ensure proper indentation
- No tabs (use spaces)

**Missing keys:**
- Schema must have: fields, directories, filenames, kinds
- Use Schema → Load Example as template

### Kinds dropdown empty

**Cause:** No directories or filenames defined yet

**Fix:**
1. Define directories first (tab 2)
2. Define filenames (tab 3)
3. Kinds dropdowns will populate automatically

### Large schema is slow

**Should not happen** - table uses virtual scrolling

If experiencing slowness:
- Update PySide6: `pip install --upgrade PySide6`
- Check Python version >= 3.10
- Report issue with schema size details

## Architecture

### Model/View Pattern

```
┌─────────────────┐
│  MainWindow     │
│  - Tab Widget   │
└────────┬────────┘
         │
    ┌────┴────┬────────┬──────────┐
    │         │        │          │
┌───▼──┐  ┌──▼──┐  ┌──▼───┐  ┌───▼───┐
│Fields│  │Dirs │  │Files │  │Kinds  │
│Editor│  │Editor  │Editor│  │Editor │
└───┬──┘  └──┬──┘  └──┬───┘  └───┬───┘
    │        │        │          │
┌───▼──┐  ┌──▼──┐  ┌──▼───┐  ┌───▼───┐
│Table │  │Tree │  │Table │  │Table  │
│Model │  │Model│  │Model │  │+Proxy │ <- Search/Filter
└──────┘  └─────┘  └──────┘  └───────┘
```

### Key Components

- **MainWindow**: Tab container, menu, toolbar, file I/O
- **FieldsEditor**: QTableView with search
- **DirectoriesEditor**: QTreeView with dialogs
- **FilenamesEditor**: QTableView with search
- **KindsEditor**: QTableView with dropdowns and search
- **Proxy Models**: Enable search/filter without affecting data

## Comparison: HTML vs PySide6

| Feature | HTML Version | PySide6 Version |
|---------|-------------|-----------------|
| Cross-platform | ✅ Browser | ✅ Qt |
| Handles 100+ kinds | ❌ Slow | ✅ Fast |
| Search/Filter | ⚠️ Manual | ✅ Built-in |
| Keyboard shortcuts | ❌ Limited | ✅ Full |
| File operations | ⚠️ Manual | ✅ Native |
| Performance | ⚠️ DOM-based | ✅ Virtual scroll |
| Dependencies | ✅ None | PySide6 |
| Offline use | ✅ Yes | ✅ Yes |
| **Recommended for** | Quick edits | Production use |

## FAQ

**Q: Do I need internet to use the editor?**
A: No, all dependencies are local. Works in fully offline environments.

**Q: Can I edit multiple schemas at once?**
A: Not in the same window. Launch multiple instances for parallel editing.

**Q: How do I backup my schema?**
A: File → Save As with a new name, or use git for version control.

**Q: Can I undo changes?**
A: Currently no undo/redo. Save frequently and use git for version control.

**Q: What if I have 500+ kinds?**
A: No problem! Table uses virtual scrolling. Use search and sort features.

**Q: Can I import from old HTML editor?**
A: Yes, both use standard YAML format. File → Open works with any valid schema.

## Future Enhancements

Potential features (not yet implemented):

- Undo/Redo support
- Drag-and-drop directory tree reordering
- Syntax highlighting for regex
- Live path preview (show generated paths)
- Import from compiled .db files
- Export to different platforms (Windows/Linux specific)
- Dark theme
- Bulk kind creation from CSV

## Related Documentation

- [Main README](../README.MD) - Path Manager overview
- [Schema Guide](SCHEMA_GUIDE.md) - How to write schemas
- [API Reference](API_REFERENCE.md) - Programming interface
- [Examples](EXAMPLES.md) - Usage examples

## Support

- **Issues**: Report bugs via project issue tracker
- **Questions**: Check Schema Guide first
- **Feature Requests**: Open issue with [GUI] prefix
