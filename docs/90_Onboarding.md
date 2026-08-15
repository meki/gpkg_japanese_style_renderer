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
  editing/relations.ts     親子・配偶者・兄弟の関係グラフをベースラインの LayoutResult
                           から構築する (SP-05-06) (Phase 6)
  editing/revealAnchors.ts ノード単位で非表示にした人物の再表示ハンドルの位置
                           (アンカーとなる可視ノードと方向) を計算する (SP-05-06) (Phase 6)
  editing/selection.ts     右クリックドラッグの矩形選択とヒットテスト、選択中
                           ノードのまとめ移動の差分計算を行う純粋関数 (SP-05-07) (Phase 6)
  canvas/TitleDisplay.tsx  標題の縦書き表示。図の全高に合わせ右端に配置 (SP-06-01) (Phase 5)
  canvas/Legend.tsx        故人の凡例。該当者がいる場合のみ表示 (SP-03-09) (Phase 5)
  canvas/layoutConstants.ts UNIT_PX・ピクセルサイズ計算を FamilyTreeCanvas と
                           App (標題の高さ算出に使う) で共有するための切り出し (Phase 5)
  export/exportChart.ts   SVG 出力 (<foreignObject> による DOM のシリアライズ)。
                           PNG 出力は未実装、下記を参照 (Phase 6)
