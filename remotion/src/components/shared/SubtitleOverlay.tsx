import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import type { Brand } from "../../types";

interface SubtitleCue {
  startMs: number;
  endMs: number;
  text: string;
}

interface Props {
  cues: SubtitleCue[];
  brand: Brand;
}

export const SubtitleOverlay: React.FC<Props> = ({ cues, brand }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { colors, fonts } = brand;

  const currentTimeMs = (frame / fps) * 1000;

  // Find current subtitle cue
  const activeCue = cues.find(
    (cue) => currentTimeMs >= cue.startMs && currentTimeMs <= cue.endMs
  );

  if (!activeCue) return null;

  // Fade in/out at edges
  const fadeIn = interpolate(
    currentTimeMs,
    [activeCue.startMs, activeCue.startMs + 150],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const fadeOut = interpolate(
    currentTimeMs,
    [activeCue.endMs - 150, activeCue.endMs],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const opacity = Math.min(fadeIn, fadeOut);

  return (
    <div
      style={{
        position: "absolute",
        bottom: 100,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        opacity,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          backgroundColor: `${colors.primary}dd`,
          borderRadius: 8,
          padding: "12px 28px",
          maxWidth: 1200,
        }}
      >
        <span
          style={{
            color: colors.text,
            fontFamily: fonts.body,
            fontSize: 28,
            fontWeight: 500,
            lineHeight: 1.4,
            textAlign: "center",
          }}
        >
          {activeCue.text}
        </span>
      </div>
    </div>
  );
};

// Parse SRT content into cues
export function parseSrt(srtContent: string): SubtitleCue[] {
  const cues: SubtitleCue[] = [];
  const blocks = srtContent.trim().split(/\n\n+/);

  for (const block of blocks) {
    const lines = block.trim().split("\n");
    if (lines.length < 3) continue;

    const timeMatch = lines[1].match(
      /(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})/
    );
    if (!timeMatch) continue;

    const [, sh, sm, ss, sms, eh, em, es, ems] = timeMatch.map(Number);
    const startMs =
      (sh || 0) * 3600000 + (sm || 0) * 60000 + (ss || 0) * 1000 + (sms || 0);
    const endMs =
      (eh || 0) * 3600000 + (em || 0) * 60000 + (es || 0) * 1000 + (ems || 0);

    const text = lines.slice(2).join(" ").trim();
    if (text) {
      cues.push({ startMs, endMs, text });
    }
  }

  return cues;
}
