import React from "react";
import type { Brand, SceneSpec } from "../../types";

interface Props {
  scene: SceneSpec;
  brand: Brand;
}

export const EvidenceBadge: React.FC<Props> = ({ scene, brand }) => {
  const { colors, fonts } = brand;
  const mode = scene.benefitHarmMode || "benefit";
  const label = scene.evidenceStrength
    ? `${scene.evidenceStrength.toUpperCase()} EVIDENCE`
    : "EVIDENCE";
  const background =
    mode === "harm" || mode === "caution" ? colors.danger : scene.evidenceColor || colors.accent;

  return (
    <div
      style={{
        position: "absolute",
        top: 56,
        right: 72,
        backgroundColor: `${background}22`,
        border: `1px solid ${background}66`,
        borderRadius: 999,
        padding: "10px 18px",
        backdropFilter: "blur(10px)",
        display: "flex",
        alignItems: "center",
        gap: 10,
      }}
    >
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          backgroundColor: background,
          boxShadow: `0 0 10px ${background}`,
        }}
      />
      <span
        style={{
          color: colors.text,
          fontFamily: fonts.body,
          fontWeight: 700,
          fontSize: 14,
          letterSpacing: 1.6,
        }}
      >
        {label}
      </span>
    </div>
  );
};
