# Path / Structure 設計方案（定案版）

目標：

- 不在程式中 hardcode 任何實體路徑  
- 用一份 schema 定義「欄位 / 資料夾 / 檔名 / 完整路徑」  
- 透過 PathResolver 依 `kind` + fields 動態產生 path  
- schema 更新時，只要更新 schema / compiled config，所有程式自動跟著走  

---

## 1. 核心概念

系統只用 4 種元素：

1. **Field**  
   - 最小元素（`root`, `proj`, `seq`, `shot`, `asset`, `ver`, `ext` …）  
   - 每個 Field 有自己的 regex，用來驗證值是否合法

2. **Directory**  
   - 資料夾樹的每一個節點  
   - 用樹狀描述  
   - 每一層 only 管「自己這一段」字串（segment），往上展開後得到完整路徑 template

3. **Filename**  
   - 單純檔名 template（不含任何資料夾）  
   - 使用 Python `string.Template` 語法：`$name` / `${name}`

4. **Kind**  
   - 完整路徑的「代號」  
   - 把某個 Directory + 某個 Filename 組合起來  
   - 純資料夾路徑可以直接用 Directory 名稱當 kind，不用再定義一次

---

## 2. PathResolver API 介面

```python
resolver(kind, **fields).get_path()
# 或
resolver.get_path(kind, **fields)
```

其中 `kind` 可以是：

- schema 裡定義的 `kinds.<name>`（dir + filename 組合）
- 或 `directories` 裡的某個 `name`（純資料夾）

---

## 3. `schema.yml` 格式總覽

`schema.yml` 採用四大區塊：

```yaml
fields:       # 欄位定義（regex 驗證）
directories:  # 資料夾樹（nested）
filenames:    # 檔名模板（string.Template）
kinds:        # 完整路徑 alias（dir + filename）
```

---

## 4. Fields：欄位 + regex

```yaml
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

  seq:
    regex: "[A-Z0-9]{3}"
    example: "S01"

  shot:
    regex: "[0-9]{4}"
    example: "0010"

  ver:
    regex: "[0-9]{3}"     # v003 這種用 3 位數字
    example: "003"

  ext:
    regex: "[a-z0-9]+"
    example: "jpg"
```

說明：

- **唯一用途**：`regex` = 如何驗證欄位值  
- `example` 只用來示範或產 demo，不參與邏輯  

---

## 5. Directories：樹狀結構 + segment template

使用 nested 結構，每一層有：

- `name`：這一層的 ID  
- `segment`：這一層的資料夾名稱，只負責「自己這一段」  
  - 可使用 fields：`$root`, `$proj`, `$asset`…  
  - 使用 Python `string.Template` 語法  
- `children`：子節點列表  

```yaml
directories:
  name: root
  segment: "$root"
  children:
    - name: proj_root
      segment: "$proj"
      children:
        - name: proj_ref
          segment: "ref"
          children:
            - name: proj_ref_2d
              segment: "2d"
            - name: proj_ref_3d
              segment: "3d"

        - name: proj_client
          segment: "client"

        - name: proj_work
          segment: "work"

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
```

展開後，每個 `name` 都對應到一個完整 template，例如：

- `proj_root` → `"$root/$proj"`  
- `proj_ref_2d` → `"$root/$proj/ref/2d"`  
- `asset_render_jpg` → `"$root/$proj/asset/$asset/render/jpg"`  

任何一層的 folder（例如 `proj_ref` / `asset_root`）都可以獨立被拿來當 kind 使用。

---

## 6. Filenames：單純 `string.Template`

只負責檔名這一段，全部用 `$field` 語法，不使用 `{ver:03d}` 這類格式字串。

```yaml
filenames:
  asset_render:
    template: "$asset.$ext"

  asset_render_versioned:
    template: "$asset.v$ver.$ext"
```

說明：

- padding 由欄位本身控制（例如 `ver` regex 就要求三位數）  
- 需要「這個 filename 用到哪些欄位」，可用簡單 regex 從 template 抓 `$xxx`  

---

## 7. Kinds：完整路徑 alias

`kinds` 只定義「需要 dir + filename 組合」的路徑。  
純資料夾不必重複出現在 kinds 內，直接用 directory `name` 就能拿到 path。

```yaml
kinds:
  asset_render_image:
    directory: asset_render_jpg
    filename: asset_render

  asset_render_image_versioned:
    directory: asset_render_jpg
    filename: asset_render_versioned
```

