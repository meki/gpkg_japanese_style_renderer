import { describe, expect, it } from "vitest";
import {
  DEFAULT_TITLE_SETTINGS,
  normalizeTitleSettings,
  type TitleSettings,
} from "./titleSettings";

describe("normalizeTitleSettings", () => {
  it("uses right-side vertical writing by default", () => {
    expect(normalizeTitleSettings()).toEqual(DEFAULT_TITLE_SETTINGS);
  });

  it("preserves the top horizontal-writing position", () => {
    const settings: Partial<TitleSettings> = {
      text: "山田家系図",
      fontSize: 32,
      position: "top",
    };

    expect(normalizeTitleSettings(settings)).toEqual(settings);
  });

  it("falls back to the default position for legacy settings", () => {
    expect(normalizeTitleSettings({ text: "旧形式の標題", fontSize: 24 })).toEqual({
      text: "旧形式の標題",
      fontSize: 24,
      position: "right",
    });
  });

  it("rejects invalid persisted values", () => {
    expect(
      normalizeTitleSettings({
        text: 123 as unknown as string,
        fontSize: Number.NaN,
        position: "invalid" as unknown as TitleSettings["position"],
      }),
    ).toEqual(DEFAULT_TITLE_SETTINGS);
  });
});
