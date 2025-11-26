# Schema Editor UI

視覺化編輯 Path Manager 的 schema.yml 檔案。

## 功能特色

### 📝 欄位編輯 (Fields)
- 定義可在路徑中使用的變數欄位
- 設定正則表達式驗證規則
- 提供示例值
- 支援新增、編輯、刪除欄位

### 📁 目錄結構編輯 (Directories)
- 視覺化樹狀結構顯示
- 支援階層式目錄定義
- 可使用 `$變數名` 引用欄位
- 支援固定路徑片段
- 支援新增、編輯、刪除節點

### 📄 檔名模板編輯 (Filenames)
- 定義可重複使用的檔名模板
- 支援 `$變數` 語法
- 管理多個檔名模板

### 🎯 種類定義 (Kinds)
- 組合目錄和檔名模板
- 下拉選單選擇已定義的目錄和檔名
- 定義完整的路徑種類

### 💾 導入/導出
- 導入現有的 YAML schema 檔案
- 導出為標準 schema.yml 格式
- 載入範例 schema
- 即時驗證 schema 結構

## 使用方法

### 1. 開啟編輯器

在瀏覽器中開啟 `schema_editor.html`：

```bash
# 使用 Python 啟動本地伺服器
python3 -m http.server 8000

# 在瀏覽器開啟
# http://localhost:8000/schema_editor.html
```

或直接在瀏覽器中開啟檔案：
```bash
open schema_editor.html
```

### 2. 編輯 Schema

#### 編輯欄位
1. 切換到「欄位 (Fields)」標籤
2. 點擊「+ 新增欄位」按鈕
3. 輸入欄位名稱
4. 在表格中編輯正則表達式和示例值

範例：
- **名稱**: `proj`
- **正則表達式**: `[A-Za-z0-9_]+`
- **示例**: `demo_proj`

#### 編輯目錄結構
1. 切換到「目錄結構 (Directories)」標籤
2. 點擊「+ 設定根目錄」建立根節點
3. 在每個節點上：
   - 點擊「✏️」編輯節點
   - 點擊「➕」新增子節點
   - 點擊「🗑️」刪除節點

路徑片段語法：
- `$root` - 引用 root 欄位的值
- `$proj` - 引用 proj 欄位的值
- `asset` - 固定字串

#### 編輯檔名模板
1. 切換到「檔名模板 (Filenames)」標籤
2. 點擊「+ 新增檔名模板」
3. 輸入模板名稱
4. 編輯模板內容

範例模板：
- `$asset.v$ver.$ext` → `tree.v003.jpg`
- `$asset.$ext` → `tree.jpg`

#### 定義種類
1. 切換到「種類 (Kinds)」標籤
2. 點擊「+ 新增種類」
3. 輸入種類名稱
4. 從下拉選單選擇目錄和檔名

### 3. 導入/導出

#### 導入 YAML
1. 點擊「📁 導入 YAML」按鈕
2. 選擇 `.yml` 或 `.yaml` 檔案
3. Schema 會自動載入到編輯器

#### 導出 YAML
1. 點擊「💾 導出 YAML」按鈕
2. 檔案會自動下載為 `schema.yml`

#### 載入範例
點擊「📋 載入範例」按鈕可載入預設的範例 schema。

### 4. 驗證 Schema

點擊「✓ 驗證」按鈕檢查 schema 是否有效：
- 檢查是否定義了必要的欄位
- 檢查目錄結構是否存在
- 檢查種類是否正確引用目錄和檔名

## Schema 結構範例

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

這會產生路徑：`/proj/demo_proj/asset/tree/render/jpg/tree.v003.jpg`

## 編輯工作流程

### 典型的 Schema 設計流程

1. **定義欄位** - 先定義會在路徑中使用的所有變數
   - 專案名稱、資產名稱、版本號等
   - 設定驗證規則（正則表達式）

2. **建立目錄結構** - 設計階層式目錄樹
   - 從根目錄開始
   - 逐層建立子目錄
   - 混合使用變數 (`$proj`) 和固定字串 (`asset`)

3. **定義檔名模板** - 建立可重複使用的檔名格式
   - 考慮不同的檔案類型
   - 包含版本控制

4. **組合種類** - 將目錄和檔名組合成完整路徑
   - 為每種檔案類型定義一個種類
   - 確保引用的目錄和檔名都存在

5. **驗證和測試** - 使用編譯器測試
   ```bash
   python -m path_manager.compiler schema.yml schema.db
   ```

## 技術細節

### 依賴項
- 瀏覽器內建功能（無需安裝）
- js-yaml CDN（自動載入）

### 瀏覽器支援
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

### 資料結構
編輯器使用 JavaScript 物件儲存 schema，結構與 YAML 格式一致，可直接轉換。

## 最佳實踐

1. **命名規範**
   - 使用小寫字母和底線：`asset_render_jpg`
   - 避免特殊字元
   - 使用描述性名稱

2. **目錄結構**
   - 保持階層清晰
   - 不要過深（建議 5-7 層以內）
   - 合理使用變數和固定字串

3. **正則表達式**
   - 儘可能嚴格，但保持實用性
   - 提供清楚的示例值
   - 考慮跨平台相容性

4. **版本控制**
   - 將 `schema.yml` 納入 git
   - 使用有意義的 commit 訊息
   - 標記重大變更的版本

## 整合工作流程

編輯完成後，使用 Path Manager 編譯和使用：

```bash
# 編譯 schema
python -m path_manager.compiler schema.yml schema.db --format sqlite

# 在程式中使用
from path_manager.resolver import PathResolver

resolver = PathResolver.from_file('schema.db')
path = resolver.get_path('asset_render_image_versioned',
                         root='/proj',
                         proj='demo',
                         asset='tree',
                         ver='003',
                         ext='jpg')
print(path.as_posix())
# /proj/demo/asset/tree/render/jpg/tree.v003.jpg
```

## 常見問題

**Q: 可以編輯多個 schema 嗎？**
A: 每次只能編輯一個 schema，但可以隨時導入/導出不同的 YAML 檔案。

**Q: 編輯器會自動儲存嗎？**
A: 不會，需要手動點擊「導出 YAML」按鈕儲存。建議定期導出。

**Q: 如何備份我的 schema？**
A: 使用「導出 YAML」功能，並將檔案納入版本控制系統（如 git）。

**Q: 支援 undo/redo 嗎？**
A: 目前不支援，建議在做重大修改前先導出備份。

## 相關文件

- [Path Manager README](README.MD) - 主要文件
- [Platform Schemas](examples/PLATFORM_SCHEMAS.md) - 跨平台 schema 指南
- [Examples](examples/) - Schema 範例
