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

function centerX(node: PersonNode): number {
  return node.x + node.width / 2;
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
        return (
          <line
            key={edge.family_handle}
            className="connector-layer__marriage"
            x1={mirror(centerX(husband))}
            y1={y}
            x2={mirror(centerX(wife))}
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
