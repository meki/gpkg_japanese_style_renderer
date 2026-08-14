import { defineConfig } from "vitest/config";

// editing/ 配下の純粋な TS ロジック (オーバーライド適用・コマンドスタック) の
// ユニットテスト用。DOM 操作を伴わないため environment は node のままでよい。
export default defineConfig({
  test: {
    include: ["src/**/*.test.ts"],
  },
});
