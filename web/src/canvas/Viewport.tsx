import { useRef, useState, type PointerEvent, type ReactNode, type WheelEvent } from "react";
import "./Viewport.css";

// SP-05-05: ズーム範囲は 25%〜400%。
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 4;
const ZOOM_STEP = 0.001;

interface ViewportProps {
  children: ReactNode;
}

interface DragState {
  pointerId: number;
  startX: number;
  startY: number;
  originX: number;
  originY: number;
}

export function Viewport({ children }: ViewportProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 40, y: 40 });
  const dragState = useRef<DragState | null>(null);

  function handleWheel(event: WheelEvent<HTMLDivElement>) {
    event.preventDefault();
    setZoom((current) => {
      const next = current - event.deltaY * ZOOM_STEP;
      return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, next));
    });
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    (event.target as HTMLElement).setPointerCapture(event.pointerId);
    dragState.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: pan.x,
      originY: pan.y,
    };
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    const drag = dragState.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    setPan({
      x: drag.originX + (event.clientX - drag.startX),
      y: drag.originY + (event.clientY - drag.startY),
    });
  }

  function handlePointerUp() {
    dragState.current = null;
  }

  return (
    <div
      className="viewport"
      onWheel={handleWheel}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      <div
        className="viewport__content"
        style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
      >
        {children}
      </div>
      <div className="viewport__zoom-indicator">{Math.round(zoom * 100)}%</div>
    </div>
  );
}
