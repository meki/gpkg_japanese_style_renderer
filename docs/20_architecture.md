# アーキテクチャ

本書はシステム構成・データフロー・モジュール境界を `AD-` として、設計判断の根拠を `ADR-` として記録する。要件は [00_requirements.md](00_requirements.md)、機能仕様は [10_specifications.md](10_specifications.md) を参照。

## 1. 全体構成

### システム構成

**UID**: AD-01-01 \
**STATUS**: Active

ローカル Web アプリ構成とする (RQ-08-01)。Python (FastAPI) バックエンドが gpkg 解析・ドメインモデル構築・レイアウト計算を担い、ブラウザ (Vite + React + TypeScript) が縦書き描画・対話編集・印刷ビューを担う。両者は HTTP (JSON) で通信し、ブラウザは `localhost` の FastAPI プロセスにのみ接続する。

```
.gpkg ファイル
  │  (tar.gz + 二重 gzip)
  ▼
GrampsDatabase  ……… src/gpkg_jsr/gramps/gpkg_reader.py (既存、無変更)
  │  (person/family/event/... の Python オブジェクト)
  ▼
PersonView / DAG  ……… model/, format/
  │  (表示用に正規化された派生データ)
  ▼
LayoutResult (JSON)  ……… layout/
  │  ← Python/TS の唯一の契約 (ADR-04)
  ▼
VerticalNode / ConnectorLayer (React)  ……… web/src/canvas/
  │  (CSS writing-mode + <ruby> + SVG 折れ線)
  ▼
編集オーバーライド (client state)  ……… web/src/editing/
  │
  ▼
印刷ビュー / SVG・PNG・PDF 出力
```

### モジュール境界

**UID**: AD-01-02 \
**STATUS**: Active

```
src/gpkg_jsr/
  gramps/gpkg_reader.py   既存 src/gpkg_reader.py の移設。gpkg パースのみ担当し、表示ロジックを持ち込まない
  model/view.py           Person -> PersonView への正規化 (SP-01, SP-03-01)
  model/graph.py          DAG 構築・世代割当・到達可能集合計算 (SP-01-02, SP-02-01, SP-05-01)
  format/wareki.py        元号テーブル・和暦変換 (SP-04-01, SP-04-02, SP-04-04)
  format/kanji_number.py  漢数字変換 (SP-04-03)
  format/name_rules.py    家系姓判定・姓省略・旧姓 (SP-03-02, SP-03-03)
  layout/metrics.py       縦書きノード寸法推定 (ADR-01)
  layout/types.py         LayoutResult 等の pydantic モデル (DF-01, DF-02)
  layout/engine.py        自動レイアウト計算 (SP-02)
  layout/paging.py        系統分割・A4 タイル割付 (SP-07-03, SP-07-04)
  api/app.py               FastAPI ルーティング (11_specifications-APIs.md)
web/src/
  canvas/                 VerticalNode・ConnectorLayer・Viewport (縦書き描画そのもの)
  editing/                overrides・commandStack (ADR-02)
  panels/                 スタイル・表示範囲・印刷パネル (UI-03)
  print/                  タイル印刷ビュー (SP-07-01, SP-07-04)
```

各層は上位層の存在を知らない一方向の依存とする（`gramps` は `model` を知らない、`model`/`format` は `layout` を知らない、`layout` は `api` を知らない）。この順序を逆転させる変更（例: `layout` が `gramps` の XML 構造に直接依存する）は行わない。

### LayoutResult を Python/TS の唯一の契約とする

**UID**: AD-01-03 \
**STATUS**: Active

バックエンドとフロントエンドの間で受け渡すデータは `LayoutResult` ([12_specifications-data_format.md](12_specifications-data_format.md)) に一本化する。`GrampsDatabase` の内部表現 (`Person`, `Family` 等) を API 経由で直接ブラウザへ渡さない。これにより、将来 Python コアを別言語へ置き換える場合の影響範囲を `layout/` 配下に限定できる (ADR-04)。

## 2. Architecture Decision Records

### ADR-01: 縦書き組版の分担をブラウザに委ねる

**UID**: ADR-01-01 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-02-01

**決定**: 縦書き・ルビの実際の組版は CSS (`writing-mode: vertical-rl`, `<ruby>`) にすべて委ね、Python 側はフォントメトリクスを実測せず、文字数ベースの近似（全角 1em・半角 0.5em、ルビ分の追加余白）でノード寸法を見積もる (`layout/metrics.py`)。

**背景**: 縦書き・ルビの自前実装（PDF 生成ライブラリでの座標計算など）は組版ルール（禁則処理、ルビの追い出し等）を Python 側で再実装することになり、コストが高い。ブラウザの縦書きサポートは成熟しており、これを使わない理由がない。

