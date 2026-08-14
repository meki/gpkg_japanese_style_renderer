// SVG 出力 (SP-07-06)。
//
// ノードは HTML (writing-mode + <ruby>) で描画しているため、ネイティブな SVG
// 要素だけでは再現できない。<foreignObject> で家系図 DOM をそのまま SVG に
// 埋め込み、単体の .svg ファイルとして完結させる方式を取る。
//
// PNG 出力は未実装 (90_Onboarding.md を参照): <foreignObject> を含む SVG は
// 内容に関わらず Canvas を "tainted" 状態にし、`canvas.toBlob()` /
// `toDataURL()` がブラウザのセキュリティ制限で失敗することをブラウザでの
// 実地検証で確認した (フォント埋め込み・写真 <img> を取り除いても再現する
// ため、外部リソース参照が原因ではなく foreignObject 自体が原因)。DOM を
// foreignObject を介さず直接 Canvas に描画するライブラリ (html2canvas 等) か、
// サーバ側のヘッドレスブラウザによるラスタライズが必要になる。

/** family-tree-canvas 要素 (DOM) を自己完結した SVG 文字列にシリアライズする。 */
export function serializeChartToSvg(chartElement: HTMLElement): string {
  const width = chartElement.offsetWidth;
  const height = chartElement.offsetHeight;

  const clone = chartElement.cloneNode(true) as HTMLElement;
  // ドラッグ用のポインタハンドラ等は不要。折りたたみボタンも出力には含めない。
  clone.querySelectorAll(".vertical-node__collapse-toggle").forEach((el) => el.remove());

  const inlineStyles = collectStylesheetText();
  const serializer = new XMLSerializer();
  const htmlString = serializer.serializeToString(clone);

  return (
    `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xhtml="http://www.w3.org/1999/xhtml" ` +
    `width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">` +
    `<style>${inlineStyles}</style>` +
    `<foreignObject x="0" y="0" width="${width}" height="${height}">${htmlString}</foreignObject>` +
    `</svg>`
  );
}

function collectStylesheetText(): string {
  const parts: string[] = [];
  for (const sheet of Array.from(document.styleSheets)) {
    try {
      for (const rule of Array.from(sheet.cssRules)) {
        parts.push(rule.cssText);
      }
    } catch {
      // 別オリジンのスタイルシート (フォント CDN 等) は CORS で読めないことが
      // あるが、本アプリはフォントも自己ホストのため通常は発生しない。
    }
  }
  return parts.join("\n");
}

export function downloadSvg(svgText: string, filename: string): void {
  const blob = new Blob([svgText], { type: "image/svg+xml" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
