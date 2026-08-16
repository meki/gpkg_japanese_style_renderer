export type TitlePosition = "right" | "top";

export interface TitleSettings {
  text: string;
  fontSize: number;
  position: TitlePosition;
}

export const DEFAULT_TITLE_SETTINGS: TitleSettings = {
  text: "",
  fontSize: 28,
  position: "right",
};

/** Normalize settings loaded from a project document, including legacy values. */
export function normalizeTitleSettings(
  settings?: Partial<TitleSettings> | null,
): TitleSettings {
  return {
    text: typeof settings?.text === "string" ? settings.text : DEFAULT_TITLE_SETTINGS.text,
    fontSize:
      typeof settings?.fontSize === "number" &&
      Number.isFinite(settings.fontSize) &&
      settings.fontSize > 0
        ? settings.fontSize
        : DEFAULT_TITLE_SETTINGS.fontSize,
    position: settings?.position === "top" ? "top" : DEFAULT_TITLE_SETTINGS.position,
  };
}
