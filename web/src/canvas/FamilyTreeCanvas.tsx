import type { LayoutResult } from "../types/layout";
import { ConnectorLayer } from "./ConnectorLayer";
import { VerticalNode } from "./VerticalNode";

// 抽象座標系の 1 単位あたりの px 数。ADR-01: フォント実測ではなく文字数ベースの
// 近似のため、正確なグリフ幅との厳密な一致は期待しない (Phase 6 で調整)。
const UNIT_PX = 32;

interface FamilyTreeCanvasProps {
  layout: LayoutResult;
  projectId: string;
}

export function FamilyTreeCanvas({ layout, projectId }: FamilyTreeCanvasProps) {
  const allNodes = [...layout.nodes, ...layout.auxiliary_nodes];
  const maxX = Math.max(0, ...allNodes.map((n) => n.x + n.width));
  const maxY = Math.max(0, ...allNodes.map((n) => n.y + n.height));
  const pixelWidth = maxX * UNIT_PX;
  const pixelHeight = maxY * UNIT_PX;

  return (
    <div
      className="family-tree-canvas"
      style={{ position: "relative", width: pixelWidth, height: pixelHeight }}
    >
      <ConnectorLayer
        layout={layout}
        scale={UNIT_PX}
        width={pixelWidth}
        height={pixelHeight}
        totalWidth={maxX}
      />
      {allNodes.map((node) => (
        <VerticalNode
          key={node.handle}
          node={node}
          scale={UNIT_PX}
          projectId={projectId}
          totalWidth={maxX}
        />
      ))}
    </div>
  );
}
