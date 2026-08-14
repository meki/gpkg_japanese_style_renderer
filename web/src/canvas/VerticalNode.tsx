import type { PersonNode } from "../types/layout";
import { personPhotoUrl } from "../api/client";
import "./VerticalNode.css";

interface VerticalNodeProps {
  node: PersonNode;
  scale: number;
  projectId: string;
  /**
   * 抽象座標系での全体幅 (単位)。x=0 が画面上「最も右」に来るよう、ここで
   * 左右反転する (RQ-02-03: 年長者を右に配置。layout/types.ts の docstring
   * および Python 側 layout/types.py の docstring を参照)。
   */
  totalWidth: number;
}

export function VerticalNode({ node, scale, projectId, totalWidth }: VerticalNodeProps) {
  const { view } = node;
  const classNames = ["vertical-node"];
  if (view.is_deceased) classNames.push("vertical-node--deceased");
  if (view.is_focus_person) classNames.push("vertical-node--focus");
  if (view.is_spouse_in) classNames.push("vertical-node--spouse-in");

  const displayLeft = (totalWidth - node.x - node.width) * scale;

  return (
    <div
      className={classNames.join(" ")}
      style={{
        left: displayLeft,
        top: node.y * scale,
        width: node.width * scale,
        height: node.height * scale,
      }}
      title={view.notes.join("\n") || undefined}
    >
      <div className="vertical-node__name">
        {view.former_surname && (
          <span className="vertical-node__former-surname">({view.former_surname})</span>
        )}
        <ruby>
          {view.surname}
          {view.surname_kana && <rt>{view.surname_kana}</rt>}
        </ruby>
        <ruby>
          {view.given_name}
          {view.given_name_kana && <rt>{view.given_name_kana}</rt>}
        </ruby>
      </div>
      <div className="vertical-node__side">
        {view.birth_order_label && (
          <span className="vertical-node__label">{view.birth_order_label}</span>
        )}
        {view.birth_date_display && (
          <span className="vertical-node__date">{view.birth_date_display.text}</span>
        )}
        {view.death_date_display && (
          <span className="vertical-node__date">{view.death_date_display.text}</span>
        )}
      </div>
      {view.has_photo && (
        <img
          className="vertical-node__photo"
          src={personPhotoUrl(projectId, node.handle)}
          alt=""
        />
      )}
    </div>
  );
}
