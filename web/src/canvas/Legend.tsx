import "./Legend.css";

interface LegendProps {
  hasDeceased: boolean;
}

/** 故人の凡例 (SP-03-09)。該当者が 1 名以上いる場合のみ表示する。 */
export function Legend({ hasDeceased }: LegendProps) {
  if (!hasDeceased) return null;
  return (
    <div className="legend">
      <span className="legend__swatch" />
      <span className="legend__label">故人</span>
    </div>
  );
}
