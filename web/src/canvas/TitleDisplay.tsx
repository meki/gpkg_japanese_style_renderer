import "./TitleDisplay.css";

interface TitleDisplayProps {
  text: string;
  heightPx: number;
  fontSize: number;
}

/** 標題の縦書き表示 (SP-06-01)。図の右端に、図の全高に合わせて配置する。 */
export function TitleDisplay({ text, heightPx, fontSize }: TitleDisplayProps) {
  if (!text) return null;
  return (
    <div className="title-display" style={{ height: heightPx, fontSize }}>
      {text}
    </div>
  );
}
