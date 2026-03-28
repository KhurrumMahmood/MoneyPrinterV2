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
import type { SceneSpec, Brand, SourceEntry } from "../../types";
import { GrainOverlay } from "../shared/GrainOverlay";
import { EvidenceBadge } from "../shared/EvidenceBadge";
import { FallbackEvidencePanel } from "../shared/FallbackEvidencePanel";
import { useLayout } from "../../hooks/useLayout";

interface Props {
  scene: SceneSpec;
  brand: Brand;
  sourcesList?: SourceEntry[];
}

export const SourceListScene: React.FC<Props> = ({ scene, brand, sourcesList = [] }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { colors, fonts } = brand;
  const layout = useLayout();

  const headerSpring = spring({ frame, fps, config: { damping: 14 } });

  // Ken Burns: subtle slow zoom
  const bgScale = interpolate(frame, [0, durationInFrames], [1.0, 1.06], {
    extrapolateRight: "clamp",
  });

  // Use sourcesList from top-level spec if available, else use citations
  const sources: Array<{ label: string; detail?: string; doi?: string }> =
    sourcesList.length > 0
      ? sourcesList.map((s) => ({
          label: s.label,
          detail: s.full_citation,
          doi: s.doi,
        }))
      : (scene.citations || []).map((c) => ({
          label: c.label,
          detail: c.detail,
          doi: c.doi,
        }));

  return (
    <AbsoluteFill style={{ backgroundColor: colors.primary }}>
      {/* ── Background image with subtle Ken Burns ── */}
      {scene.imagePath && (
        <Img
          src={staticFile(scene.imagePath)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            position: "absolute",
            opacity: 0.3,
            transform: `scale(${bgScale})`,
            transformOrigin: "center center",
          }}
        />
      )}

      {/* ── Gradient overlay ── */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, ${colors.primary}70 0%, ${colors.primary}50 50%, ${colors.primary}90 100%)`,
        }}
      />

      {/* ── Grain ── */}
      <GrainOverlay />

      <EvidenceBadge scene={scene} brand={brand} />

      {/* ── Content ── */}
      <AbsoluteFill style={{ padding: layout.contentPadding }}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            marginBottom: 40,
            opacity: headerSpring,
            transform: `translateX(${interpolate(headerSpring, [0, 1], [-20, 0])}px)`,
          }}
        >
          <div
            style={{
              width: 40,
              height: 3,
              backgroundColor: colors.accent,
              borderRadius: 2,
            }}
          />
          <h2
            style={{
              color: colors.text,
              fontFamily: fonts.heading,
              fontSize: layout.h2FontSize,
              fontWeight: 700,
              margin: 0,
              textShadow: "0 2px 12px rgba(0,0,0,0.4)",
            }}
          >
            {scene.heading || "Sources & References"}
          </h2>
        </div>

        {/* Source list */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
            overflow: "hidden",
            flex: 1,
          }}
        >
          {sources.map((source, i) => {
            const delay = 8 + i * 4;
            const itemOpacity = interpolate(frame, [delay, delay + 10], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const itemSlide = interpolate(frame, [delay, delay + 10], [15, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });

            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 16,
                  opacity: itemOpacity,
                  transform: `translateY(${itemSlide}px)`,
                  padding: "12px 20px",
                  backgroundColor: `${colors.text}08`,
                  borderRadius: 8,
                  backdropFilter: "blur(4px)",
                }}
              >
                {/* Number */}
                <span
                  style={{
                    color: colors.accent,
                    fontFamily: fonts.body,
                    fontSize: layout.sourceNumberFontSize,
                    fontWeight: 700,
                    minWidth: 32,
                    flexShrink: 0,
                  }}
                >
                  {i + 1}.
                </span>

                {/* Source info */}
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      color: colors.text,
                      fontFamily: fonts.body,
                      fontSize: layout.sourceItemFontSize,
                      fontWeight: 600,
                      lineHeight: 1.4,
                      textShadow: "0 1px 6px rgba(0,0,0,0.3)",
                    }}
                  >
                    {source.label}
                  </div>
                  {source.detail && (
                    <div
                      style={{
                        color: colors.textSecondary,
                        fontFamily: fonts.body,
                        fontSize: layout.sourceDetailFontSize,
                        marginTop: 4,
                        lineHeight: 1.4,
                      }}
                    >
                      {source.detail.length > 150
                        ? source.detail.substring(0, 150) + "..."
                        : source.detail}
                    </div>
                  )}
                  {source.doi && (
                    <div
                      style={{
                        color: colors.accent,
                        fontFamily: fonts.body,
                        fontSize: 14,
                        marginTop: 4,
                        opacity: 0.7,
                      }}
                    >
                      DOI: {source.doi}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Disclaimer */}
        <div
          style={{
            position: "absolute",
            bottom: layout.bottomInset / 2,
            left: layout.edgeInset,
            right: layout.edgeInset,
            color: colors.textSecondary,
            fontFamily: fonts.body,
            fontSize: 16,
            opacity: 0.5,
            textAlign: "center",
          }}
        >
          All sources available in the video description
        </div>
      </AbsoluteFill>

      <FallbackEvidencePanel scene={scene} brand={brand} />
    </AbsoluteFill>
  );
};
