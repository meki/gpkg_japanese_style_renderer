// 婚姻線・親子接続線・生没年列の左右配置を「現在のノード位置」から都度計算する
// ための共有ロジック。オーバーライド (手動でのノード移動) 適用後の LayoutResult
// を受け取ることを前提とし、レイアウト計算時点の静的な座標
// (MarriageEdge.y, ChildEdge.points) には依存しない。依存すると、ノードを
// ドラッグで動かしても接続線だけが古い位置に取り残されてしまう
// (実データでの目視確認で発覚した不具合)。

import type { LayoutResult, PersonNode } from "../types/layout";

export function buildNodeIndex(layout: LayoutResult): Map<string, PersonNode> {
  const index = new Map<string, PersonNode>();
  for (const node of [...layout.nodes, ...layout.auxiliary_nodes]) {
    index.set(node.handle, node);
  }
  return index;
}

/**
 * 2 つのノードのうち互いに向き合う端 (抽象座標) を返す。
 *
 * 中心同士を結ぶと線が両方のボックスの内側まで伸びてしまうため、実際に
 * 隣接するボックスの端同士を結ぶ。abstract x が小さい方が画面上「右」に
 * 来る (RQ-02-03) ため、小さい方の abstract 右端・大きい方の abstract 左端が
 * 向かい合う。
 */
export function facingEdges(a: PersonNode, b: PersonNode): [number, number] {
  const [rightSide, leftSide] = a.x <= b.x ? [a, b] : [b, a];
  return [rightSide.x + rightSide.width, leftSide.x];
}

export function marriageEdgeY(husband: PersonNode, wife: PersonNode): number {
  const commonHeight = Math.min(husband.height, wife.height);
  return Math.min(husband.y, wife.y) + commonHeight / 2;
}

/**
 * 各人物について、婚姻線が画面上どちら側にあるかを返す (該当する婚姻が
 * なければ未設定)。生没年列を婚姻線と反対側に配置するために使う。
 */
export function computeMarriageSides(
  layout: LayoutResult,
  nodeByHandle: Map<string, PersonNode>,
): Map<string, "left" | "right"> {
  const sides = new Map<string, "left" | "right">();
  for (const edge of layout.marriage_edges) {
    const husband = nodeByHandle.get(edge.husband_handle);
    const wife = nodeByHandle.get(edge.wife_handle);
    if (!husband || !wife) continue;
    if (husband.x <= wife.x) {
      sides.set(husband.handle, "left");
      sides.set(wife.handle, "right");
    } else {
      sides.set(husband.handle, "right");
      sides.set(wife.handle, "left");
    }
  }
  return sides;
}

/**
 * 生没年列とボックスの左右を入れ替えた (dateSide==="left" の) 人物は、
 * VerticalNode.tsx がボックス本体を画面上 date_column_width 分だけ
 * セル内でずらして描画する (生没年列をセルの外側/元のボックス位置に出す
 * ため)。接続線はこの「実際に描画されるボックス位置」に合わせる必要が
 * あるため、該当ノードの abstract x を同じ量だけ補正したノード集合を返す。
 * (補正しないと、婚姻線が反対側にずれたボックスまで届かず隙間ができる。)
 */
export function buildVisualNodeIndex(
  layout: LayoutResult,
  marriageSides: Map<string, "left" | "right">,
): Map<string, PersonNode> {
  const raw = buildNodeIndex(layout);
  const visual = new Map<string, PersonNode>();
  for (const [handle, node] of raw) {
    const dateSide = marriageSides.get(handle) === "right" ? "left" : "right";
    if (dateSide === "left" && node.date_column_width > 0) {
      visual.set(handle, { ...node, x: node.x - node.date_column_width });
    } else {
      visual.set(handle, node);
    }
  }
  return visual;
}

export interface ChildEdgeGeometry {
  points: [number, number][];
}

/**
 * 親子接続線を現在のノード位置から計算する。両親がそろっていれば夫婦連結線
 * の中点相当を、単親であればその人物自身の下端中央を始点とする。
 */
export function computeChildEdgeGeometry(
  parentHandles: string[],
  childHandle: string,
  nodeByHandle: Map<string, PersonNode>,
): ChildEdgeGeometry | null {
  const child = nodeByHandle.get(childHandle);
  if (!child) return null;
  const parents = parentHandles
    .map((h) => nodeByHandle.get(h))
    .filter((n): n is PersonNode => n !== undefined);
  if (parents.length === 0) return null;

  let startX: number;
  let startY: number;
  if (parents.length >= 2) {
    const [a, b] = parents;
    const [edgeA, edgeB] = facingEdges(a, b);
    startX = (edgeA + edgeB) / 2;
    startY = marriageEdgeY(a, b);
  } else {
    const solo = parents[0];
    startX = solo.x + solo.width / 2;
    // 単親の場合、線は frame の下端ではなく (顔写真があれば) その下端から
    // 降ろす。顔写真は frame の直後に挟んで描画するため (engine.py と同じ)。
    startY = solo.y + solo.height + solo.photo_height;
  }

  const childX = child.x + child.width / 2;
  const childTop = child.y;
  const barY = startY + (childTop - startY) / 2;

  return {
    points: [
      [startX, startY],
      [startX, barY],
      [childX, barY],
      [childX, childTop],
    ],
  };
}
