# Onboarding

## Documentation

All documents are located in the `docs` folder. You can edit them directly in the repository. `docs_templates` contains the templates for the StrictDoc markdown documents. You should follow the templates when editing documents.

Read [00_requirements.md](00_requirements.md) first, then [10_specifications.md](10_specifications.md) and [20_architecture.md](20_architecture.md) (including its ADRs) before making design decisions — several non-obvious constraints (vertical typesetting split, override-based editing, pre-1873 date handling) are recorded there and are easy to re-derive incorrectly from the code alone.

## Example data (`__example_data/`)

`__example_data/` (sample `.gpkg`, sample family-tree images, `GPKG_FORMAT_NOTES.md`) is listed in `.gitignore` and is **not present in every checkout or worktree** — it may exist in the main repository working copy but not in a given git worktree. Do not assume its presence.

Because of this, **automated tests must not depend on `__example_data/`**. `tests/fixtures/minimal_family.gramps.xml` is a small synthetic Gramps XML fixture that reproduces the edge cases discovered by analyzing the real sample data (adoption, remarriage, former surname, kana, birth-order labels, blood type, every date-completeness pattern the format supports, an unlinked nameless person, notes, and a media reference) — see `tests/gramps/test_gpkg_reader.py`. Extend this fixture rather than reaching for the real file when adding tests.

Manual verification against the real sample data (visual review in a browser, layout sanity checks on 136 people / 8 generations) is expected but optional and out of scope for CI.

## Python environment

The project is pinned to Python 3.12 (`.python-version`, `requires-python = ">=3.12"` in `pyproject.toml`) via [uv](https://docs.astral.sh/uv/). Python 3.14 was the original target but is only available locally as a pre-release build (`3.14.0a4`), which `uv` will not resolve against; revisit the pin once 3.14 reaches a stable release.

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy src tests
```

## Package layout

```
src/gpkg_jsr/
  gramps/gpkg_reader.py   Gramps .gpkg 読み込み。元 src/gpkg_reader.py を無変更で移設したもの。
                           ruff/mypy の strict ルールは per-file-ignore / override で緩めてある
                           (pyproject.toml を参照) — 新規コードには通常どおり全ルールを適用する。
                           このモジュールの list フィールドは型引数なし (list[Any] 相当) のため、
                           呼び出し側で str 化する際に mypy が Any 漏れを検出したら
                           typing.cast で明示する (format/name_rules.py の例を参照)。
  format/wareki.py        元号テーブル・和暦変換 (Phase 1)
  format/kanji_number.py  漢数字変換 (Phase 1)
  format/name_rules.py    家系姓判定・姓省略・旧姓 (Phase 1)
  model/graph.py          世代割当・到達可能集合計算 (Phase 1)
  model/view.py           Person -> PersonView への正規化 (Phase 1)
  layout/types.py         LayoutResult 等の pydantic モデル。Python/TS の唯一の契約 (Phase 2)
  layout/metrics.py       縦書きノードの寸法推定 (文字数ベースの近似。ADR-01) (Phase 2)
  layout/engine.py        自動レイアウト計算 (粗い版。重なり解消は Phase 6) (Phase 2)
  layout/paging.py        系統分割・A4 タイル割付。Phase 6 以降で追加
  api/app.py              FastAPI ルーティング (11_specifications-APIs.md) (Phase 3)
  api/store.py            アップロード済みプロジェクトのインメモリ管理 (Phase 3)
  api/schemas.py          API 応答用の pydantic モデル (Phase 3)
  api/errors.py           共通エラー応答形式 (API-00-02) (Phase 3)
web/src/
  types/layout.ts         LayoutResult 等の TS 型定義。pydantic モデルと手動で対応させる (Phase 3)
  api/client.ts            バックエンド API の fetch ラッパー (Phase 3)
  canvas/VerticalNode.tsx   縦書き人物ノード (CSS writing-mode + <ruby>) (Phase 3)
  canvas/ConnectorLayer.tsx SVG による夫婦連結線・親子接続線 (Phase 3)
  canvas/Viewport.tsx       パン・ズーム (Phase 3)
  canvas/FamilyTreeCanvas.tsx 上記3つを束ね、並び順軸の左右反転を適用する (Phase 3)
  editing/overrides.ts     オーバーライドレイヤー (ADR-02, DF-03-04)。ベースラインの
                           LayoutResult に位置・非表示の差分を適用する純粋関数 (Phase 4)
  editing/commandStack.ts  Undo/Redo 用のメメント方式コマンドスタック。ノード移動・
                           枝の折りたたみ・自動レイアウト再実行をすべて
                           Overrides のスナップショット差分として扱う (Phase 4)
```

`web/src/App.tsx` がこれらを結線する: `baseLayout` (サーバから取得したベースライン) +
`overrides` (state) を `applyOverrides` で合成して描画し、編集操作は
`commandStackRef.current.push(...)` してから `setOverrides(next)` する。

サーバの起動 (2 つとも起動する):

```bash
uv run uvicorn gpkg_jsr.api.app:app --reload --port 8000
```

```bash
cd web && npm install && npm run dev
```

`web/vite.config.ts` の dev サーバは `/api` を `http://127.0.0.1:8000` へプロキシする
(ポート番号を変える場合はここも合わせて変更する)。フロントエンドの検証コマンド:

```bash
cd web && npx tsc -b && npm run lint && npm run test && npm run build
```

`GET /api/v1/layout` は現状 `root_handle` が必須 (11_specifications-APIs.md の
API-02-01 の実装範囲メモを参照)。「全人物を1つの図に」(RQ-05-01) は今後拡張する。
プロジェクト保存/読込 (RQ-05-08) はサーバを経由せず `App.tsx` 内でブラウザの
ファイル保存/読込ダイアログのみを使って完結させている (API-04-01/04-02 の
実装範囲メモを参照)。

**並び順軸 (x) の左右反転を忘れないこと**: `layout.engine.build_layout` が返す
x 座標は「年長者が小さい x」の抽象順序であり、日本式表示 (年長者を右に配置、
RQ-02-03) への変換は描画層 (`FamilyTreeCanvas.tsx`) の責務。この反転を Phase 3
の初回実装で一度見落とし、ブラウザでの目視確認で気づいて修正した
(10_specifications.md の SP-02-07 を参照)。ノード・接続線の両方に同じ反転を
一貫して適用すること。

**ドラッグ操作は state ではなく ref で確定値を読むこと**: `VerticalNode.tsx` の
ドラッグ実装で、`pointerup` ハンドラが `pointermove` で更新した React state
(`dragOffsetPx`) を直接読むと、両イベントが同一タスク内で連続発火した場合に
古いクロージャの値 (更新前の state) を読んでしまい、ドラッグ操作が
コマンドとして積まれないことがある。ブラウザでの目視確認 (合成 PointerEvent
の連続ディスパッチ) で発見した。確定時に読む値は `useRef` (`latestOffsetPx`)
に持たせ、`dragOffsetPx` state は描画プレビュー専用にすること。

**既知の制約**: 枝の折りたたみ (SP-05-02) は「起点人物の子孫」を隠すのみで、
隠れた子孫の配偶者 (元々 X の子孫ではなく、その配偶者として表示されていた人物)
までは連動して隠さない。折りたたむと、隠れた人物の配偶者だけが他と接続されず
画面上に孤立して残る。RQ-05-02 の要求自体は満たすが、見た目の課題として
Phase 5/6 で見直す候補。

ディレクトリ構成の全体像は [20_architecture.md](20_architecture.md) の AD-01-02 を参照。
