import type { LayoutResult } from "../types/layout";
import { DEFAULT_DISPLAY_OPTIONS, type DisplayOptions } from "../types/displayOptions";
import { ConnectorLayer } from "./ConnectorLayer";
import { buildNodeIndex, buildVisualNodeIndex, computeMarriageSides } from "./connectorGeometry";
import type { RevealAnchor } from "../editing/revealAnchors";
import { computePixelSize, UNIT_PX } from "./layoutConstants";
import { RevealHandle } from "./RevealHandle";
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
  onHideNode?: (handle: string) => void;
  revealAnchors?: RevealAnchor[];
  onRevealNodes?: (handles: string[]) => void;
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
  onHideNode = () => {},
  revealAnchors = [],
  onRevealNodes = () => {},
}: FamilyTreeCanvasProps) {
  const allNodes = [...layout.nodes, ...layout.auxiliary_nodes];
  const maxX = Math.max(0, ...allNodes.map((n) => n.x + n.width));
  const { width: pixelWidth, height: pixelHeight } = computePixelSize(layout);
  // 生没年列は婚姻線と反対側に配置する (婚姻線が右にあるノードは生没年を
  // 左に出す)。手動でのノード移動後の現在位置から都度計算する。
  const marriageSides = computeMarriageSides(layout, buildNodeIndex(layout));
  // 再表示ハンドル (RQ-05-10) の位置は、接続線と同じく「実際に画面へ描画
  // されるボックス位置」(生没年列との左右入れ替え補正込み) から計算する。
  const visualNodeByHandle = buildVisualNodeIndex(layout, marriageSides);
  const mirror = (x: number) => (maxX - x) * UNIT_PX;

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
          dateSide={marriageSides.get(node.handle) === "right" ? "left" : "right"}
          onDragEnd={onNodeDragEnd}
          isCollapsible={collapsibleHandles?.has(node.handle) ?? false}
          isCollapsed={collapsedHandles?.has(node.handle) ?? false}
          onToggleCollapse={onToggleCollapse}
          onHideNode={onHideNode}
        />
      ))}
      {revealAnchors.map((anchor) => {
        const anchorNode = visualNodeByHandle.get(anchor.anchorHandle);
        if (!anchorNode) return null;
        const left = mirror(anchorNode.x + anchorNode.width);
        const right = mirror(anchorNode.x);
        const top = anchorNode.y * UNIT_PX;
        const bottom = (anchorNode.y + anchorNode.height) * UNIT_PX;
        return (
          <RevealHandle
            key={anchor.key}
            anchor={anchor}
            box={{ left, top, right, bottom }}
            onReveal={onRevealNodes}
          />
        );
      })}
    </div>
  );
}