呼叫時：

- `kind="asset_render_image_versioned"` → dir = `asset_render_jpg` + filename = `asset_render_versioned`  
- `kind="asset_render_jpg"`（沒有出現在 kinds） → 直接當作 Directory 名稱，算出 `"$root/$proj/asset/$asset/render/jpg"` 的路徑  

---

## 8. PathResolver：概念與 lazy 設計

### 8.1 使用方式

```python
resolver = PathResolver(runtime_store)

path = resolver(
    "asset_render_image_versioned",
    root="/proj",
    proj="demo_proj",
    asset="tree",
    ver="003",
    ext="jpg",
).get_path()

# 或
path = resolver.get_path(
    "asset_render_image_versioned",
    root="/proj",
    proj="demo_proj",
    asset="tree",
    ver="003",
    ext="jpg",
)
```

### 8.2 編譯階段 vs runtime

**編譯階段（開發時）**：

1. 人編輯 `schema.yml`  
2. 跑 `compile_schema.py`，做：
   - 展開 directories 樹 → 每個 dir 得到：
     - `name`
     - `template`（完整路徑模板，如 `"$root/$proj/ref/2d"`）
     - `fields`（此 template 需要哪些欄位）
   - 每個 filename 得到：
     - `name`
     - `template`
     - `fields`
   - 每個 kind 得到：
     - `name`
     - `template`（dir + filename 或只有 dir）
     - `fields`
3. 把這些結果存到「索引化存儲」：
   - 例如 SQLite / key‑value DB，或多個 JSON / MsgPack / Parquet 檔案  

**runtime**：

- PathResolver 只握有這個 compiled store 的介面（例如 `store.get_kind(name)`）  
- 啟動時不載入全部 schema  
- 第一次遇到某個 kind / directory / filename 時，才從 store 讀該筆資料並 cache（真正 lazy）

---

### 8.3 PathResolver 主要流程（forward resolve）

概念流程：

1. 依 kind 拿到 `KindSpec`：
   - 先問 store：`get_kind(kind)`  
   - 若沒有，當作 directory：`get_dir(kind)`  
   - 得到：
     - `template`: 例如 `"$root/$proj/asset/$asset/render/jpg/$asset.v$ver.$ext"`
     - `fields`: `{"root", "proj", "asset", "ver", "ext"}`

2. 檢查呼叫時提供的 fields：
   - 是否包含所有 `fields`  
   - 每個欄位值是否通過對應 `fields.regex`

3. 用 `string.Template` 展開：
   - `Template(template).substitute(ctx)` → 得到完整字串路徑

4. 回傳 `Path(完整字串)`


（以下是簡化版 Python 介面）

```python
from pathlib import Path
from string import Template
import re

class KindSpec:
    def __init__(self, name: str, template: str, fields: set[str]):
        self.name = name
        self.template = template
        self.fields = fields
        self._tmpl_obj: Template | None = None

    @property
    def tmpl(self) -> Template:
        if self._tmpl_obj is None:
            self._tmpl_obj = Template(self.template)
        return self._tmpl_obj


class ResolvedPath:
    def __init__(self, spec: KindSpec, ctx: dict[str, str]):
        self._spec = spec
        self._ctx = ctx

    def get_path(self) -> Path:
        s = self._spec.tmpl.substitute(self._ctx)
        return Path(s)


class PathResolver:
    def __init__(self, store):
        """
        store 介面預期：
          - get_kind(name) -> {"template": str, "fields": [str]} or None
          - get_dir(name) -> {"template": str, "fields": [str]} or None
          - get_field_regex(name) -> str or None
        """
        self.store = store
        self._kind_cache: dict[str, KindSpec] = {}

    def __call__(self, kind: str, **fields) -> ResolvedPath:
        spec = self._get_kind_spec(kind)
        ctx = self._build_context(spec, fields)
        return ResolvedPath(spec, ctx)

    def get_path(self, kind: str, **fields) -> Path:
        return self(kind, **fields).get_path()

    def _get_kind_spec(self, kind: str) -> KindSpec:
        if kind in self._kind_cache:
            return self._kind_cache[kind]

        rec = self.store.get_kind(kind)
        if not rec:
            # 不在 kinds，就當作 directory
            rec = self.store.get_dir(kind)
            if not rec:
                raise KeyError(f"Unknown kind: {kind}")

        template = rec["template"]
        fields = set(rec["fields"])

        spec = KindSpec(kind, template, fields)
        self._kind_cache[kind] = spec
        return spec

    def _build_context(self, spec: KindSpec, ctx: dict) -> dict:
        missing = spec.fields - ctx.keys()
        if missing:
            raise ValueError(f"Missing fields for kind {spec.name}: {missing}")

        for name in spec.fields:
            value = str(ctx[name])
            regex = self.store.get_field_regex(name)
            if regex is None:
                continue
            if not re.fullmatch(regex, value):
                raise ValueError(
                    f"Field {name} value {value!r} doesn't match {regex}"
                )

        return ctx
```

