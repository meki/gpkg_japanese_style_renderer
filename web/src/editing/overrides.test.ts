import { describe, expect, it } from "vitest";
import type { LayoutResult, PersonNode, PersonView } from "../types/layout";
import { applyOverrides, createEmptyOverrides, descendantsOf } from "./overrides";

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

// P1=P2 -> P3, P4 (F1) ; P3 -> P5 (F2, 単親)
function sampleLayout(): LayoutResult {
  return {
    version: 1,
    direction: "vertical",
    nodes: [
      node("P1", 0, 0),
      node("P2", 3, 0),
      node("P3", 0, 1),
      node("P4", 3, 1),
      node("P5", 0, 2),
    ],
    marriage_edges: [
      { family_handle: "F1", husband_handle: "P1", wife_handle: "P2", midpoint_x: 1.5, y: 1 },
    ],
    child_edges: [
      {
        family_handle: "F1",
        child_handle: "P3",
        parent_handles: ["P1", "P2"],
        relation: "birth",
        points: [
          [1.5, 2],
          [1.5, 3],
          [0, 3],
          [0, 4],
        ],
      },
      {
        family_handle: "F1",
        child_handle: "P4",
        parent_handles: ["P1", "P2"],
        relation: "birth",
        points: [
          [1.5, 2],
          [1.5, 3],
          [3, 3],
          [3, 4],
        ],
      },
      {
        family_handle: "F2",
        child_handle: "P5",
        parent_handles: ["P3"],
        relation: "birth",
        points: [
          [0, 12],
          [0, 13],
          [0, 13],
          [0, 14],
        ],
      },
    ],
    auxiliary_nodes: [],
  };
}

describe("descendantsOf", () => {
  it("follows child_edges via parent_handles, including single-parent families", () => {
    const layout = sampleLayout();
    expect(new Set(descendantsOf(layout, "P1"))).toEqual(new Set(["P3", "P4", "P5"]));
  });

  it("returns an empty list for a leaf node", () => {
    const layout = sampleLayout();
    expect(descendantsOf(layout, "P5")).toEqual([]);
  });

  it("does not include the handle itself", () => {
    const layout = sampleLayout();
    expect(descendantsOf(layout, "P1")).not.toContain("P1");
  });
});

describe("applyOverrides", () => {
  it("returns the layout unchanged when overrides are empty", () => {
    const layout = sampleLayout();
    const result = applyOverrides(layout, createEmptyOverrides());
    expect(result.nodes).toHaveLength(5);
    expect(result.marriage_edges).toHaveLength(1);
    expect(result.child_edges).toHaveLength(3);
  });

  it("moves a node according to a position override", () => {
    const layout = sampleLayout();
    const result = applyOverrides(layout, {
      node_positions: { P3: { x: 99, y: 42 } },
      hidden_handles: [],
    });
    const moved = result.nodes.find((n) => n.handle === "P3");
    expect(moved?.x).toBe(99);
    expect(moved?.y).toBe(42);
    // 他のノードは影響を受けない
    const untouched = result.nodes.find((n) => n.handle === "P4");
    expect(untouched?.x).toBe(3);
  });

  it("collapsing a branch (hiding a node and its descendants) removes their edges too", () => {
    const layout = sampleLayout();
    const toHide = ["P3", ...descendantsOf(layout, "P3")]; // P3 自身 + P5
    const result = applyOverrides(layout, { node_positions: {}, hidden_handles: toHide });

    const remainingHandles = new Set(result.nodes.map((n) => n.handle));
    expect(remainingHandles).toEqual(new Set(["P1", "P2", "P4"]));

    // P3 への child_edge、P5 への child_edge のいずれも消える
    const remainingChildren = result.child_edges.map((e) => e.child_handle);
    expect(remainingChildren).toEqual(["P4"]);

    // 夫婦連結線 (P1=P2) は両者とも表示されたままなので残る
    expect(result.marriage_edges).toHaveLength(1);
  });

  it("hiding one spouse removes the marriage edge", () => {
    const layout = sampleLayout();
    const result = applyOverrides(layout, { node_positions: {}, hidden_handles: ["P2"] });
    expect(result.marriage_edges).toHaveLength(0);
  });
});
