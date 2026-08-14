import type { LayoutResult } from "../types/layout";
import { DEFAULT_DISPLAY_OPTIONS, type DisplayOptions } from "../types/displayOptions";
import { ConnectorLayer } from "./ConnectorLayer";
import { computePixelSize, UNIT_PX } from "./layoutConstants";
import { VerticalNode } from "./VerticalNode";

interface FamilyTreeCanvasProps {
  layout: LayoutResult;
  projectId: string;
  zoom: number;
  displayOptions?: DisplayOptions;
  onNodeDragEnd?: (handle: string, x: number, y: number) => void;
  collapsibleHandles?: ReadonlySet<string>;
  collapsedHandles?: ReadonlySet<string>;
  onToggleCollapse?: (handle: string) => void;
}

export function FamilyTreeCanvas({
  layout,
  projectId,
  zoom,
  displayOptions = DEFAULT_DISPLAY_OPTIONS,
  onNodeDragEnd = () => {},
  collapsibleHandles,
  collapsedHandles,
  onToggleCollapse = () => {},
}: FamilyTreeCanvasProps) {
  const allNodes = [...layout.nodes, ...layout.auxiliary_nodes];
  const maxX = Math.max(0, ...allNodes.map((n) => n.x + n.width));
  const { width: pixelWidth, height: pixelHeight } = computePixelSize(layout);

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
          zoom={zoom}
          projectId={projectId}
          totalWidth={maxX}
          displayOptions={displayOptions}
          onDragEnd={onNodeDragEnd}
          isCollapsible={collapsibleHandles?.has(node.handle) ?? false}
          isCollapsed={collapsedHandles?.has(node.handle) ?? false}
          onToggleCollapse={onToggleCollapse}
        />
      ))}
    </div>
  );
}