---

## 9. StructureManager：獨立管理「要建什麼」

StructureManager 不碰 schema 細節，只透過 PathResolver 拿路徑，專心做：

- 專案 / asset / shot 被建立時，要建哪些資料夾
- 有需要時，在某些資料夾下建立預設檔案
- 每個節點可帶 metadata，給 UI 或進一步邏輯使用

### 9.1 `structures.yml` 範例（樹狀 + metadata）

```yaml
structures:
  project_basic:
    node:
      name: proj_root
      directory: proj_root
      meta:
        ui_label: "Project Root"
      children:
        - name: ref
          directory: proj_ref
          meta:
            ui_label: "References"
          children:
            - name: ref_2d
              directory: proj_ref_2d
              meta:
                ui_icon: "image_2d"
            - name: ref_3d
              directory: proj_ref_3d
              meta:
                ui_icon: "cube_3d"

        - name: client
          directory: proj_client
          meta:
            ui_label: "Client"

        - name: work
          directory: proj_work
          meta:
            ui_label: "Work"
          children:
            - name: work_cache
              kind: work_cache_file      # kinds 裡的一個檔案路徑
              create: file
              meta:
                description: "Initial cache file"
```

說明：

- `directory`：指向 schema.directories 的名稱 → `resolver.get_path(directory, **fields)`
- `kind`：指向某個 kind（通常是檔案）
- `meta`：任意 key/value，給 UI 或上層邏輯用
- `create`：
  - `dir`（可省略）→ mkdir
  - `file` → touch 檔案（`Path.touch()`）

---

### 9.2 StructureManager 簡化實作

```python
class StructureManager:
    def __init__(self, resolver: PathResolver, structures_cfg: dict):
        self.resolver = resolver
        self.structures = structures_cfg["structures"]

    def create(self, struct_name: str, **fields):
        root_node = self.structures[struct_name]["node"]
        self._create_node(root_node, fields, flags=set())

    def _create_node(self, node: dict, fields: dict, flags: set[str]):
        meta = node.get("meta", {})

        # 可利用 meta["require_flag"] + flags 做條件控制
        require_flag = meta.get("require_flag")
        if require_flag and require_flag not in flags:
            return

        # 1) 建資料夾
        if "directory" in node:
            dpath = self.resolver.get_path(node["directory"], **fields)
            dpath.mkdir(parents=True, exist_ok=True)

        # 2) 建檔案
        if "kind" in node:
            p = self.resolver.get_path(node["kind"], **fields)
            mode = node.get("create", "file")
            if mode == "file":
                p.parent.mkdir(parents=True, exist_ok=True)
                p.touch(exist_ok=True)

        # 3) 遞迴 children
        for child in node.get("children", []):
            self._create_node(child, fields, flags=flags)
```

---

## 10. 反向解析（選配）

如果需要從實際 path 反推 fields / kind，可以在「編譯階段」為每個 kind 建立一棵 pattern tree（trie）：

1. 將 template 拆成 segments：  
   例如：`"$root/$proj/ref/2d"` → `["$root", "$proj", "ref", "2d"]`
2. literal segment（字串常數）直接作為 trie key；  
   variable segment（`$root`, `$proj`）用特殊 slot，並記錄對應欄位名稱。
3. 解析時將 path 拆 segment，沿 trie 走下去：
   - variable segment 收集對應欄位值
   - literal segment 必須完全相等
4. 走到底的 node 可以對應到一個或多個 kinds → 做候選判定。

這部分可以實作在 PathResolver 的進階 API，例如：

- `resolver.parse(kind, path) -> fields`
- `resolver.guess_kinds(path) -> [(kind, fields?), ...]`

不影響本文件描述的 forward resolve 設計。

---