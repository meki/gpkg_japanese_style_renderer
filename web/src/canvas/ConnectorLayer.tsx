import type { LayoutResult } from "../types/layout";
import {
  buildNodeIndex,
  buildVisualNodeIndex,
  computeChildEdgeGeometry,
  computeMarriageSides,
  facingEdges,
  marriageEdgeY,
} from "./connectorGeometry";
import "./ConnectorLayer.css";

interface ConnectorLayerProps {
  layout: LayoutResult;
  scale: number;
  width: number;
  height: number;
  /** VerticalNode と同じ左右反転を座標に適用するための全体幅 (単位)。 */
  totalWidth: number;
}

export function ConnectorLayer({ layout, scale, width, height, totalWidth }: ConnectorLayerProps) {
  // 生没年列がボックスと左右入れ替わっているノードは、実際に画面へ描画される
  // ボックス位置に合わせて接続線を引く必要があるため、marriageSides から
  // 補正済みの座標 (buildVisualNodeIndex) を使う (VerticalNode.tsx と同じ判定)。
  const marriageSides = computeMarriageSides(layout, buildNodeIndex(layout));
  const nodeByHandle = buildVisualNodeIndex(layout, marriageSides);
  const mirror = (x: number) => (totalWidth - x) * scale;

  return (
    <svg className="connector-layer" width={width} height={height}>
      {layout.marriage_edges.map((edge) => {
        const husband = nodeByHandle.get(edge.husband_handle);
        const wife = nodeByHandle.get(edge.wife_handle);
        if (!husband || !wife) return null;
        const y = marriageEdgeY(husband, wife) * scale;
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
      {layout.child_edges.map((edge, index) => {
        const geometry = computeChildEdgeGeometry(
          edge.parent_handles,
          edge.child_handle,
          nodeByHandle,
        );
        if (!geometry) return null;
        return (
          <polyline
            key={`${edge.family_handle}-${edge.child_handle}-${index}`}
            className={
              edge.relation === "adopted"
                ? "connector-layer__child connector-layer__child--adopted"
                : "connector-layer__child"
            }
            points={geometry.points.map(([x, y]) => `${mirror(x)},${y * scale}`).join(" ")}
          />
        );
      })}
    </svg>
  );
}
