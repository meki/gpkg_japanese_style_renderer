import { describe, expect, it } from "vitest";
import type { LayoutResult, PersonNode, PersonView } from "../types/layout";
import { UNIT_PX } from "../canvas/layoutConstants";
import { computeGroupMove, computeSelectedHandles } from "./selection";

function view(overrides: Partial<PersonView> = {}): PersonView {
  return {
    surname: "山田",
    given_name: "太郎",
    surname_kana: null,
    given_name_kana: null,
    former_surname: null,
    is_spouse_in: false,
    birth_order_label: null,
    blood_type: null,
    birth_date_display: null,
    death_date_display: null,
    is_deceased: false,
    has_photo: false,
    notes: [],
    is_focus_person: false,
    gender: "M",
    ...overrides,
  };
}

function node(handle: string, x: number, generation: number): PersonNode {
  return {
    handle,
    generation,
    order_in_generation: 0,
    x,
    y: generation * 10,
    width: 2,
    height: 2,
    date_column_width: 0,
    photo_height: 0,
    view: view(),
  };
}

// P1(x=0), P2(x=5), P3(x=10) は同一世代 (y=0)。abstract x が小さいほど画面右
// (RQ-02-03) に描画されるため、mirror(x) = (maxX+width - x) の関係で画面上の
// 左右が入れ替わる。totalWidth = maxX + width = 12。
function sampleLayout(): LayoutResult {
  return {
    version: 1,
    direction: "vertical",
    nodes: [node("P1", 0, 0), node("P2", 5, 0), node("P3", 10, 0)],
    marriage_edges: [],
    child_edges: [],
    auxiliary_nodes: [],
  };
}

describe("computeSelectedHandles", () => {
  it("selects only nodes whose visual box intersects the rectangle", () => {
    const layout = sampleLayout();
    // P1 (abstract x=0..2) は画面上もっとも右 (screen x が最大)。
    // totalWidth=12 なので mirror(0)=12*32=384, mirror(2)=10*32=320 →
    // P1 の画面ボックスは [320,384]。
    const rect = { left: 300, top: -10, right: 400, bottom: 100 };
    const selected = computeSelectedHandles(layout, rect);
    expect(selected).toEqual(new Set(["P1"]));
  });

  it("selects multiple nodes when the rectangle spans them", () => {
    const layout = sampleLayout();
    // P2 (x=5..7 -> screen [160,224]), P3 (x=10..12 -> screen [0,64]) の両方を含む範囲。
    const rect = { left: 0, top: -10, right: 224, bottom: 100 };
    const selected = computeSelectedHandles(layout, rect);
    expect(selected).toEqual(new Set(["P2", "P3"]));
  });

  it("selects nothing when the rectangle does not overlap any node", () => {
    const layout = sampleLayout();
    const rect = { left: 1000, top: 1000, right: 1100, bottom: 1100 };
    expect(computeSelectedHandles(layout, rect)).toEqual(new Set());
  });

  it("selects all nodes when the rectangle covers the whole layout", () => {
    const layout = sampleLayout();
    const rect = { left: -1000, top: -1000, right: 1000, bottom: 1000 };
    expect(computeSelectedHandles(layout, rect)).toEqual(new Set(["P1", "P2", "P3"]));
  });

  it("touches a node with a boundary-only overlap (inclusive)", () => {
    const layout = sampleLayout();
    // P1 の画面ボックスは [320,384]、P2 は [160,224]。矩形の右端をちょうど
    // P1 の左端 (320) に合わせ、P2 には届かない範囲にする。
    const rect = { left: 300, top: -10, right: 320, bottom: 100 };
    expect(computeSelectedHandles(layout, rect)).toEqual(new Set(["P1"]));
  });
});

describe("computeGroupMove", () => {
  it("applies the same abstract-space delta to every target node", () => {
    const layout = sampleLayout();
    const nodeByHandle = new Map(layout.nodes.map((n) => [n.handle, n]));
    const targets = new Set(["P1", "P2"]);
    const moved = computeGroupMove(nodeByHandle, targets, 1, 2);
    // VerticalNode.tsx と同じ符号規約: 画面上は左右反転しているため x は減算、y は加算。
    expect(moved.P1).toEqual({ x: -1, y: 2 });
    expect(moved.P2).toEqual({ x: 4, y: 2 });
    expect(moved.P3).toBeUndefined(); // 選択されていないノードは含まれない
  });

  it("ignores target handles that are not present in nodeByHandle", () => {
    const layout = sampleLayout();
    const nodeByHandle = new Map(layout.nodes.map((n) => [n.handle, n]));
    const moved = computeGroupMove(nodeByHandle, new Set(["P1", "GHOST"]), 0, 0);
    expect(Object.keys(moved)).toEqual(["P1"]);
  });

  it("is a no-op delta for a single-node move (matches prior single-drag behavior)", () => {
    const layout = sampleLayout();
    const nodeByHandle = new Map(layout.nodes.map((n) => [n.handle, n]));
    const moved = computeGroupMove(nodeByHandle, new Set(["P2"]), 0, 0);
    expect(moved.P2).toEqual({ x: 5, y: 0 });
  });
});

// UNIT_PX を直接使わないと、layoutConstants.ts の値が変わったときに
// このテストの座標前提が静かにズレるのを防げないため、参照して確認しておく。
describe("test fixture assumptions", () => {
  it("UNIT_PX matches the value baked into the expected screen coordinates above", () => {
    expect(UNIT_PX).toBe(32);
  });
});
