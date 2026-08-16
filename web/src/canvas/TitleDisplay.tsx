import "./TitleDisplay.css";
import type { TitlePosition } from "../types/titleSettings";

interface TitleDisplayProps {
  text: string;
  position: TitlePosition;
  widthPx: number;
  heightPx: number;
  fontSize: number;
}

/** Display the title on the right vertically or at the top horizontally (SP-06-01). */
export function TitleDisplay({ text, position, widthPx, heightPx, fontSize }: TitleDisplayProps) {
  if (!text) return null;
  return (
    <div
      className={`title-display title-display--${position}`}
      style={{
        fontSize,
        ...(position === "top" ? { width: widthPx } : { height: heightPx }),
      }}
    >
      {text}
    </div>
  );
}
