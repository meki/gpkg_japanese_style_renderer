# データ形式仕様

本書は Python コアとブラウザ描画層の間で受け渡す JSON スキーマ、およびプロジェクト保存ファイルの形式を定義する。すべてのスキーマは pydantic v2 モデル（Python 側）と対になる TypeScript 型（`web/src/types/`）として実装し、両者を手動で同期させる（Phase 3 時点ではコード生成は導入しない）。

## LayoutResult（Python → ブラウザ）

### LayoutResult のトップレベル構造

**UID**: DF-01-01 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-05-04

```json
{
  "version": 1,
  "direction": "vertical",
  "nodes": [ /* PersonNode[] */ ],
  "marriage_edges": [ /* MarriageEdge[] */ ],
  "child_edges": [ /* ChildEdge[] */ ],
  "auxiliary_nodes": [ /* PersonNode[] */ ]
}
```

`nodes` は世代グリッドに配置された人物ノード (SP-02-01〜02-04)。`auxiliary_nodes` は婚入配偶者の実家併記 (SP-02-06) のような、通常のグリッド配置対象外のノード。`direction` は `"vertical"` | `"horizontal"` (SP-02-07)。

### PersonNode

**UID**: DF-01-02 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-03-01

```json
{
  "handle": "_p0898...",
  "generation": 3,
  "order_in_generation": 5,
  "x": 120.0,
  "y": 340.0,
  "width": 32.0,
  "height": 96.0,
  "date_column_width": 19.2,
  "view": { /* PersonView, DF-01-03 */ }
}
```

`x` / `y` / `width` / `height` は SP-02-07 で述べる抽象座標系（世代軸・並び順軸）での値。方向変換は描画層で行うため、ここでは常に「世代軸 = 縦方向」の座標として格納する。`width` / `height` は罫線で囲むノード本体 (frame) のみの寸法であり、生没年の表記幅は含まない。生没年は `date_column_width` 分だけ frame の外側（画面表示では frame の右隣）に描画層が独立した列として配置する (SP-03-06)。`date_column_width` が 0 の場合は生没年を表示しない（対象人物に生没年がない、または表示トグルが OFF）。

### PersonView

**UID**: DF-01-03 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-03-01
- **Type**: Parent
  **ID**: SP-03-01

```json
{
  "surname": "山田",
  "given_name": "長左衛門",
  "surname_kana": "しまむら",
  "given_name_kana": "ちょうざえもん",
  "former_surname": null,
  "is_spouse_in": false,
  "birth_order_label": "長男",
  "birth_date_display": { "calendar": "wareki", "text": "明治二十七年八月十二日生" },
  "death_date_display": null,
  "is_deceased": false,
  "has_photo": true,
  "notes": ["兄弟の中では一番下"],
  "is_focus_person": false,
  "gender": "M"
}
```

`birth_date_display` / `death_date_display` は西暦・和暦いずれの表示モードでも同じ形（`calendar` フィールドで判別可能な `{calendar, text}`）とし、両方を同時に含める場合 (SP-04-06) は将来 `text_secondary` を追加する形で後方互換に拡張する。

### MarriageEdge / ChildEdge

**UID**: DF-01-04 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-02-04
- **Type**: Parent
  **ID**: RQ-02-05
- **Type**: Parent
  **ID**: RQ-02-06

```json
{
  "family_handle": "_fXXXX",
  "husband_handle": "_pAAAA",
  "wife_handle": "_pBBBB",
  "midpoint_x": 150.0,
  "y": 340.0
}
```

```json
{
  "family_handle": "_fXXXX",
  "child_handle": "_pCCCC",
  "parent_handles": ["_pAAAA", "_pBBBB"],
  "relation": "birth",
  "points": [[150.0, 340.0], [150.0, 360.0], [200.0, 360.0], [200.0, 420.0]]
}
```

`relation` は `"birth"` | `"adopted"`。`points` は SP-02-04 の 3 セグメント（始点→水平→垂直）を明示的な折れ点列として持ち、描画層でのルーティング再計算を不要にする。`parent_handles` はレイアウト対象に含まれる親の `handle`（両親が対象なら 2 件、単親家庭または一方が対象範囲外なら 1 件）。`MarriageEdge` は両親がそろっている family にしか存在しないため（SP-02-03）、子孫方向の到達可能集合をクライアント側で辿る用途（枝の表示/非表示、SP-05-02）には `MarriageEdge` ではなく本フィールドを使う。

## TilePage（A4 タイル印刷）

### TilePage の構造

**UID**: DF-02-01 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-07-04
- **Type**: Parent
  **ID**: SP-07-04

```json
{
  "page_id": "B-2",
  "row": 1,
  "col": 2,
  "viewbox": { "x": 300.0, "y": 100.0, "width": 210.0, "height": 297.0 },
  "overlap_mm": 10.0,
  "crop_marks": [[10, 10], [200, 10], [10, 287], [200, 287]]
}
```

`page_id` は列を英字、行を数字で表す（サンプル画像の「1 系統/2 系統」の系統分割とは別軸）。`viewbox` はのりしろを含んだ、元図の抽象座標系での切り出し矩形。

## ProjectDocument（プロジェクト保存ファイル）

### 保存ファイルのトップレベル構造

**UID**: DF-03-01 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-05-08
- **Type**: Parent
  **ID**: SP-05-04

```json
{
  "format_version": 1,
  "source_gpkg": {
    "filename": "山田家系図.gpkg",
    "size_bytes": 1360849,
    "sha256": "..."
  },
  "title_settings": { "text": "山田家系図", "font": "yuji-syuku", "position": "right" },
  "style_settings": { /* DF-03-02 */ },
  "display_toggles": { /* DF-03-03 */ },
  "overrides": { /* DF-03-04 */ },
  "focus_person_handle": "_p0898...",
  "collapsed_branches": ["_p0912..."]
}
```

`source_gpkg.sha256` は API-04-02 の整合性確認に用いる。`.gpkg` バイナリ自体はこのファイルに含めない（RQ-05-08 の「元データを書き換えない」を、別ファイルとして扱うことで満たす）。

### style_settings

**UID**: DF-03-02 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-06-02
- **Type**: Parent
  **ID**: RQ-06-03
- **Type**: Parent
  **ID**: RQ-03-08

```json
{
  "body_font": "shippori-mincho",
  "calendar": "wareki",
  "direction": "vertical",
  "person_frame": true,
  "colors": { "text": "#1a1a1a", "line": "#333333", "background": "#fdfcf7", "focus": "#b5321a" }
}
```

### display_toggles

**UID**: DF-03-03 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-03-12

```json
{
  "ruby": true,
  "birth_order": true,
  "dates": true,
  "photos": true,
  "notes": false,
  "former_surname": true
}
```

### overrides

**UID**: DF-03-04 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-05-05
- **Type**: Parent
  **ID**: RQ-05-07
- **Type**: Parent
  **ID**: SP-05-02

```json
{
  "node_positions": { "_p0898...": { "x": 130.0, "y": 340.0 } },
  "hidden_handles": ["_p0912..."]
}
```

`node_positions` のキーが存在しない人物は、その時点の自動レイアウト計算結果 (DF-01-01) をそのまま用いる。オーバーライドはベースラインの再計算 (SP-05-03 の自動レイアウト再実行) をまたいでも、キーが指す `handle` が引き続きレイアウト対象に含まれる限り保持する。
