import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
  staticFile,
} from "remotion";
import type { SceneSpec, Brand } from "../../types";
import { GrainOverlay } from "../shared/GrainOverlay";
import { KineticCaptions } from "../shared/KineticCaptions";
import { EvidenceBadge } from "../shared/EvidenceBadge";
import { FallbackEvidencePanel } from "../shared/FallbackEvidencePanel";
import { StructuredVisualLayer } from "../shared/StructuredVisualLayer";
import { getScenePalette } from "../shared/sceneStyle";
import { useLayout } from "../../hooks/useLayout";

interface Props {
  scene: SceneSpec;
  brand: Brand;
}

export const CitationScene: React.FC<Props> = ({ scene, brand }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { colors, fonts } = brand;
  const palette = getScenePalette(scene, brand);

  const layout = useLayout();
  const cardSpring = spring({ frame, fps, config: { damping: 12, stiffness: 60 } });
  const citation = scene.citations?.[0];

  // Ken Burns: slow zoom-in
  const bgScale = interpolate(frame, [0, durationInFrames], [1.0, 1.12], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: palette.background }}>
      {/* ── Background image with Ken Burns ── */}
      {scene.imagePath && (
        <Img
          src={staticFile(scene.imagePath)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            position: "absolute",
            opacity: 0.5,
            transform: `scale(${bgScale})`,
            transformOrigin: "center center",
          }}
        />
      )}

      <StructuredVisualLayer scene={scene} brand={brand} layout="split" emphasize="right" />

      {/* ── Gradient overlay ── */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, ${palette.background}55 0%, ${palette.background}28 36%, ${palette.backgroundAlt}da 100%)`,
        }}
      />

      {/* ── Grain ── */}
      <GrainOverlay />

      <EvidenceBadge scene={scene} brand={brand} />

      {/* ── Content ── */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: layout.edgeInset,
        }}
      >
        {/* "STUDY REFERENCED" label */}
        <div
          style={{
            position: "absolute",
            top: layout.topInset,
            left: layout.edgeInset,
            display: "flex",
            alignItems: "center",
            gap: 12,
            opacity: interpolate(frame, [0, 15], [0, 0.7], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          <div
            style={{
              width: 32,
              height: 2,
              backgroundColor: palette.accent,
            }}
          />
          <span
            style={{
              color: palette.textMuted,
              fontFamily: fonts.body,
              fontSize: 16,
              textTransform: "uppercase",
              letterSpacing: 3,
              fontWeight: 600,
            }}
          >
            Research Citation
          </span>
        </div>

        {/* Paper card */}
        <div
          style={{
            backgroundColor: `${colors.text}0c`,
            border: `1px solid ${colors.text}18`,
            borderRadius: 20,
            padding: `${layout.cardPaddingV}px ${layout.cardPaddingH}px`,
            maxWidth: layout.maxContentWidth,
            width: "100%",
            transform: `translateY(${interpolate(cardSpring, [0, 1], [30, 0])}px)`,
            opacity: cardSpring,
            position: "relative",
            backdropFilter: "blur(12px)",
            marginLeft: "28%",
          }}
        >
          {/* Evidence strength pip */}
          <div
            style={{
              position: "absolute",
              top: -1,
              left: layout.edgeInset / 2,
              right: layout.edgeInset / 2,
              height: 3,
              backgroundColor: scene.evidenceColor,
              borderRadius: "0 0 3px 3px",
            }}
          />

          {/* Paper title */}
          {citation && (
            <div
              style={{
                color: palette.accent,
                fontFamily: fonts.body,
                fontSize: layout.citationTitleFontSize,
                fontWeight: 600,
                marginBottom: 20,
                textTransform: "uppercase",
                letterSpacing: 1,
              }}
            >
              {citation.label}
              {citation.detail && (
                <span style={{ color: palette.textMuted, fontWeight: 400 }}>
                  {" "}
                  — {citation.detail}
                </span>
              )}
            </div>
          )}

          {/* Main quote/claim */}
          <div
            style={{
              color: palette.text,
              fontFamily: fonts.heading,
              fontSize: layout.bodyFontSize,
              fontWeight: 600,
              lineHeight: 1.4,
              marginBottom: 28,
              borderLeft: `3px solid ${palette.accent}`,
              paddingLeft: 24,
              textShadow: "0 2px 8px rgba(0,0,0,0.3)",
            }}
          >
            {scene.heading || scene.narration.split(".")[0] + "."}
          </div>

          {/* Static narration fallback (when no word timings) */}
          {!(scene.wordTimings && scene.wordTimings.length > 0) && scene.narration ? (
            <p
              style={{
                color: palette.textMuted,
                fontFamily: fonts.body,
                fontSize: layout.bodyFontSize - 4,
                lineHeight: 1.6,
                margin: 0,
                opacity: interpolate(frame, [15, 30], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              {scene.narration.length > 300
                ? scene.narration.substring(0, 300) + "..."
                : scene.narration}
            </p>
          ) : null}

          {/* DOI / URL */}
          {citation?.doi && (
            <div
              style={{
                marginTop: 24,
                color: palette.textMuted,
                fontFamily: fonts.body,
                fontSize: 16,
                opacity: interpolate(frame, [25, 40], [0, 0.6], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              DOI: {citation.doi}
            </div>
          )}

        </div>
      </AbsoluteFill>

      {/* ── Bottom caption gradient ── */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "35%",
          background: `linear-gradient(transparent, ${palette.background}e0)`,
          pointerEvents: "none",
        }}
      />

      {/* ── Bottom captions ── */}
      {scene.wordTimings && scene.wordTimings.length > 0 && (
        <div
          style={{
            position: "absolute",
            bottom: layout.bottomInset,
            left: layout.edgeInset,
            right: layout.edgeInset,
            display: "flex",
            justifyContent: "center",
          }}
        >
          <KineticCaptions
            wordTimings={scene.wordTimings}
            colors={{
              ...colors,
              text: palette.text,
              textSecondary: palette.textMuted,
              accent: palette.accent,
            }}
            fonts={fonts}
          />
        </div>
      )}

      <FallbackEvidencePanel scene={scene} brand={brand} />
    </AbsoluteFill>
  );
};
