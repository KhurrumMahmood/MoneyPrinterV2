import { useVideoConfig } from "remotion";

export interface LayoutConfig {
  isPortrait: boolean;
  width: number;
  height: number;

  // Padding
  contentPadding: string;
  titlePadding: string;

  // Font sizes
  headingFontSize: number;
  h2FontSize: number;
  bodyFontSize: number;
  captionFontSize: number;
  subtitleFontSize: number;
  smallLabelFontSize: number;
  citationTitleFontSize: number;
  doiFontSize: number;

  // Widths
  maxContentWidth: number;
  maxCaptionWidth: number;
  maxSubtitleWidth: number;
  citationCardMaxWidth: number;
  dividerWidth: number;

  // Positioning
  edgeInset: number;
  topInset: number;
  bottomInset: number;

  // Evidence badge
  badgePaddingH: number;
  badgePaddingV: number;

  // Card styling
  cardPaddingH: number;
  cardPaddingV: number;

  // Source list
  sourceItemFontSize: number;
  sourceDetailFontSize: number;
  sourceNumberFontSize: number;
}

export function useLayout(): LayoutConfig {
  const { width, height } = useVideoConfig();
  const isPortrait = height > width;

  if (isPortrait) {
    return {
      isPortrait: true,
      width,
      height,

      contentPadding: "60px 40px",
      titlePadding: "80px 48px",

      headingFontSize: 64,
      h2FontSize: 44,
      bodyFontSize: 30,
      captionFontSize: 48,
      subtitleFontSize: 28,
      smallLabelFontSize: 14,
      citationTitleFontSize: 16,
      doiFontSize: 13,

      maxContentWidth: 960,
      maxCaptionWidth: 960,
      maxSubtitleWidth: 960,
      citationCardMaxWidth: 340,
      dividerWidth: 100,

      edgeInset: 40,
      topInset: 40,
      bottomInset: 80,

      badgePaddingH: 16,
      badgePaddingV: 6,

      cardPaddingH: 40,
      cardPaddingV: 40,

      sourceItemFontSize: 20,
      sourceDetailFontSize: 15,
      sourceNumberFontSize: 16,
    };
  }

  // Landscape (16:9) defaults
  return {
    isPortrait: false,
    width,
    height,

    contentPadding: "70px 100px",
    titlePadding: "100px 120px",

    headingFontSize: 86,
    h2FontSize: 56,
    bodyFontSize: 34,
    captionFontSize: 54,
    subtitleFontSize: 30,
    smallLabelFontSize: 16,
    citationTitleFontSize: 18,
    doiFontSize: 16,

    maxContentWidth: 1400,
    maxCaptionWidth: 1300,
    maxSubtitleWidth: 1200,
    citationCardMaxWidth: 420,
    dividerWidth: 160,

    edgeInset: 100,
    topInset: 56,
    bottomInset: 120,

    badgePaddingH: 20,
    badgePaddingV: 8,

    cardPaddingH: 64,
    cardPaddingV: 56,

    sourceItemFontSize: 22,
    sourceDetailFontSize: 17,
    sourceNumberFontSize: 18,
  };
}
