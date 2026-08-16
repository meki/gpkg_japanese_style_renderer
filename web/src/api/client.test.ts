import { afterEach, describe, expect, it, vi } from "vitest";
import { getLayout } from "./client";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("getLayout", () => {
  it("restores photo height when an older backend omits it", async () => {
    const legacyLayout = {
      version: 1,
      direction: "vertical",
      nodes: [
        {
          handle: "_p0004",
          generation: 1,
          order_in_generation: 0,
          x: 2,
          y: 3,
          width: 3.2,
          height: 9.8,
          view: {
            surname: "山田",
            given_name: "三郎",
            surname_kana: null,
            given_name_kana: null,
            former_surname: null,
            is_spouse_in: false,
            birth_order_label: null,
            blood_type: null,
            birth_date_display: null,
            death_date_display: null,
            is_deceased: false,
            has_photo: true,
            notes: [],
            is_focus_person: false,
            gender: "M",
          },
        },
      ],
      marriage_edges: [],
      child_edges: [],
      auxiliary_nodes: [],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => legacyLayout,
      }),
    );

    const layout = await getLayout("project", "_p0004");

    expect(layout.nodes[0].date_column_width).toBe(0);
    expect(layout.nodes[0].photo_height).toBeCloseTo(0.15 + 3.2 * 1.25);
  });

  it("keeps the backend photo height when it is present", async () => {
    const layout = {
      version: 1,
      direction: "vertical",
      nodes: [
        {
          handle: "_p0001",
          generation: 0,
          order_in_generation: 0,
          x: 0,
          y: 0,
          width: 2,
          height: 4,
          date_column_width: 0,
          photo_height: 7.5,
          view: { has_photo: true },
        },
      ],
      marriage_edges: [],
      child_edges: [],
      auxiliary_nodes: [],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => layout,
      }),
    );

    const result = await getLayout("project", "_p0001");

    expect(result.nodes[0].photo_height).toBe(7.5);
  });
});
