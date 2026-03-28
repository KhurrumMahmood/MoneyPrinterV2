import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Img,
  staticFile,
} from "remotion";
import type { SceneSpec, Brand } from "../../types";
import { KineticCaptions } from "../shared/KineticCaptions";
import { KeywordOverlay } from "../shared/KeywordOverlay";
import { EvidenceBadge } from "../shared/EvidenceBadge";
import { FallbackEvidencePanel } from "../shared/FallbackEvidencePanel";
import { useLayout } from "../../hooks/useLayout";

interface Props {
  scene: SceneSpec;
  brand: Brand;
}

export const ImageScene: React.FC<Props> = ({ scene, brand }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { colors, fonts } = brand;
  const layout = useLayout();

  // Ken Burns: slow zoom out (pull-back reveal)
  const scale = interpolate(frame, [0, durationInFrames], [1.18, 1.0], {
    extrapolateRight: "clamp",
  });

  const captionFade = interpolate(frame, [10, 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.primary }}>
      {/* Image with Ken Burns */}
      {scene.imagePath ? (
        <Img
          src={staticFile(scene.imagePath)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${scale})`,
            transformOrigin: "top center",
          }}
        />
      ) : (
        <AbsoluteFill
          style={{
            background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.secondary} 100%)`,
          }}
        />
      )}

      {/* Bottom gradient for caption readability */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "40%",
          background: `linear-gradient(transparent, ${colors.primary}ee)`,
        }}
      />

      {/* Caption */}
      {scene.heading && (
        <div
          style={{
            position: "absolute",
            bottom: layout.bottomInset,
            left: layout.edgeInset,
            right: layout.edgeInset,
            opacity: captionFade,
          }}
        >
          <h3
            style={{
              color: colors.text,
              fontFamily: fonts.heading,
              fontSize: layout.h2FontSize - 4,
              fontWeight: 700,
              lineHeight: 1.3,
              marginBottom: 12,
              textShadow: "0 2px 12px rgba(0,0,0,0.5)",
            }}
          >
            {scene.heading}
          </h3>
          {scene.wordTimings && scene.wordTimings.length > 0 ? (
            <KineticCaptions
              wordTimings={scene.wordTimings}
              colors={colors}
              fonts={fonts}
            />
          ) : scene.narration ? (
            <p
              style={{
                color: colors.textSecondary,
                fontFamily: fonts.body,
                fontSize: layout.bodyFontSize - 6,
                lineHeight: 1.5,
                maxWidth: layout.maxContentWidth * 0.7,
              }}
            >
              {scene.narration.length > 200
                ? scene.narration.substring(0, 200) + "..."
                : scene.narration}
            </p>
          ) : null}
        </div>
      )}

      {/* Citation overlay */}
      {scene.citations && scene.citations.length > 0 && (
        <div
          style={{
            position: "absolute",
            top: layout.topInset,
            right: layout.edgeInset,
            opacity: interpolate(frame, [20, 35], [0, 0.8], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          {scene.citations.map((cite, i) => (
            <div
              key={i}
              style={{
                backgroundColor: `${colors.primary}cc`,
                border: `1px solid ${colors.accent}40`,
                borderRadius: 8,
                padding: "8px 16px",
                color: colors.textSecondary,
                fontFamily: fonts.body,
                fontSize: 15,
                marginBottom: 6,
              }}
            >
              {cite.label}
            </div>
          ))}
        </div>
      )}

      <EvidenceBadge scene={scene} brand={brand} />

      {scene.keywords && scene.keywords.length > 0 && (
        <KeywordOverlay keywords={scene.keywords} colors={colors} fonts={fonts} startFrame={18} />
      )}

      <FallbackEvidencePanel scene={scene} brand={brand} />
    </AbsoluteFill>
  );
};
