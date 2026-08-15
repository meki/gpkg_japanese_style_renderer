import { describe, expect, it } from "vitest";
import type { LayoutResult, PersonNode, PersonView } from "../types/layout";
import { computeRevealAnchors } from "./revealAnchors";

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

function node(handle: string, x: number, generation: number, order = 0): PersonNode {
  return {
    handle,
    generation,
    order_in_generation: order,
    x,
    y: generation * 10,
    width: 2,
    height: 2,
    date_column_width: 0,
    photo_height: 0,
    view: view(),
  };
}

// P1=P2 (F1) -> C1,C2,C3,C4,C5 (order 0..4, elder->younger)
function sampleLayout(): LayoutResult {
  return {
    version: 1,
    direction: "vertical",
    nodes: [
      node("P1", 0, 0),
      node("P2", 3, 0),
      node("C1", 0, 1, 0),
      node("C2", 2, 1, 1),
      node("C3", 4, 1, 2),
      node("C4", 6, 1, 3),
      node("C5", 8, 1, 4),
    ],
    marriage_edges: [
      { family_handle: "F1", husband_handle: "P1", wife_handle: "P2", midpoint_x: 1.5, y: 1 },
    ],
    child_edges: [
      "C1",
      "C2",
      "C3",
      "C4",
      "C5",
    ].map((child) => ({
      family_handle: "F1",
      child_handle: child,
      parent_handles: ["P1", "P2"],
      relation: "birth" as const,
      points: [
        [1.5, 2],
        [1.5, 3],
        [0, 3],
        [0, 4],
      ] as [number, number][],
    })),
    auxiliary_nodes: [],
  };
}

describe("computeRevealAnchors", () => {
  it("returns nothing when no handles are hidden", () => {
    expect(computeRevealAnchors(sampleLayout(), new Set())).toEqual([]);
  });

  it("anchors a hidden parent to the visible child with direction 'up'", () => {
    const anchors = computeRevealAnchors(sampleLayout(), new Set(["P1"]));
    const upAnchors = anchors.filter((a) => a.direction === "up");
    // すべての子 (C1..C5) が可視のため、それぞれから P1 への 'up' ハンドルができる
    expect(upAnchors).toHaveLength(5);
    for (const a of upAnchors) {
      expect(a.targetHandles).toEqual(["P1"]);
    }
  });

  it("anchors a hidden child to the visible parent with direction 'down'", () => {
    const anchors = computeRevealAnchors(sampleLayout(), new Set(["C3"]));
    // C3 は他の兄弟 (C2, C4) にも挟まれているため sibling の left/right、
    // かつ両親 (P1, P2) からも down のハンドルができる
    const downAnchors = anchors.filter((a) => a.direction === "down");
    expect(downAnchors.map((a) => a.anchorHandle).sort()).toEqual(["P1", "P2"]);
    for (const a of downAnchors) {
      expect(a.targetHandles).toEqual(["C3"]);
    }
  });

  it("anchors a hidden spouse to the visible spouse using abstract-x ordering", () => {
    // P1.x(0) <= P2.x(3) なので、P1 から見て P2 は画面左、P2 から見て P1 は画面右
    const anchors = computeRevealAnchors(sampleLayout(), new Set(["P2"]));
    const spouseAnchor = anchors.find((a) => a.anchorHandle === "P1" && a.direction === "left");
    expect(spouseAnchor?.targetHandles).toEqual(["P2"]);
  });

  it("merges a contiguous run of hidden middle siblings onto both bordering visible siblings", () => {
    const anchors = computeRevealAnchors(sampleLayout(), new Set(["C2", "C3"]));
    const leftAnchor = anchors.find((a) => a.anchorHandle === "C1" && a.direction === "left");
    const rightAnchor = anchors.find((a) => a.anchorHandle === "C4" && a.direction === "right");
    expect(new Set(leftAnchor?.targetHandles)).toEqual(new Set(["C2", "C3"]));
    expect(new Set(rightAnchor?.targetHandles)).toEqual(new Set(["C2", "C3"]));
  });

  it("only anchors to the single bordering sibling when the hidden run touches an edge of the group", () => {
    // C1 (最年長, order=0) が非表示 -> グループの先頭なので「前」は存在しない。
    // 「後」の C2 にのみ 'right' ハンドルが付く。
    const anchors = computeRevealAnchors(sampleLayout(), new Set(["C1"]));
    const siblingAnchors = anchors.filter((a) => a.targetHandles.includes("C1") && a.anchorHandle !== "P1" && a.anchorHandle !== "P2");
    expect(siblingAnchors).toHaveLength(1);
    expect(siblingAnchors[0]).toMatchObject({ anchorHandle: "C2", direction: "right" });
  });

  it("gives a single node independent handles per direction without merging across relations", () => {
    // P1 と C1 の両方を隠すと、C2 は「C1 の兄」(sibling, 'right') と
    // 「P1 の子」(parent/child, 'up') の 2 つの別方向ハンドルを持つ
    const anchors = computeRevealAnchors(sampleLayout(), new Set(["P1", "C1"]));
    const keys = anchors.map((a) => a.key);
    expect(new Set(keys).size).toBe(keys.length); // (anchor,direction) の重複がない

    const c2Anchors = anchors.filter((a) => a.anchorHandle === "C2");
    expect(c2Anchors).toHaveLength(2);
    expect(c2Anchors.find((a) => a.direction === "up")?.targetHandles).toEqual(["P1"]);
    expect(c2Anchors.find((a) => a.direction === "right")?.targetHandles).toEqual(["C1"]);

    // 非表示ノード自身 (P1) はどの方向のアンカーにもならない
    expect(anchors.some((a) => a.anchorHandle === "P1")).toBe(false);
  });
});
