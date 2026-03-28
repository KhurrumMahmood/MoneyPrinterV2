import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";
import type { BrandColors } from "../../types";

interface Props {
  keywords: string[];
  colors: BrandColors;
  fonts: { heading: string };
  startFrame?: number;
}

export const KeywordOverlay: React.FC<Props> = ({
  keywords,
  colors,
  fonts,
  startFrame = 15,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!keywords || keywords.length === 0) return null;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 120,
        left: 80,
        right: 80,
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        gap: 16,
      }}
    >
      {keywords.map((keyword, i) => {
        const delay = startFrame + i * 6;
        const localFrame = Math.max(0, frame - delay);
        const pillSpring = spring({
          frame: localFrame,
          fps,
          config: { damping: 14, stiffness: 120, mass: 0.7 },
        });

        const scale = interpolate(pillSpring, [0, 1], [0.7, 1]);
        const translateY = interpolate(pillSpring, [0, 1], [20, 0]);

        return (
          <div
            key={i}
            style={{
              opacity: pillSpring,
              transform: `scale(${scale}) translateY(${translateY}px)`,
              backgroundColor: `${colors.accent}18`,
              border: `1px solid ${colors.accent}35`,
              borderRadius: 16,
              padding: "14px 32px",
              backdropFilter: "blur(8px)",
            }}
          >
            <span
              style={{
                color: colors.text,
                fontFamily: fonts.heading,
                fontSize: 42,
                fontWeight: 800,
                letterSpacing: -0.5,
                textShadow: `0 2px 16px rgba(0,0,0,0.3)`,
              }}
            >
              {keyword}
            </span>
          </div>
        );
      })}
    </div>
  );
};
