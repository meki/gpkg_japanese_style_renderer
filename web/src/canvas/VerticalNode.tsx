import { useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { PersonNode } from "../types/layout";
import type { DisplayOptions } from "../types/displayOptions";
import { personPhotoUrl } from "../api/client";
import "./VerticalNode.css";

export interface DragOffsetPx {
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
  /**
   * 生没年列をボックスのどちら側 (画面表示) に出すか。婚姻線が接続する側と
   * 反対側に出すことで、生没年テキストと婚姻線の重なりを避ける
   * (FamilyTreeCanvas.tsx の computeMarriageSides を参照)。
   */
  dateSide: "left" | "right";
  /** ドラッグ終了時、画面ピクセルの移動量を抽象座標の差分に変換して渡す
   *  (絶対座標ではなく差分)。複数ノードのまとめ選択 (RQ-05-11) 時に、
   *  選択中の全ノードへ同じ差分を適用して一括移動できるようにするため。 */
  onDragEnd: (handle: string, deltaX: number, deltaY: number) => void;
  /** ドラッグ中に (確定前の) 画面ピクセル移動量を都度通知する。選択中の
   *  他ノードのプレビュー表示 (groupPreviewOffsetPx) を駆動するために使う。 */
  onDragMove?: (handle: string, offsetPx: DragOffsetPx | null) => void;
  isCollapsible: boolean;
  isCollapsed: boolean;
  onToggleCollapse: (handle: string) => void;
  /** このノード単体を非表示にする (RQ-05-10)。婚姻線・親子接続線は
   *  applyOverrides 側で自動的に連動して非表示になる。 */
  onHideNode: (handle: string) => void;
  /** 右クリックドラッグによる矩形選択で選ばれているか (RQ-05-11)。 */
  isSelected?: boolean;
  /** 自分は物理的にドラッグされていないが、選択グループの一員として
   *  他ノードのドラッグに追従してプレビュー表示すべき画面ピクセル差分。 */
  groupPreviewOffsetPx?: DragOffsetPx | null;
}

export function VerticalNode({
  node,
  scale,
  zoom,
  projectId,
  totalWidth,
  displayOptions,
  dateSide,
  onDragEnd,
  onDragMove,
  isCollapsible,
  isCollapsed,
  onToggleCollapse,
  onHideNode,
  isSelected = false,
  groupPreviewOffsetPx = null,
}: VerticalNodeProps) {
  const { view } = node;
  const classNames = ["vertical-node"];
  if (view.is_deceased) classNames.push("vertical-node--deceased");
  if (view.is_focus_person) classNames.push("vertical-node--focus");
  if (view.is_spouse_in) classNames.push("vertical-node--spouse-in");
  if (!displayOptions.showFrame) classNames.push("vertical-node--no-frame");
  if (isSelected) classNames.push("vertical-node--selected");

  const [dragOffsetPx, setDragOffsetPx] = useState<DragOffsetPx | null>(null);
  const dragStart = useRef<{ clientX: number; clientY: number } | null>(null);
  // pointerup は pointermove の setDragOffsetPx が反映される前 (同一タスク内)
  // に発火しうる (state 更新は非同期でバッチされるため、直前の state を読む
  // クロージャが古いままになりうる)。確定時の値は常に同期的に最新の ref から
  // 読み、dragOffsetPx (state) は描画用のプレビューにのみ使う。
  const latestOffsetPx = useRef<DragOffsetPx>({ dx: 0, dy: 0 });

  function handlePointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return; // 右クリックは Viewport 側の矩形選択に委ねる
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
    onDragMove?.(node.handle, offset);
  }

  function handlePointerUp(event: ReactPointerEvent<HTMLDivElement>) {
    if (!dragStart.current) return;
    event.stopPropagation();
    dragStart.current = null;
    const offset = latestOffsetPx.current;
    setDragOffsetPx(null);
    onDragMove?.(node.handle, null);
    const unitDx = offset.dx / (scale * zoom);
    const unitDy = offset.dy / (scale * zoom);
    // 画面上は左右反転しているため (totalWidth - x)、右へのドラッグは x を減らす。
    if (unitDx !== 0 || unitDy !== 0) {
      onDragEnd(node.handle, unitDx, unitDy);
    }
  }

  // 自分自身が物理的にドラッグ中ならその移動量を、そうでなく選択グループの
  // 一員として他ノードのドラッグに追従する場合は groupPreviewOffsetPx を使う。
  const effectiveOffsetPx = dragOffsetPx ?? groupPreviewOffsetPx ?? null;

  // セル (ボックス + 生没年列) 全体の画面左端。婚姻線が右にある人物は
  // dateSide==="left" となり、セル内でボックスと生没年列の左右を入れ替える
  // (セル全体の footprint は engine.py 側の計算と変えない)。
  const cellDisplayLeft =
    (totalWidth - node.x - node.width) * scale + (effectiveOffsetPx?.dx ?? 0);
  const displayTop = node.y * scale + (effectiveOffsetPx?.dy ?? 0);
  const frameWidthPx = node.width * scale;
  const dateColumnWidthPx = node.date_column_width * scale;
  const showDates =
    displayOptions.showDates &&
    dateColumnWidthPx > 0 &&
    (view.birth_date_display || view.death_date_display);
  const flipped = dateSide === "left";
  const boxDisplayLeft = flipped ? cellDisplayLeft + dateColumnWidthPx : cellDisplayLeft;
  const dateDisplayLeft = flipped ? cellDisplayLeft : cellDisplayLeft + frameWidthPx;
  const frameHeightPx = node.height * scale;
  const photoHeightPx = node.photo_height * scale;
  const showPhoto = displayOptions.showPhotos && view.has_photo && photoHeightPx > 0;

  return (
    <>
      <div
        className={classNames.join(" ") + (effectiveOffsetPx ? " vertical-node--dragging" : "")}
        style={{
          left: boxDisplayLeft,
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
        <button
          type="button"
          className="vertical-node__hide-toggle"
          title="このノードを非表示にする"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={(event) => {
            event.stopPropagation();
            onHideNode(node.handle);
          }}
        >
          <svg viewBox="0 0 16 16" width="10" height="10" aria-hidden="true">
            <path
              d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.3"
            />
            <circle cx="8" cy="8" r="2" fill="currentColor" />
          </svg>
        </button>
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
            left: dateDisplayLeft,
            top: displayTop,
            width: dateColumnWidthPx,
          }}
        >
          {view.birth_date_display && <span>{view.birth_date_display.text}</span>}
          {view.death_date_display && <span>{view.death_date_display.text}</span>}
        </div>
      )}
      {showPhoto && (
        <div
          className="vertical-node__photo-column"
          style={{
            left: boxDisplayLeft,
            top: displayTop + frameHeightPx,
            width: frameWidthPx,
            height: photoHeightPx,
          }}
        >
          <img src={personPhotoUrl(projectId, node.handle)} alt="" />
        </div>
      )}
    </>
  );
}
