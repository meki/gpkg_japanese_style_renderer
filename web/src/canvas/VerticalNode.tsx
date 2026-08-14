import { useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { PersonNode } from "../types/layout";
import type { DisplayOptions } from "../types/displayOptions";
import { personPhotoUrl } from "../api/client";
import "./VerticalNode.css";

interface DragOffsetPx {
  dx: number;
  dy: number;
}

interface VerticalNodeProps {
  node: PersonNode;
  scale: number;
  zoom: number;
  projectId: string;
  /**
   * 抽象座標系での全体幅 (単位)。x=0 が画面上「最も右」に来るよう、ここで
   * 左右反転する (RQ-02-03: 年長者を右に配置。layout/types.ts の docstring
   * および Python 側 layout/types.py の docstring を参照)。
   */
  totalWidth: number;
  displayOptions: DisplayOptions;
  onDragEnd: (handle: string, x: number, y: number) => void;
  isCollapsible: boolean;
  isCollapsed: boolean;
  onToggleCollapse: (handle: string) => void;
}

export function VerticalNode({
  node,
  scale,
  zoom,
  projectId,
  totalWidth,
  displayOptions,
  onDragEnd,
  isCollapsible,
  isCollapsed,
  onToggleCollapse,
}: VerticalNodeProps) {
  const { view } = node;
  const classNames = ["vertical-node"];
  if (view.is_deceased) classNames.push("vertical-node--deceased");
  if (view.is_focus_person) classNames.push("vertical-node--focus");
  if (view.is_spouse_in) classNames.push("vertical-node--spouse-in");
  if (!displayOptions.showFrame) classNames.push("vertical-node--no-frame");

  const [dragOffsetPx, setDragOffsetPx] = useState<DragOffsetPx | null>(null);
  const dragStart = useRef<{ clientX: number; clientY: number } | null>(null);
  // pointerup は pointermove の setDragOffsetPx が反映される前 (同一タスク内)
  // に発火しうる (state 更新は非同期でバッチされるため、直前の state を読む
  // クロージャが古いままになりうる)。確定時の値は常に同期的に最新の ref から
  // 読み、dragOffsetPx (state) は描画用のプレビューにのみ使う。
  const latestOffsetPx = useRef<DragOffsetPx>({ dx: 0, dy: 0 });

  function handlePointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    event.stopPropagation(); // Viewport 側のパン操作を発火させない
    (event.target as HTMLElement).setPointerCapture(event.pointerId);
    dragStart.current = { clientX: event.clientX, clientY: event.clientY };
    latestOffsetPx.current = { dx: 0, dy: 0 };
    setDragOffsetPx({ dx: 0, dy: 0 });
  }

  function handlePointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    if (!dragStart.current) return;
    const offset = {
      dx: event.clientX - dragStart.current.clientX,
      dy: event.clientY - dragStart.current.clientY,
    };
    latestOffsetPx.current = offset;
    setDragOffsetPx(offset);
  }

  function handlePointerUp(event: ReactPointerEvent<HTMLDivElement>) {
    event.stopPropagation();
    if (!dragStart.current) return;
    dragStart.current = null;
    const offset = latestOffsetPx.current;
    setDragOffsetPx(null);
    const unitDx = offset.dx / (scale * zoom);
    const unitDy = offset.dy / (scale * zoom);
    // 画面上は左右反転しているため (totalWidth - x)、右へのドラッグは x を減らす。
    if (unitDx !== 0 || unitDy !== 0) {
      onDragEnd(node.handle, node.x - unitDx, node.y + unitDy);
    }
  }

  const displayLeft = (totalWidth - node.x - node.width) * scale + (dragOffsetPx?.dx ?? 0);
  const displayTop = node.y * scale + (dragOffsetPx?.dy ?? 0);
  const frameWidthPx = node.width * scale;
  const dateColumnWidthPx = node.date_column_width * scale;
  const showDates =
    displayOptions.showDates &&
    dateColumnWidthPx > 0 &&
    (view.birth_date_display || view.death_date_display);

  return (
    <>
      <div
        className={classNames.join(" ") + (dragOffsetPx ? " vertical-node--dragging" : "")}
        style={{
          left: displayLeft,
          top: displayTop,
          width: frameWidthPx,
          height: node.height * scale,
        }}
        title={view.notes.join("\n") || undefined}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      >
        <div className="vertical-node__name">
          {displayOptions.showFormerSurname && view.former_surname && (
            <span className="vertical-node__former-surname">({view.former_surname})</span>
          )}
          <ruby>
            {view.surname}
            {displayOptions.showRuby && view.surname_kana && <rt>{view.surname_kana}</rt>}
          </ruby>
          <ruby>
            {view.given_name}
            {displayOptions.showRuby && view.given_name_kana && <rt>{view.given_name_kana}</rt>}
          </ruby>
        </div>
        {displayOptions.showBirthOrder && view.birth_order_label && (
          <span className="vertical-node__label">{view.birth_order_label}</span>
        )}
        {displayOptions.showPhotos && view.has_photo && (
          <img
            className="vertical-node__photo"
            src={personPhotoUrl(projectId, node.handle)}
            alt=""
          />
        )}
        {isCollapsible && (
          <button
            type="button"
            className="vertical-node__collapse-toggle"
            title={isCollapsed ? "枝を展開" : "枝を折りたたむ"}
            onPointerDown={(event) => event.stopPropagation()}
            onClick={(event) => {
              event.stopPropagation();
              onToggleCollapse(node.handle);
            }}
          >
            {isCollapsed ? "+" : "−"}
          </button>
        )}
      </div>
      {showDates && (
        <div
          className="vertical-node__date-column"
          style={{
            left: displayLeft + frameWidthPx,
            top: displayTop,
            width: dateColumnWidthPx,
          }}
        >
          {view.birth_date_display && <span>{view.birth_date_display.text}</span>}
          {view.death_date_display && <span>{view.death_date_display.text}</span>}
        </div>
      )}
    </>
  );
}
