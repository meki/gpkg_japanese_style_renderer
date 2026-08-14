import type { LayoutResult } from "../types/layout";

// 抽象座標系の 1 単位あたりの px 数。ADR-01: フォント実測ではなく文字数ベースの
// 近似のため、正確なグリフ幅との厳密な一致は期待しない (Phase 6 で調整)。
export const UNIT_PX = 32;

export function computePixelSize(layout: LayoutResult): { width: number; height: number } {
  const allNodes = [...layout.nodes, ...layout.auxiliary_nodes];
  const maxX = Math.max(0, ...allNodes.map((n) => n.x + n.width));
  const maxY = Math.max(0, ...allNodes.map((n) => n.y + n.height));
  return { width: maxX * UNIT_PX, height: maxY * UNIT_PX };
}
