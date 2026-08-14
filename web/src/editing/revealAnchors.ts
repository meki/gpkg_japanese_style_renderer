// ノード単位で非表示にした人物を再表示するための「復帰ハンドル」の位置計算
// (RQ-05-10)。非表示ノードそのものは描画されないため、隣接する可視ノードの
// 縁に短いスタブ+ハンドルを表示し、クリックで非表示ノードを再表示する。

import type { LayoutResult } from "../types/layout";
import { buildRelationMaps } from "./relations";

export type RevealDirection = "up" | "down" | "left" | "right";

export interface RevealAnchor {
  key: string;
  anchorHandle: string;
  direction: RevealDirection;
  targetHandles: string[];
}

/**
 * 可視ノードから見て非表示ノードが画面上どちら側 (left/right) にあるかを、
 * ベースラインの abstract x から判定する。abstract x が小さいほど画面右
 * (RQ-02-03) に描画されるため、visible.x <= other.x なら other は画面左。
 */
function horizontalDirection(visibleX: number, otherX: number): RevealDirection {
  return visibleX <= otherX ? "left" : "right";
}

export function computeRevealAnchors(
  baseLayout: LayoutResult,
  hiddenHandles: ReadonlySet<string>,
): RevealAnchor[] {
  if (hiddenHandles.size === 0) return [];
  const { parentsOf, childrenOf, spousesOf, siblingGroups, nodeByHandle } =
    buildRelationMaps(baseLayout);
  const isVisible = (handle: string) => !hiddenHandles.has(handle) && nodeByHandle.has(handle);

  // (anchorHandle, direction) ごとにまとめる。同じ縁に複数の関係
  // (兄弟・配偶者等) から重複してハンドルが生えるのを避けるため。
  const grouped = new Map<string, RevealAnchor>();
  function addTarget(anchorHandle: string, direction: RevealDirection, targetHandle: string) {
    const key = `${anchorHandle}:${direction}`;
    const existing = grouped.get(key);
    if (existing) {
      if (!existing.targetHandles.includes(targetHandle)) {
        existing.targetHandles.push(targetHandle);
      }
      return;
    }
    grouped.set(key, { key, anchorHandle, direction, targetHandles: [targetHandle] });
  }

  // 親子関係: 可視の子から見て非表示の親は "up"、可視の親から見て非表示の
  // 子は "down"。
  for (const [child, parents] of parentsOf) {
    for (const parent of parents) {
      if (isVisible(child) && hiddenHandles.has(parent)) {
        addTarget(child, "up", parent);
      }
    }
  }
  for (const [parent, children] of childrenOf) {
    for (const child of children) {
      if (isVisible(parent) && hiddenHandles.has(child)) {
        addTarget(parent, "down", child);
      }
    }
  }

  // 配偶者関係: 可視の配偶者から見た非表示配偶者の画面上の左右。
  for (const [handle, spouses] of spousesOf) {
    if (!isVisible(handle)) continue;
    const selfNode = nodeByHandle.get(handle);
    if (!selfNode) continue;
    for (const spouse of spouses) {
      if (!hiddenHandles.has(spouse)) continue;
      const spouseNode = nodeByHandle.get(spouse);
      if (!spouseNode) continue;
      addTarget(handle, horizontalDirection(selfNode.x, spouseNode.x), spouse);
    }
  }

  // 兄弟関係: 世代内で年長→年少に並んだ兄弟のうち、非表示ノードの連続した
  // 塊 (run) を、その両隣の可視な兄弟にハンドルとして割り当てる。塊が
  // グループの端にある場合は、存在する側の隣接可視ノードのみに割り当てる。
  for (const group of siblingGroups) {
    let i = 0;
    while (i < group.length) {
      if (!hiddenHandles.has(group[i])) {
        i += 1;
        continue;
      }
      const runStart = i;
      while (i < group.length && hiddenHandles.has(group[i])) i += 1;
      const run = group.slice(runStart, i);
      const before = runStart > 0 ? group[runStart - 1] : null;
      const after = i < group.length ? group[i] : null;
      if (before && isVisible(before)) {
        for (const handle of run) addTarget(before, "left", handle);
      }
      if (after && isVisible(after)) {
        for (const handle of run) addTarget(after, "right", handle);
      }
    }
  }

  return [...grouped.values()];
}
