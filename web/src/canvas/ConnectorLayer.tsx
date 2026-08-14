import type { LayoutResult, PersonNode } from "../types/layout";
import "./ConnectorLayer.css";

interface ConnectorLayerProps {
  layout: LayoutResult;
  scale: number;
  width: number;
  height: number;
  /** VerticalNode と同じ左右反転を座標に適用するための全体幅 (単位)。 */
  totalWidth: number;
}

/**
 * 2 つのノードのうち互いに向き合う端 (抽象座標) を返す。
 *
 * 婚姻線は中心同士ではなく、実際に隣接するボックスの端同士を結ぶ
 * (中心同士だと線がボックス内部まで伸び、半透明でなくとも見た目上
 * ボックスと重なって見えることが実データでの目視確認で判明した)。
 * abstract x が小さい方が画面上「右」に来る (RQ-02-03) ため、
 * 小さい方の abstract 右端・大きい方の abstract 左端が向かい合う。
 */
function facingEdges(a: PersonNode, b: PersonNode): [number, number] {
  const [rightSide, leftSide] = a.x <= b.x ? [a, b] : [b, a];
  return [rightSide.x + rightSide.width, leftSide.x];
}

export function ConnectorLayer({ layout, scale, width, height, totalWidth }: ConnectorLayerProps) {
  const nodeByHandle = new Map<string, PersonNode>();
  for (const node of [...layout.nodes, ...layout.auxiliary_nodes]) {
    nodeByHandle.set(node.handle, node);
  }
  const mirror = (x: number) => (totalWidth - x) * scale;

  return (
    <svg className="connector-layer" width={width} height={height}>
      {layout.marriage_edges.map((edge) => {
        const husband = nodeByHandle.get(edge.husband_handle);
        const wife = nodeByHandle.get(edge.wife_handle);
        if (!husband || !wife) return null;
        const y = edge.y * scale;
        const [edgeA, edgeB] = facingEdges(husband, wife);
        return (
          <line
            key={edge.family_handle}
            className="connector-layer__marriage"
            x1={mirror(edgeA)}
            y1={y}
            x2={mirror(edgeB)}
            y2={y}
          />
        );
      })}
      {layout.child_edges.map((edge, index) => (
        <polyline
          key={`${edge.family_handle}-${edge.child_handle}-${index}`}
          className={
            edge.relation === "adopted"
              ? "connector-layer__child connector-layer__child--adopted"
              : "connector-layer__child"
          }
          points={edge.points.map(([x, y]) => `${mirror(x)},${y * scale}`).join(" ")}
        />
      ))}
    </svg>
  );
}
