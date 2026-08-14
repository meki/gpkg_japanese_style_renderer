// Python 側 (src/gpkg_jsr/layout/types.py, src/gpkg_jsr/model/view.py) の
// pydantic モデルと対になる TypeScript 型定義。
// AD-01-03: LayoutResult が Python とブラウザ描画層の唯一の契約。

export type Calendar = "western" | "wareki";

export interface DateDisplay {
  calendar: Calendar;
  text: string;
}

export interface PersonView {
  surname: string;
  given_name: string;
  surname_kana: string | null;
  given_name_kana: string | null;
  former_surname: string | null;
  is_spouse_in: boolean;
  birth_order_label: string | null;
  blood_type: string | null;
  birth_date_display: DateDisplay | null;
  death_date_display: DateDisplay | null;
  is_deceased: boolean;
  has_photo: boolean;
  notes: string[];
  is_focus_person: boolean;
  gender: string;
}

export interface PersonNode {
  handle: string;
  generation: number;
  order_in_generation: number;
  x: number;
  y: number;
  width: number;
  height: number;
  view: PersonView;
}

export interface MarriageEdge {
  family_handle: string;
  husband_handle: string;
  wife_handle: string;
  midpoint_x: number;
  y: number;
}

export type ChildRelation = "birth" | "adopted";

export interface ChildEdge {
  family_handle: string;
  child_handle: string;
  parent_handles: string[];
  relation: ChildRelation;
  points: [number, number][];
}

export type LayoutDirection = "vertical" | "horizontal";

export interface LayoutResult {
  version: number;
  direction: LayoutDirection;
  nodes: PersonNode[];
  marriage_edges: MarriageEdge[];
  child_edges: ChildEdge[];
  auxiliary_nodes: PersonNode[];
}
