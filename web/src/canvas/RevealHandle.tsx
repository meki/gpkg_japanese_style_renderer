import type { RevealAnchor } from "../editing/revealAnchors";
import "./RevealHandle.css";

interface RevealHandleProps {
  anchor: RevealAnchor;
  /** アンカーとなる可視ノードの、画面上のボックス矩形 (px)。 */
  box: { left: number; top: number; right: number; bottom: number };
  onReveal: (handles: string[]) => void;
}

const STUB_LENGTH = 10;
const HANDLE_SIZE = 14;

export function RevealHandle({ anchor, box, onReveal }: RevealHandleProps) {
  const centerX = (box.left + box.right) / 2;
  const centerY = (box.top + box.bottom) / 2;
  let left: number;
  let top: number;
  switch (anchor.direction) {
    case "up":
      left = centerX - HANDLE_SIZE / 2;
      top = box.top - STUB_LENGTH - HANDLE_SIZE;
      break;
    case "down":
      left = centerX - HANDLE_SIZE / 2;
      top = box.bottom + STUB_LENGTH;
      break;
    case "left":
      left = box.left - STUB_LENGTH - HANDLE_SIZE;
      top = centerY - HANDLE_SIZE / 2;
      break;
    case "right":
      left = box.right + STUB_LENGTH;
      top = centerY - HANDLE_SIZE / 2;
      break;
  }

  return (
    <button
      type="button"
      className={`reveal-handle reveal-handle--${anchor.direction}`}
      style={{ left, top }}
      title={`非表示のノードを再表示 (${anchor.targetHandles.length}件)`}
      onPointerDown={(event) => event.stopPropagation()}
      onClick={(event) => {
        event.stopPropagation();
        onReveal(anchor.targetHandles);
      }}
    >
      +
    </button>
  );
}
