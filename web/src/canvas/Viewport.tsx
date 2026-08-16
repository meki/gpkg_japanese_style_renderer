import { useRef, useState, type PointerEvent, type ReactNode, type WheelEvent } from "react";
import "./Viewport.css";

// SP-05-05: ズーム範囲は 25%〜400%。
export const MIN_ZOOM = 0.25;
export const MAX_ZOOM = 4;
const ZOOM_STEP = 0.001;
// これ未満の移動量はドラッグではなくクリックとみなす (px)。
const CLICK_THRESHOLD_PX = 3;

export interface SelectionRect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

interface ViewportProps {
  /**
   * ズーム倍率は親 (App) が状態として持つ制御コンポーネントにする。ノードの
   * ドラッグ移動 (VerticalNode) が画面ピクセルの移動量を抽象座標へ変換する際、
   * 現在のズーム倍率を知る必要があるため (scale * zoom で割る)。
   */
  zoom: number;
  onZoomChange: (zoom: number) => void;
  children: ReactNode;
  /**
   * 右クリックドラッグによる矩形選択が確定したときに呼ばれる。矩形は
   * `.viewport__content` を基準とした変換前 (pan/zoom 適用前) の座標系
   * (= FamilyTreeCanvas 内のノードの left/top と同じ座標系) で渡す
   * (RQ-05-11: 複数ノードのまとめ選択)。
   */
  onSelectionEnd?: (rect: SelectionRect) => void;
  /** 背景を (ドラッグなしで) クリックしたときに呼ばれる。選択解除に使う。 */
  onBackgroundClick?: () => void;
}

interface PanState {
  pointerId: number;
  startClientX: number;
  startClientY: number;
  originX: number;
  originY: number;
  moved: boolean;
}

interface SelectState {
  pointerId: number;
  startContentX: number;
  startContentY: number;
}

export function Viewport({
  zoom,
  onZoomChange,
  children,
  onSelectionEnd = () => {},
  onBackgroundClick = () => {},
}: ViewportProps) {
  const [pan, setPan] = useState({ x: 40, y: 40 });
  const [selectionRect, setSelectionRect] = useState<SelectionRect | null>(null);
  const panState = useRef<PanState | null>(null);
  const selectState = useRef<SelectState | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  function handleWheel(event: WheelEvent<HTMLDivElement>) {
    event.preventDefault();
    const next = zoom - event.deltaY * ZOOM_STEP;
    onZoomChange(Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, next)));
  }

  /** クライアント座標 (screen px) を viewport__content 基準の座標に変換する。 */
  function toContentPoint(clientX: number, clientY: number): { x: number; y: number } {
    const origin = rootRef.current?.getBoundingClientRect();
    const originX = origin?.left ?? 0;
    const originY = origin?.top ?? 0;
    return {
      x: (clientX - originX - pan.x) / zoom,
      y: (clientY - originY - pan.y) / zoom,
    };
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    // ノード側 (VerticalNode) が左クリックドラッグを処理する場合は
    // stopPropagation されているため、ここに来るのは背景での操作のみ
    // (右クリックはノード側で stopPropagation しないため、ノード上から
    // 始めても矩形選択の起点にできる)。
    if (event.button === 2) {
      (event.target as HTMLElement).setPointerCapture(event.pointerId);
      const content = toContentPoint(event.clientX, event.clientY);
      selectState.current = {
        pointerId: event.pointerId,
        startContentX: content.x,
        startContentY: content.y,
      };
      setSelectionRect({ left: content.x, top: content.y, right: content.x, bottom: content.y });
      return;
    }
    if (event.button !== 0) return;
    (event.target as HTMLElement).setPointerCapture(event.pointerId);
    panState.current = {
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      originX: pan.x,
      originY: pan.y,
      moved: false,
    };
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    const select = selectState.current;
    if (select && select.pointerId === event.pointerId) {
      const content = toContentPoint(event.clientX, event.clientY);
      setSelectionRect({
        left: Math.min(select.startContentX, content.x),
        top: Math.min(select.startContentY, content.y),
        right: Math.max(select.startContentX, content.x),
        bottom: Math.max(select.startContentY, content.y),
      });
      return;
    }
    const pan_ = panState.current;
    if (!pan_ || pan_.pointerId !== event.pointerId) return;
    const dx = event.clientX - pan_.startClientX;
    const dy = event.clientY - pan_.startClientY;
    if (Math.abs(dx) > CLICK_THRESHOLD_PX || Math.abs(dy) > CLICK_THRESHOLD_PX) {
      pan_.moved = true;
    }
    setPan({ x: pan_.originX + dx, y: pan_.originY + dy });
  }

  function handlePointerUp(event: PointerEvent<HTMLDivElement>) {
    const select = selectState.current;
    if (select && select.pointerId === event.pointerId) {
      selectState.current = null;
      const rect = selectionRect;
      setSelectionRect(null);
      // 幅・高さのどちらかが閾値を超えていればドラッグとみなす (縦方向のみの
      // 小さな矩形でも幅だけを見ていると選択が成立しない不具合を避ける)。
      const threshold = CLICK_THRESHOLD_PX / zoom;
      if (rect && (rect.right - rect.left > threshold || rect.bottom - rect.top > threshold)) {
        onSelectionEnd(rect);
      }
      return;
    }
    const pan_ = panState.current;
    if (pan_ && pan_.pointerId === event.pointerId && !pan_.moved) {
      onBackgroundClick();
    }
    panState.current = null;
  }

  return (
    <div
      ref={rootRef}
      className="viewport"
      onWheel={handleWheel}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      onContextMenu={(event) => event.preventDefault()}
    >
      <div
        className="viewport__content"
        style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
      >
        {children}
        {selectionRect && (
          <div
            className="viewport__selection-box"
            style={{
              left: selectionRect.left,
              top: selectionRect.top,
              width: selectionRect.right - selectionRect.left,
              height: selectionRect.bottom - selectionRect.top,
            }}
          />
        )}
      </div>
      <div className="viewport__zoom-indicator">{Math.round(zoom * 100)}%</div>
    </div>
  );
}