**トレードオフ**: Python 側の寸法推定はフォントの実際のグリフ幅と厳密には一致しない。ノードの重なりが発生しうるが、それは Phase 6 のレイアウト品質改善（重なり解消・微調整）で吸収する方針とし、Phase 2〜5 では許容する。

**代替案として却下したもの**: (a) サーバ側でヘッドレスブラウザにより実測する — 開発体験・速度を大きく損なうため却下。(b) Python 側で独自フォントメトリクスDBを持つ — 同梱フォント変更のたびにメンテナンスが必要になるため却下。

### ADR-02: 編集モデルはオーバーライド方式とする

**UID**: ADR-02-01 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-05-05
- **Type**: Parent
  **ID**: RQ-05-06
- **Type**: Parent
  **ID**: RQ-05-07

**決定**: 自動レイアウト結果 (`LayoutResult`) を不変のベースラインとして扱い、ユーザーによる手動調整は `handle -> 差分` の別レイヤ（オーバーライド、[DF-03-04](12_specifications-data_format.md)）として保持する。描画時にベースラインへオーバーライドを重ねて最終表示を得る。

**背景**: 自動レイアウト結果に対して手動調整を破壊的に上書きすると、「自動調整の実行・アンドゥ」(RQ-05-04, RQ-05-06) が手動調整ごと失われる、あるいは自動再計算のたびに手動調整が消えるという二者択一を迫られる。オーバーライドを独立レイヤとすることで、自動レイアウトの再実行と手動調整の保持を両立できる。

**トレードオフ**: 自動レイアウトが人物の世代・並び順を変更した場合、既存のオーバーライド（座標指定）が意味的に古くなる可能性がある（例: ある人物が別の並び順に移動したのに、古い絶対座標のオーバーライドが残る）。当面は「オーバーライドは対象 `handle` がレイアウト対象に残る限り機械的に保持する」(SP-05-02) という単純な規則とし、意味的な追従は将来の検討課題とする。

### ADR-03: 明治 6 年以前の日付は月日を確定表示しない

**UID**: ADR-03-01 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-04-05

**決定**: 和暦表示モードにおいて、グレゴリオ暦への切替日 (1873-01-01) より前の `dateval` は元号年までを表示し、月日は表示しない (SP-04-04)。西暦表示モードでは既存の `GDate.format_ja()` の出力をそのまま用いる（変更を加えない）。

**背景**: `.gpkg` 内の `dateval` は年-月-日の 3 要素として保存されているが、明治 6 年より前の日付がその表現のまま**旧暦の日付**なのか、それとも**グレゴリオ暦へすでに換算済みの値**なのかを、データそのものから判別する手段がない（[GPKG_FORMAT_NOTES.md](../__example_data/GPKG_FORMAT_NOTES.md) の変換元データに関する注記も参照）。誤った月日を断定的に和暦で表示すると、実際の月日と異なる日付を史実として提示してしまう。

**トレードオフ**: 該当期間の日付情報を一部欠落させる（月日を捨てる）ことになるが、誤情報を提示するより安全側に倒す。西暦表示では引き続き元の月日を確認できるため、情報自体は失われない。

**将来の見直し**: 元データの生成経緯（旧暦かグレゴリオ暦換算か）が判明した場合、または `quality`/`cformat` 属性等で明示される場合は、本 ADR を改訂し月日表示を復活させる。

### ADR-04: Python コアとブラウザ描画層の境界

**UID**: ADR-04-01 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-08-03

**決定**: Python コア (`model/`, `format/`, `layout/`) はブラウザ・DOM・CSS の知識を一切持たず、`LayoutResult` という座標・スタイル指定込みの JSON のみを出力する。逆に React 側は Gramps のデータモデル (`handle`, `frel` 等) を意識せず、`PersonView` / `PersonNode` の型だけを扱う (AD-01-03)。

**背景**: この境界により、(a) Python コアは画面描画に依存せず pytest で検証できる (RQ-08-03, SP-08-03)、(b) 将来描画技術を差し替える場合（例: React から別フレームワークへ、あるいはネイティブ GUI へ）も Python コアへの影響をゼロにできる、という 2 つの目的を同時に満たす。

**トレードオフ**: 座標計算をすべて Python 側に置くため、ブラウザ側のインタラクティブなレイアウト調整（ドラッグ等）はオーバーライドという別経路 (ADR-02) を必要とし、「自動レイアウト結果そのものをブラウザ側で再計算する」ような設計は取れない。これは意図した制約であり、ADR-02 の前提でもある。
