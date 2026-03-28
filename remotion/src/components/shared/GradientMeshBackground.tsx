import React from "react";
import { AbsoluteFill } from "remotion";
import type { BrandColors } from "../../types";

interface Props {
  frame: number;
  colors: BrandColors;
}

export const GradientMeshBackground: React.FC<Props> = ({ frame, colors }) => {
  const drift1 = Math.sin(frame * 0.008) * 5;
  const drift2 = Math.cos(frame * 0.006) * 4;
  const drift3 = Math.sin(frame * 0.01) * 3;

  return (
    <AbsoluteFill
      style={{
        background: [
          `radial-gradient(ellipse 80% 60% at ${48 + drift1}% ${35 + drift2}%, ${colors.accent}25 0%, transparent 70%)`,
          `radial-gradient(ellipse 70% 50% at ${65 + drift2}% ${60 + drift3}%, ${colors.warning}18 0%, transparent 65%)`,
          `radial-gradient(ellipse 90% 70% at ${30 - drift3}% ${70 - drift1}%, ${colors.danger}12 0%, transparent 60%)`,
          `radial-gradient(ellipse 100% 80% at 50% 50%, ${colors.primary}ff 0%, ${colors.secondary || "#0D1F3C"} 100%)`,
        ].join(", "),
      }}
    />
  );
};
