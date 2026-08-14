// ノード単位の表示・非表示 (RQ-05-10) のための関係グラフ構築。
//
// 再表示ハンドルは「非表示ノードそのもの」ではなく「そのノードに隣接する
// 可視ノード」に取り付けるため、非表示ノードを含む関係 (親・子・配偶者・
// 兄弟) を、非表示状態に関わらず常にたどれる必要がある。オーバーライド
// 適用後の LayoutResult (非表示ノードが除去済み) ではこれができないため、
// 必ずベースライン (baseLayout, 全ノードを含む) に対して使うこと。

import type { LayoutResult, PersonNode } from "../types/layout";

export interface RelationMaps {
  parentsOf: Map<string, string[]>;
  childrenOf: Map<string, string[]>;
  spousesOf: Map<string, string[]>;
  /** 世代内の兄弟グループ。各グループは order_in_generation 昇順 (年長→年少)。 */
  siblingGroups: string[][];
  nodeByHandle: Map<string, PersonNode>;
}

export function buildRelationMaps(layout: LayoutResult): RelationMaps {
  const nodeByHandle = new Map<string, PersonNode>();
  for (const node of [...layout.nodes, ...layout.auxiliary_nodes]) {
    nodeByHandle.set(node.handle, node);
  }

  const parentsOf = new Map<string, string[]>();
  const childrenOf = new Map<string, string[]>();
  const siblingGroupByKey = new Map<string, Set<string>>();

  for (const edge of layout.child_edges) {
    parentsOf.set(edge.child_handle, [...edge.parent_handles]);
    for (const parent of edge.parent_handles) {
      const children = childrenOf.get(parent) ?? [];
      children.push(edge.child_handle);
      childrenOf.set(parent, children);
    }
    const siblingKey = [...edge.parent_handles].sort().join("|");
    const group = siblingGroupByKey.get(siblingKey) ?? new Set<string>();
    group.add(edge.child_handle);
    siblingGroupByKey.set(siblingKey, group);
  }

  const spousesOf = new Map<string, string[]>();
  for (const edge of layout.marriage_edges) {
    const husbandSpouses = spousesOf.get(edge.husband_handle) ?? [];
    husbandSpouses.push(edge.wife_handle);
    spousesOf.set(edge.husband_handle, husbandSpouses);
    const wifeSpouses = spousesOf.get(edge.wife_handle) ?? [];
    wifeSpouses.push(edge.husband_handle);
    spousesOf.set(edge.wife_handle, wifeSpouses);
  }

  const siblingGroups = [...siblingGroupByKey.values()].map((group) =>
    [...group].sort((a, b) => {
      const orderA = nodeByHandle.get(a)?.order_in_generation ?? 0;
      const orderB = nodeByHandle.get(b)?.order_in_generation ?? 0;
      return orderA - orderB;
    }),
  );

  return { parentsOf, childrenOf, spousesOf, siblingGroups, nodeByHandle };
}
