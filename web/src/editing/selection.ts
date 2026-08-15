// 右クリックドラッグによる矩形選択と、選択中ノードのまとめ移動 (RQ-05-11)。
// Viewport.tsx / App.tsx から呼ばれる純粋関数として切り出し、DOM や
// React の状態に依存せずテストできるようにする。

import { buildNodeIndex, buildVisualNodeIndex, computeMarriageSides } from "../canvas/connectorGeometry";
import { UNIT_PX } from "../canvas/layoutConstants";
import type { LayoutResult, PersonNode } from "../types/layout";

export interface SelectionRect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

/**
 * 選択矩形 (viewport__content 基準、ノードと同じ座標系) と交差する全ノードの
 * handle を返す。生没年列との左右入れ替え補正込みの「実際に画面へ描画される
 * ボックス位置」で判定する (接続線・再表示ハンドルと同じ考え方)。
 */
export function computeSelectedHandles(layout: LayoutResult, rect: SelectionRect): Set<string> {
  const allNodes = [...layout.nodes, ...layout.auxiliary_nodes];
  const maxX = Math.max(0, ...allNodes.map((n) => n.x + n.width));
  const marriageSides = computeMarriageSides(layout, buildNodeIndex(layout));
  const visualNodeByHandle = buildVisualNodeIndex(layout, marriageSides);
  const mirror = (x: number) => (maxX - x) * UNIT_PX;

  const selected = new Set<string>();
  for (const node of allNodes) {
    const visual = visualNodeByHandle.get(node.handle) ?? node;
    const left = mirror(visual.x + visual.width);
    const right = mirror(visual.x);
    const top = visual.y * UNIT_PX;
    const bottom = (visual.y + visual.height) * UNIT_PX;
    const intersects = !(right < rect.left || left > rect.right || bottom < rect.top || top > rect.bottom);
    if (intersects) selected.add(node.handle);
  }
  return selected;
}

/**
 * 選択中のノード群 (targets) それぞれの現在位置 (nodeByHandle、オーバーライド
 * 適用後の displayLayout 由来) に、同じ抽象座標の差分 (deltaX, deltaY) を
 * 適用した新しい位置を返す。VerticalNode.tsx の単一ノードドラッグと同じ
 * 符号規約 (画面上は左右反転しているため x は減算) に従う。
 */
export function computeGroupMove(
  nodeByHandle: ReadonlyMap<string, PersonNode>,
  targets: ReadonlySet<string>,
  deltaX: number,
  deltaY: number,
): Record<string, { x: number; y: number }> {
  const result: Record<string, { x: number; y: number }> = {};
  for (const handle of targets) {
    const node = nodeByHandle.get(handle);
    if (!node) continue;
    result[handle] = { x: node.x - deltaX, y: node.y + deltaY };
  }
  return result;
}
