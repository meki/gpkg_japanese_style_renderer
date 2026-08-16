# gpkg Japanese Style Renderer

Gramps のエクスポートファイル (`.gpkg`) を、日本の伝統的な家系図の様式（縦書き・続柄・和暦など）でレンダリングするローカル Web アプリ。

詳細な要件・仕様・アーキテクチャは [docs/](docs/) を参照。特に開発に着手する前に [docs/90_Onboarding.md](docs/90_Onboarding.md) を読むこと。

## セットアップ

バックエンド (Python) は [uv](https://docs.astral.sh/uv/)、フロントエンド (`web/`) は npm を使用する。

```bash
uv sync
cd web && npm install
```

## 開発サーバの起動

```bash
uv run uvicorn gpkg_jsr.api.app:app --reload --port 8001
```

```bash
cd web && npm run dev
```

## ローカル CI 相当の検証コマンド

コード変更後は、コミット前に以下をすべて実行する。

```bash
uv run pytest
uv run ruff check .
uv run mypy src tests
```

```bash
cd web && npx tsc -b && npm run lint && npm run build
```

GitHub Actions の PR CI (`.github/workflows/ci.yml`) でも、上記の Python・フロントエンド検証と `web` のテスト、`docs/` の StrictDoc 検証を実行する。

## 要件・仕様ドキュメントの検証

`docs/` 配下は [StrictDoc](https://strictdoc.readthedocs.io/) 形式 (Markdown ベース) で記述している。パース検証・HTML 出力は以下で行う。

```bash
uv run strictdoc export docs --formats=html --output-dir /tmp/strictdoc-out
```