```

意匠用フォント (SP-06-02) は `@fontsource/yuji-syuku` (標題)・
`@fontsource/shippori-mincho` (本文・明朝体)・`@fontsource/klee-one`
(本文・楷書体寄り) を `main.tsx` で日本語サブセットのみ import し、
CDN を使わず自己ホストする (RQ-08-01)。書体は `index.css` の
`--font-title` / `--font-body-*` カスタムプロパティで参照する。

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

**婚姻線はボックスの中心同士ではなく、隣り合う端同士を結ぶこと**:
`ConnectorLayer.tsx` の婚姻線 (`MarriageEdge`) を人物ノードの中心座標同士で
結ぶと、線が両方のボックスの内側まで伸びてしまう。ボックスが不透明であれば
視覚的な破綻は目立たないが、以前 `.vertical-node--spouse-in` に `opacity`
を使っていたため、線がボックスの背後に透けて見える不具合として実データで
発覚した。修正は 2 点: (1) `facingEdges()` で実際に向き合うボックスの端
(小さい abstract x 側の右端・大きい abstract x 側の左端) を計算し、線を
その間だけに限定する、(2) `.vertical-node--spouse-in` から `opacity` を撤去し
不透明な代替スタイル (`border-color`) に置き換える。ボックスの背景・境界線に
`opacity` を使うと同様の問題が再発するため、透明度が必要な場合は
`background-color` に直接アルファを持たせるなど、他要素を巻き込まない方法を
選ぶこと。

**ノード寸法の見積もり定数は、制約なしで自然にレンダリングさせた状態で実測すること**:
`layout/metrics.py` の `estimate_node_size` は文字数ベースの近似で frame の
寸法を見積もる (ADR-01)。当初は 1 文字 = 1 単位のような粗い係数だったため、
実際の描画より frame がかなり大きくなり、無駄な余白として実データ確認で
指摘された。係数を実測値ベースに縮小したところ、今度は逆に、旧姓・続柄が
同時に付く人物などで frame が実際の文字数に対してわずかに足りず、縦書き
テキストが折り返して余分な列ができてしまう回帰が発生した (「二行になる」
不具合として報告された)。原因は 2 つ: (1) 実測に使った DOM が
`.vertical-node` に明示的な width/height を指定した「制約あり」の状態
だったため、既に折り返した後のサイズを「正しいサイズ」として実測してしまい、
本当に必要な余白より小さい値を採用してしまっていた。(2) 実測値をそのまま
frame の寸法に使うと、ブラウザのサブピクセル丸め・フォントレンダリングの
誤差だけで「1px 足りず折り返される」際どい状態になる。正しい手順は:
`VerticalNode.css` と同じ CSS クラスを、明示的な width/height を指定しない
独立した静的 HTML (`web/public/` に置いて vite dev server 経由で開けば
`getBoundingClientRect()` で実測できる) に再現し、複数の文字数パターンで
線形性を確認してから係数を求め、さらに明確な安全マージン
(`_HEIGHT_SAFETY_PX` / `_WIDTH_SAFETY_PX`) を上乗せすること。

**接続線はレイアウト計算時点の静的座標ではなく、現在のノード位置から都度再計算すること**:
手動でのノード移動 (`editing/overrides.ts` の `node_positions` オーバーライド) は
`PersonNode.x/y` のみを上書きし、`MarriageEdge`/`ChildEdge` の静的な座標
フィールド (`midpoint_x`/`y`/`points`) はレイアウト計算時点の値のまま更新されない。
そのため `ConnectorLayer.tsx` がこれらの静的座標をそのまま描画すると、ノードを
ドラッグしても婚姻線は追従するが親子接続線だけ古い位置に取り残される、という
不具合が実データ確認で発覚した (婚姻線は以前の修正で既に動的再計算になって
いたが、親子接続線は未対応だった)。修正として `canvas/connectorGeometry.ts` に
`buildNodeIndex`/`facingEdges`/`marriageEdgeY`/`computeChildEdgeGeometry` を
切り出し、婚姻線・親子接続線の両方を **毎レンダリングごとに現在のノード位置から
再計算する** 方式に統一した。`MarriageEdge`/`ChildEdge` の静的フィールドは
初期表示のフォールバック目的以外では信頼しないこと。

**生没年列の左右反転は、接続線側でも同じボックス位置補正が必要**:
生没年列が婚姻線と重ならないよう `VerticalNode.tsx` はセル内でボックス本体と
生没年列の左右を入れ替える機能 (`dateSide` prop) を持つが、これは
「セル (ボックス+生没年列) の左端」から `date_column_width` 分だけボックスを
画面上ずらす **見た目だけの調整** であり、`PersonNode.x/width` (abstract 座標)
自体は変化しない。この非対称性に気づかず `connectorGeometry.ts` の婚姻線・
親子接続線の計算に生の `node.x` を使うと、生没年列が左側に出た人物 (配偶者側)
のボックスと接続線の間に `date_column_width` 分の隙間ができる不具合を、
ブラウザでの `getBoundingClientRect()` 突き合わせ検証で発見した (見た目には
軽微だが `line.left`/`box.right` を厳密に比較して判明)。修正は
`connectorGeometry.ts` に `buildVisualNodeIndex(layout, marriageSides)` を追加し、
`dateSide==="left"` のノードは `x` を `x - date_column_width` に補正した
「実際に画面へ描画される位置」を表すノード集合を作り、`ConnectorLayer.tsx` は
必ずこの補正済みノード集合を使って接続線を計算すること。生没年列の配置
ロジックを変更する際は、`VerticalNode.tsx` の見た目上のオフセットと
`connectorGeometry.ts` の補正ロジックを必ず両方同時に見直すこと（片方だけ
直すと再びこの不具合が再発する）。

**ノード単位の非表示 (SP-05-06) はブランチ折りたたみ (SP-05-02) と同じ `hidden_handles` を共有すること**:
実装当初、専用のオーバーライドフィールドを新設することも検討したが、
`hidden_handles: string[]` は元々「非表示にする handle の集合」という一般的な
意味で設計されていた (`editing/overrides.ts` の `applyOverrides` は特定の
非表示理由を区別しない) ため、単一ノードの非表示もこの同じ配列に handle を
1 件追加するだけで実現できる。これにより、婚姻線・親子接続線の連動非表示も
既存のフィルタリングロジックをそのまま再利用でき、新規実装が不要になった。
一方で、この共有により「枝を展開」操作 (`handleToggleCollapse`) は、その枝の
子孫であれば個別非表示ノードも含めてまとめて再表示する（個別非表示という
区別を保持しない）。これは意図的な単純化であり、「枝を展開したら中身は
全部見える」という直感に合致するため許容している。

**再表示ハンドルの位置計算は、オーバーライド適用後ではなくベースラインの
LayoutResult に対して行うこと**:
非表示ノードは `applyOverrides` によって表示用の `LayoutResult` から完全に
除去されるため、そこから親子・配偶者・兄弟関係をたどることはできない
(非表示ノード自身も、非表示ノードを介した先の関係も失われる)。
`editing/revealAnchors.ts` の `computeRevealAnchors` は必ず `baseLayout`
(オーバーライド適用前、全ノードを含む) を受け取ること。可視ノードの
画面上の位置（ハンドルの実際の描画座標）は表示用 `LayoutResult` 側
(手動移動や生没年列の左右反転を反映済み) から取る必要があるため、
`FamilyTreeCanvas.tsx` は `connectorGeometry.ts` の `buildVisualNodeIndex`
を再利用してアンカーの矩形を計算している（接続線の位置計算と同じ理由 —
上記の「生没年列の左右反転は…」の項を参照）。

**矩形選択・パン・ノードドラッグはマウスボタンで排他的に切り分けること**:
`Viewport.tsx` は元々マウスボタンを区別せず、背景での pointerdown を一律パン
操作として扱っていた。右クリックドラッグを矩形選択 (SP-05-07) に割り当てる
にあたり、`event.button` (0=左, 2=右) で処理を完全に分岐させ、`onContextMenu`
で右クリックの既定コンテキストメニューも抑止する必要がある。また
`VerticalNode.tsx` 側のノード自身の pointerdown ハンドラも、それまで
ボタン種別を見ずに常に `stopPropagation` していたため、右クリックがノード上
から始まった場合に矩形選択の起点として使えなかった。左クリックのみ
`stopPropagation` するよう変更し、右クリックはノード上からでも Viewport まで
バブリングさせて矩形選択の起点にできるようにした。

**選択中ノードのまとめ移動は、絶対座標ではなく差分をノードごとに適用すること**:
`VerticalNode.tsx` の `onDragEnd` は元々「確定後の絶対座標 (x, y)」を1ノード分
だけ通知していたが、複数選択のまとめ移動 (SP-05-07) では、選択中の各ノードが
それぞれ異なる現在位置 (既存の手動オーバーライドを含む) を持つため、絶対座標
1件では対応できない。`onDragEnd` の通知内容を「画面ピクセル移動量から変換した
抽象座標の差分 (deltaX, deltaY)」に変更し、`App.tsx` 側で選択中の各ノードの
現在位置 (`displayLayout` = オーバーライド適用後) にこの差分を適用する
(`editing/selection.ts` の `computeGroupMove`)。ドラッグされたノードが選択中
グループの一員でない場合は、そのノード単体だけを同じ経路で移動する
(選択状態は変更しない)。

**この環境のブラウザ操作ツールでは、右クリックドラッグの E2E 検証ができない**:
`mcp__Claude_Browser__computer` には右クリックのドラッグ相当のアクションが
無く (`left_click_drag` と単発の `right_click` のみ)、また `PointerEvent` を
JavaScript から `dispatchEvent` で合成して代用しようとしても、`setPointerCapture`
が「アクティブなポインタが存在しない」という `NotFoundError` を投げ、
React 側のドラッグハンドラが正しく動作しない（左クリックの合成ドラッグでも
同様に失敗した。ブラウザの実際の入力パイプラインを経由しない合成
`PointerEvent` は信頼されないため）。この機能の検証は、(1) 矩形選択・
まとめ移動のヒットテストと座標変換ロジックを `editing/selection.ts` の
純粋関数として切り出し vitest で網羅的に検証する、(2) 左クリックのパン・
単一ノードドラッグ (既存の動作するコードパスと構造が対称) を
`computer.left_click_drag` で回帰確認する、(3) 右クリック単発 (ドラッグなし)
がコンテキストメニューを出さずパンもしないことを `computer.right_click` で
確認する、という組み合わせで行った。右クリックドラッグそのものの実ブラウザ
確認が必要な場合は、人手での確認を依頼すること。

**既知の制約 (複数配偶者の婚姻線)**: ある人物が複数の配偶者を持つ場合
(再婚)、2 人目以降の配偶者との婚姻線は、間に挟まる別の配偶者のボックスの
真下 (画面上は背後) を通過する。人物枠が不透明な既定設定では視覚的に隠れて
問題にならないが、人物枠を非表示にする設定 (`showFrame: false`) にすると
露呈しうる。3 人以上が絡む婚姻線のルーティングは今回未対応。

**既知の制約**: 枝の折りたたみ (SP-05-02) は「起点人物の子孫」を隠すのみで、
隠れた子孫の配偶者 (元々 X の子孫ではなく、その配偶者として表示されていた人物)
までは連動して隠さない。折りたたむと、隠れた人物の配偶者だけが他と接続されず
画面上に孤立して残る。RQ-05-02 の要求自体は満たすが、見た目の課題として
Phase 5/6 で見直す候補。

**印刷ビュー・SVG 出力には編集専用 UI (非表示ボタン・再表示ハンドル) を含めないこと**:
ノード単位の非表示ボタン (`.vertical-node__hide-toggle`, SP-05-06) と再表示
ハンドル (`.reveal-handle`, SP-05-06) を追加した際、`App.css` の
`@media print` の非表示対象リストと `export/exportChart.ts` の
`serializeChartToSvg()` の除去対象リストの両方に追加するのを忘れており、
印刷プレビュー・SVG 出力の両方に編集用のボタン・ハンドルがそのまま写り込む
不具合が実利用で報告された。**編集専用の UI 要素を新設したら、必ずこの 2 箇所
(印刷 CSS と SVG エクスポートの除去セレクタ) の両方を同時に更新すること**
(既存の `.vertical-node__collapse-toggle` も同じ扱いになっている)。

**SVG 出力の `<img>` は data: URI として埋め込むこと (相対 URL のままだと単体で開けない)**:
顔写真は `personPhotoUrl()` が返す `/api/v1/projects/{id}/people/{handle}/photo`
という相対 URL を `src` に使っているため、アプリの画面内で見ている分には
問題なく表示されるが、`serializeChartToSvg()` が生成した `.svg` を単体の
ファイルとしてダウンロードし、別タブ・別オリジン・ローカルファイルとして
開くと、その相対 URL は解決できずリンク切れ画像になる (実データ確認で発覚)。
「単体で完結した SVG」という設計意図 (ファイル冒頭のコメント参照) を満たす
には、シリアライズ前に `<img>` の `src` を `fetch()` で取得したバイト列から
`data:` URI に変換して埋め込む必要がある (`inlinePhotoImages()`)。取得に
失敗した画像は元の参照のまま残し、出力全体は失敗させない。

**`<foreignObject>` は Canvas を tainted にする (PNG 出力が実装できない理由)**:
人物ノードを HTML (`writing-mode` + `<ruby>`) で描画しているため、家系図を
SVG 化するには `<foreignObject>` で DOM をそのまま埋め込む方式しか現実的でない
(`export/exportChart.ts`)。この SVG を `<img>` 経由で `<canvas>` に描画し
`toBlob()`/`toDataURL()` で PNG 化しようとすると、ブラウザでの実地検証により
**内容（フォント参照・写真 `<img>` 等の外部リソースの有無）に関わらず
`SecurityError: Tainted canvases may not be exported` が発生する**ことを確認した
(`<foreignObject>` の存在自体が原因で、外部リソースを取り除いても再現する)。
そのため PNG 出力ボタンは実装せずに見送った (SVG 出力は影響を受けないため実装
済み)。10_specifications.md の SP-07-05 に詳細を記録。PNG が必要になった場合は
html2canvas 等の `<foreignObject>` を使わないライブラリ、またはサーバ側の
ヘッドレスブラウザによるラスタライズを検討すること。

**印刷ビューは "1 枚に収める" ケースのみ対応**: `@media print` CSS でツールバー等の
編集用 UI を非表示にし、`window.print()` で PDF 化できる (SP-07-01, SP-07-05)。
一方で系統分割 (SP-07-03) と、のりしろ・トンボ付きの A4 タイル印刷 (SP-07-04) は
未実装。図が 1 ページに収まらない場合はブラウザの既定のページ分割に委ねる
(意図した分割にはならない)。レイアウトの重なり・交差解消 (ADR-01 で Phase 6 に
据え置くとしていたもの) も未着手。次にこのプロジェクトへ着手する際の最有力候補。

ディレクトリ構成の全体像は [20_architecture.md](20_architecture.md) の AD-01-02 を参照。
