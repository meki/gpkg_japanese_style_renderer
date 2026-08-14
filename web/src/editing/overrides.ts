// オーバーライドレイヤー (SP-05-02, DF-03-04, ADR-02)。
//
// 自動レイアウト結果 (LayoutResult) を不変のベースラインとして扱い、
// ユーザー編集は handle -> 差分のオーバーライドとして別レイヤに保持する。
// 描画時にベースラインへオーバーライドを適用して最終表示を得る。これにより
// 「自動レイアウトの再実行」(RQ-05-04) とオーバーライドの独立した保持
// (RQ-05-07) を両立する。

import type { LayoutResult, PersonNode } from "../types/layout";

export interface NodePosition {
  x: number;
  y: number;
}

export interface Overrides {
  node_positions: Record<string, NodePosition>;
  hidden_handles: string[];
}

export function createEmptyOverrides(): Overrides {
  return { node_positions: {}, hidden_handles: [] };
}

function withPositionOverride(node: PersonNode, overrides: Overrides): PersonNode {
  const position = overrides.node_positions[node.handle];
  if (!position) return node;
  return { ...node, x: position.x, y: position.y };
}

/** ベースラインの LayoutResult にオーバーライドを適用した表示用 LayoutResult を返す。 */
export function applyOverrides(layout: LayoutResult, overrides: Overrides): LayoutResult {
  const hidden = new Set(overrides.hidden_handles);

  const nodes = layout.nodes
    .filter((node) => !hidden.has(node.handle))
    .map((node) => withPositionOverride(node, overrides));
  const auxiliaryNodes = layout.auxiliary_nodes
    .filter((node) => !hidden.has(node.handle))
    .map((node) => withPositionOverride(node, overrides));

  const visible = new Set([...nodes, ...auxiliaryNodes].map((node) => node.handle));

  const marriageEdges = layout.marriage_edges.filter(
    (edge) => visible.has(edge.husband_handle) && visible.has(edge.wife_handle),
  );
  const childEdges = layout.child_edges.filter((edge) => visible.has(edge.child_handle));

  return {
    ...layout,
    nodes,
    auxiliary_nodes: auxiliaryNodes,
    marriage_edges: marriageEdges,
    child_edges: childEdges,
  };
}

/**
 * `child_edges[].parent_handles` から親→子の隣接リストを構築する (DF-01-04)。
 * `marriage_edges` は両親がそろっている family にしか存在しないため、単親家庭
 * も正しく辿れるようこちらを使う。
 */
function buildChildrenMap(layout: LayoutResult): Map<string, string[]> {
  const childrenOf = new Map<string, string[]>();
  for (const edge of layout.child_edges) {
    for (const parent of edge.parent_handles) {
      const list = childrenOf.get(parent) ?? [];
      list.push(edge.child_handle);
      childrenOf.set(parent, list);
    }
  }
  return childrenOf;
}

/** handle を起点とする子孫全員 (handle 自身は含まない) の handle 一覧を返す (SP-05-01 相当)。 */
export function descendantsOf(layout: LayoutResult, handle: string): string[] {
  const childrenOf = buildChildrenMap(layout);
  const result: string[] = [];
  const visited = new Set<string>([handle]);
  const queue = [...(childrenOf.get(handle) ?? [])];
  while (queue.length > 0) {
    const current = queue.shift() as string;
    if (visited.has(current)) continue;
    visited.add(current);
    result.push(current);
    queue.push(...(childrenOf.get(current) ?? []));
  }
  return result;
}
