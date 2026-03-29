import React from "react";
import type { Brand, SceneSpec } from "../../types";

interface Props {
  scene: SceneSpec;
  brand: Brand;
}

export const FallbackEvidencePanel: React.FC<Props> = ({ scene, brand }) => {
  const { colors, fonts } = brand;
  const hasPanel =
    (!!scene.citationCard && !(scene.citations && scene.citations.length > 0)) ||
    (scene.safetyFlags && scene.safetyFlags.length > 0) ||
    (scene.evidenceIds && scene.evidenceIds.length > 0) ||
    !!scene.ctaTarget;

  if (!hasPanel) {
    return null;
  }

  return (
    <div
      style={{
        position: "absolute",
        right: 72,
        bottom: 86,
        maxWidth: 420,
        display: "flex",
        flexDirection: "column",
        gap: 12,
        alignItems: "flex-end",
      }}
    >
      {scene.citationCard && (
        <div
          style={{
            backgroundColor: `${colors.primary}cc`,
            border: `1px solid ${colors.accent}55`,
            borderRadius: 18,
            padding: "16px 20px",
            backdropFilter: "blur(12px)",
          }}
        >
          <div
            style={{
              color: colors.accent,
              fontFamily: fonts.body,
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: 1.5,
              marginBottom: 8,
            }}
          >
            CITED SOURCE
          </div>
          <div
            style={{
              color: colors.text,
              fontFamily: fonts.heading,
              fontSize: 22,
              fontWeight: 700,
              lineHeight: 1.3,
            }}
          >
            {scene.citationCard.label}
          </div>
          {scene.citationCard.detail && (
            <div
              style={{
                color: colors.textSecondary,
                fontFamily: fonts.body,
                fontSize: 16,
                marginTop: 8,
                lineHeight: 1.4,
              }}
            >
              {scene.citationCard.detail}
            </div>
          )}
        </div>
      )}

      {scene.safetyFlags && scene.safetyFlags.length > 0 && (
        <div
          style={{
            backgroundColor: `${colors.danger}18`,
            border: `1px solid ${colors.danger}55`,
            borderRadius: 18,
            padding: "16px 20px",
            backdropFilter: "blur(12px)",
          }}
        >
          <div
            style={{
              color: colors.danger,
              fontFamily: fonts.body,
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: 1.5,
              marginBottom: 8,
            }}
          >
            SAFETY FLAGS
          </div>
          <div
            style={{
              color: colors.text,
              fontFamily: fonts.body,
              fontSize: 18,
              lineHeight: 1.5,
            }}
          >
            {scene.safetyFlags.join(" • ")}
          </div>
        </div>
      )}

      {scene.ctaTarget && (
        <div
          style={{
            color: colors.textSecondary,
            fontFamily: fonts.body,
            fontSize: 16,
            fontWeight: 600,
            letterSpacing: 1.2,
          }}
        >
          Read the dossier for sources and caveats.
        </div>
      )}
    </div>
  );
};
