# API 仕様

本書は FastAPI バックエンドが提供する HTTP API を定義する。すべてのエンドポイントはローカルホスト (`127.0.0.1`) でのみ待受し (SP-08-01)、認証は設けない（単一利用者のローカル実行を前提とするため）。ペイロードのスキーマは [12_specifications-data_format.md](12_specifications-data_format.md) を参照。

## 共通事項

### ベース URL とバージョニング

**UID**: API-00-01 \
**STATUS**: Active

すべてのエンドポイントは `/api/v1` を prefix とする。破壊的変更を行う場合は prefix のバージョンを上げ、旧バージョンとの共存期間は設けない（単一利用者向けローカルアプリのため）。

### エラー応答形式

**UID**: API-00-02 \
**STATUS**: Active

エラー時は HTTP ステータスコードに加え、以下の形式の JSON を返す。

```json
{
  "error": {
    "code": "GPKG_PARSE_FAILED",
    "message": "data.gramps が見つかりません(.gpkg として不正な可能性)"
  }
}
```

`code` は機械可読な識別子（スネークケース禁止・定数的な英大文字＋アンダースコア）とし、クライアント側の分岐に用いる。`message` は開発者向けの詳細であり、ユーザー向け文言への変換は UI 層 (SP-13) の責務とする。

## プロジェクト管理

### gpkg のアップロード

**UID**: API-01-01 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-01-01

`POST /api/v1/projects` — `multipart/form-data` で `.gpkg` ファイルを受け取り、サーバ側の一時領域に展開して `GrampsDatabase` を構築する。成功時は `201 Created` で `{"project_id": "...", "summary": {"people": 136, "families": 46, ...}}` を返す。パース失敗時は `422 Unprocessable Entity` かつ `code: GPKG_PARSE_FAILED`。

### プロジェクト一覧

**UID**: API-01-02 \
**STATUS**: Active

`GET /api/v1/projects` — サーバプロセス起動後にアップロードされたプロジェクトの一覧を返す。永続化はしない（プロセス再起動でクリアされる）。永続的な保存は SP-05-04 のプロジェクト保存 API (API-04) で別途行う。

### プロジェクトの破棄

**UID**: API-01-03 \
**STATUS**: Active

`DELETE /api/v1/projects/{project_id}` — サーバ側の一時領域を解放する。破棄操作は UI 側で確認を要する破壊的操作として扱う ([13_user_interface_requirements.md](13_user_interface_requirements.md))。

## レイアウト

### レイアウトの取得

**UID**: API-02-01 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-05-01
- **Type**: Parent
  **ID**: RQ-05-04

`GET /api/v1/projects/{project_id}/layout` — クエリパラメータ `root_handle`（省略時は全人物）、`direction`（`ancestors`|`descendants`|`both`）を受け取り、`LayoutResult` (SP-05-01, SP-02) を計算して返す。この応答はベースラインであり、クライアント側のオーバーライドは含まない。

**Phase 3 時点の実装範囲**: `layout.engine.build_layout` は単一起点からの子孫方向レイアウトのみに対応しており、`root_handle` は現状必須（省略時は `422 ROOT_HANDLE_REQUIRED`）。`direction`（祖先方向・両方向）のクエリパラメータは未実装。「省略時は全人物」(RQ-05-01) と枝の表示/非表示 (RQ-05-02, SP-05-01 の到達可能集合計算は Phase 1 で実装済み) を用いた `direction` 対応は、対話編集を実装する Phase 4 で拡張する。

### 人物一覧の取得

**UID**: API-02-02 \
**STATUS**: Active

`GET /api/v1/projects/{project_id}/people` — 起点人物選択 UI (RQ-05-03) 向けに、`handle`・表示名・生没年のみの軽量な一覧を返す。

## メディア

### 顔写真の取得

**UID**: API-03-01 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-03-07

`GET /api/v1/projects/{project_id}/media/{object_handle}` — `MediaObject` の実データをそのまま `mime` に応じた `Content-Type` でストリーミング返却する。存在しない `object_handle` は `404 Not Found`。

### 人物の顔写真の取得

**UID**: API-03-02 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-03-07
- **Type**: Parent
  **ID**: DF-01-03

`GET /api/v1/projects/{project_id}/people/{person_handle}/photo` — `PersonView.has_photo` (DF-01-03) は写真の有無のみを示し、対応する `MediaObject` の `object_handle` を含まない。フロントエンドが `object_handle` を知らなくても表示できるよう、人物 handle から `GrampsDatabase.photo_bytes()` (先頭の `objref` を解決) で直接取得する経路を別途用意する。レスポンス形式は API-03-01 と同じ。写真が無い人物、または `object_handle` は存在するが実バイト列が取得できない場合は `404 Not Found`。

## プロジェクト保存（編集内容の永続化）

### 保存データの書き出し

**UID**: API-04-01 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-05-08

`GET /api/v1/projects/{project_id}/document` — オーバーライド・スタイル設定・標題設定を含む保存用 JSON ([12_specifications-data_format.md](12_specifications-data_format.md) の `ProjectDocument`) を返す。クライアントはこれをブラウザのファイル保存ダイアログでローカルディスクへ保存する（サーバ側でファイルシステムへ永続化はしない）。

### 保存データの読み込み

**UID**: API-04-02 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-05-08

`PUT /api/v1/projects/{project_id}/document` — クライアントが読み込んだ `ProjectDocument` をサーバのプロジェクト状態に適用する。`gpkg` フィンガープリントが現在ロード中のファイルと一致しない場合は `409 Conflict` を返し、UI 側で警告のうえ利用者に続行可否を確認させる。

**Phase 4 時点の実装範囲**: サーバ (`api/store.py`) はオーバーライド・表示設定・標題設定のいずれも保持しない、レイアウト計算専用のステートレスな存在として実装した (`ProjectState` が持つのは `db` と `lineage_surnames` のみ)。そのため API-04-01/04-02 の「サーバのプロジェクト状態に保存/適用する」という設計はそのままでは意味を持たず、保存・読込は **サーバを経由せずクライアント (`web/src/App.tsx`) 内で完結**させている: 保存はブラウザの `Blob` + `<a download>` でローカルディスクへ直接書き出し、読込は `<input type="file">` で読んだ JSON を React state へ直接反映する。`gpkg` フィンガープリントによる厳密な一致確認 (409 Conflict 相当) も未実装で、読み込んだ `root_handle` がアップロード中の gpkg に存在しない場合は `GET .../layout` が返す `404 PERSON_NOT_FOUND` がそのままエラー表示される簡略動作に留める。API-04-01/04-02 のサーバエンドポイントは、複数クライアント間でプロジェクト状態を共有する必要が生じた場合に見直す。

## 出力

### 系統分割済みレイアウトの取得

**UID**: API-05-01 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-07-03

`GET /api/v1/projects/{project_id}/layout/segments` — 分割起点人物の一覧をクエリで受け取り、系統ごとの `LayoutResult` 配列を返す (SP-07-03)。

### A4 タイル割付の取得

**UID**: API-05-02 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-07-04

`GET /api/v1/projects/{project_id}/layout/tiles` — 用紙サイズ・倍率・のりしろ幅をクエリで受け取り、`TilePage` 配列 ([12_specifications-data_format.md](12_specifications-data_format.md)) を返す。実際の PDF/PNG 化はクライアント側の印刷・エクスポート機能 (SP-07-05) が担う。
