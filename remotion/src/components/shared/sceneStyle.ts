import type { Brand, BrandColors, SceneSpec } from "../../types";

export type SceneRegister =
  | "hook"
  | "kitchen"
  | "clinical"
  | "warning"
  | "action"
  | "neutral";

export interface ScenePalette {
  background: string;
  backgroundAlt: string;
  surface: string;
  surfaceAlt: string;
  text: string;
  textMuted: string;
  accent: string;
  accentAlt: string;
  positive: string;
  caution: string;
  danger: string;
  rule: string;
}

const REGISTER_KEYWORDS: Array<[SceneRegister, string[]]> = [
  ["warning", ["warning", "danger", "safety", "correction", "free pass", "left out"]],
  ["action", ["what you can", "swap", "choose", "pair", "order", "hack", "lentils"]],
  ["clinical", ["trial", "study", "citation", "mystery", "proof"]],
  ["hook", ["changes everything", "one swap", "cut your"]],
];

export const deriveKeywords = (scene: SceneSpec): string[] => {
  if (scene.keywords && scene.keywords.length > 0) {
    return scene.keywords.slice(0, 4);
  }

  const heading = scene.heading
    .replace(/rapid-fire/gi, "")
    .replace(/[—:-]/g, " ")
    .trim();
  const words = heading
    .split(/\s+/)
    .map((word) => word.replace(/[^A-Za-z0-9]/g, ""))
    .filter(Boolean);

  const strongWords = words.filter((word) => {
    const lower = word.toLowerCase();
    return lower.length >= 4 && !["that", "with", "your", "this", "from", "into"].includes(lower);
  });

  if (strongWords.length >= 3) {
    return strongWords.slice(0, 3);
  }

  const narrationWords = scene.narration
    .split(/\s+/)
    .map((word) => word.replace(/[^A-Za-z0-9]/g, ""))
    .filter(Boolean)
    .filter((word) => {
      const lower = word.toLowerCase();
      return lower.length >= 5 && !["would", "there", "which", "about", "their", "these"].includes(lower);
    });

  return [...new Set([...strongWords, ...narrationWords])].slice(0, 3);
};

export const resolveSceneRegister = (scene: SceneSpec): SceneRegister => {
  if (scene.sceneRegister) {
    return scene.sceneRegister;
  }

  const haystack = `${scene.heading} ${scene.narration} ${scene.visualNotes}`.toLowerCase();
  for (const [register, cues] of REGISTER_KEYWORDS) {
    if (cues.some((cue) => haystack.includes(cue))) {
      return register;
    }
  }

  if (scene.type === "citation") {
    return "clinical";
  }
  if (scene.type === "title" || scene.visualType === "hook_card") {
    return "hook";
  }
  if (scene.benefitHarmMode === "caution") {
    return "warning";
  }
  if (scene.evidenceStrength === "strong" || scene.mood === "hopeful" || scene.mood === "excited") {
    return "kitchen";
  }
  return "neutral";
};

const withAlpha = (hex: string, alpha: string): string => `${hex}${alpha}`;

export const getScenePalette = (scene: SceneSpec, brand: Brand): ScenePalette => {
  const register = resolveSceneRegister(scene);
  const fallbackText = brand.colors.text || "#f8fafc";
  const fallbackMuted = brand.colors.textSecondary || "#94a3b8";

  switch (register) {
    case "hook":
      return {
        background: "#0f1726",
        backgroundAlt: "#1f2940",
        surface: "rgba(16, 27, 43, 0.7)",
        surfaceAlt: "rgba(240, 236, 225, 0.08)",
        text: "#f7f2e8",
        textMuted: "#dacfb8",
        accent: "#ffd166",
        accentAlt: "#3ecf8e",
        positive: "#3ecf8e",
        caution: "#ff8f5a",
        danger: "#ff5f7a",
        rule: "#d5a04d",
      };
    case "kitchen":
      return {
        background: "#152235",
        backgroundAlt: "#33455f",
        surface: "rgba(252, 244, 227, 0.1)",
        surfaceAlt: "rgba(14, 34, 48, 0.45)",
        text: "#fbf6eb",
        textMuted: "#d8ceb8",
        accent: "#f4b860",
        accentAlt: "#76d1c4",
        positive: "#5cd38b",
        caution: "#f7a14a",
        danger: "#f36c6c",
        rule: "#e6b672",
      };
    case "clinical":
      return {
        background: "#091322",
        backgroundAlt: "#18304b",
        surface: "rgba(11, 24, 39, 0.78)",
        surfaceAlt: "rgba(20, 184, 166, 0.08)",
        text: fallbackText,
        textMuted: fallbackMuted,
        accent: "#58d5f4",
        accentAlt: "#8edcff",
        positive: "#37d39a",
        caution: "#f3b65f",
        danger: "#ef6b73",
        rule: "#58d5f4",
      };
    case "warning":
      return {
        background: "#231018",
        backgroundAlt: "#47222d",
        surface: "rgba(38, 15, 23, 0.8)",
        surfaceAlt: "rgba(255, 180, 120, 0.08)",
        text: "#fff1eb",
        textMuted: "#e3bfb2",
        accent: "#ff9b54",
        accentAlt: "#ffc36f",
        positive: "#76d1c4",
        caution: "#ff9b54",
        danger: "#ff5f7a",
        rule: "#ff9b54",
      };
    case "action":
      return {
        background: "#1b2430",
        backgroundAlt: "#3b4352",
        surface: "rgba(246, 215, 163, 0.08)",
        surfaceAlt: "rgba(255, 246, 228, 0.08)",
        text: "#fff7eb",
        textMuted: "#e7d4b5",
        accent: "#f3c06d",
        accentAlt: "#9fdac3",
        positive: "#6fda9f",
        caution: "#f3c06d",
        danger: "#ff7a72",
        rule: "#f3c06d",
      };
    default:
      return {
        background: brand.colors.primary,
        backgroundAlt: brand.colors.secondary,
        surface: withAlpha(brand.colors.primary, "cc"),
        surfaceAlt: withAlpha(brand.colors.secondary, "88"),
        text: fallbackText,
        textMuted: fallbackMuted,
        accent: brand.colors.accent,
        accentAlt: brand.colors.warning,
        positive: brand.colors.success,
        caution: brand.colors.warning,
        danger: brand.colors.danger,
        rule: brand.colors.accent,
      };
  }
};
