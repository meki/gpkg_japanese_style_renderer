# gpkg Japanese Style Renderer — フロントエンド

Vite + React + TypeScript。バックエンド (FastAPI) との役割分担・座標系の規約は
[../docs/20_architecture.md](../docs/20_architecture.md) の AD-01、開発環境の
セットアップは [../docs/90_Onboarding.md](../docs/90_Onboarding.md) を参照。

## セットアップと起動

バックエンド (`uv run uvicorn gpkg_jsr.api.app:app --reload --port 8001`、リポジトリ
ルートで実行) を先に起動してから、以下を実行する。

```bash
npm install
npm run dev
```

`vite.config.ts` の dev サーバプロキシにより、`/api` へのリクエストは
`http://127.0.0.1:8001` へ転送される。ポート 8000 は環境によって VS Code 等の
他プロセスに使われていることがあるため 8001 を既定にしている
(`WinError 10013` 等でバックエンドが起動しない場合はポートの競合を疑うこと)。

## 検証コマンド

```bash
npx tsc -b       # 型チェック
npm run lint     # oxlint
npm run build    # 本番ビルド (型チェック + vite build)
```
