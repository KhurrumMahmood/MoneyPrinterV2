import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
  staticFile,
  Easing,
} from "remotion";
import type { SceneSpec, Brand, BrandColors } from "../../types";
import { GrainOverlay } from "../shared/GrainOverlay";
import { EvidenceBadge } from "../shared/EvidenceBadge";
import { FallbackEvidencePanel } from "../shared/FallbackEvidencePanel";

interface Props {
  scene: SceneSpec;
  brand: Brand;
}

// ── Slide-in directions for dramatic card entrances ─────────────────────
type SlideDirection = "left" | "right" | "bottom" | "top";
const SLIDE_DIRECTIONS: SlideDirection[] = ["left", "right", "bottom", "top"];

function getSlideOffset(direction: SlideDirection): { x: number; y: number } {
  switch (direction) {
    case "left":
      return { x: -80, y: 0 };
    case "right":
      return { x: 80, y: 0 };
    case "bottom":
      return { x: 0, y: 60 };
    case "top":
      return { x: 0, y: -60 };
  }
}

// ── Glass morphism card ─────────────────────────────────────────────────
const GlassCard: React.FC<{
  text: string;
  index: number;
  accentColor: string;
  frame: number;
  fps: number;
  delay: number;
  totalCards: number;
  fonts: { heading: string; body: string };
  colors: BrandColors;
}> = ({ text, index, accentColor, frame, fps, delay, totalCards, fonts, colors }) => {
  const localFrame = Math.max(0, frame - delay);

  const direction = SLIDE_DIRECTIONS[index % SLIDE_DIRECTIONS.length];
  const offset = getSlideOffset(direction);

  const cardSpring = spring({
    frame: localFrame,
    fps,
    config: { damping: 14, stiffness: 90, mass: 0.8 },
  });

  const translateX = interpolate(cardSpring, [0, 1], [offset.x, 0]);
  const translateY = interpolate(cardSpring, [0, 1], [offset.y, 0]);
  const scale = interpolate(cardSpring, [0, 1], [0.85, 1]);

  // Number indicator entrance (slightly delayed from card)
  const numberFrame = Math.max(0, localFrame - 4);
  const numberSpring = spring({
    frame: numberFrame,
    fps,
    config: { damping: 10, stiffness: 150 },
  });
  const numberScale = interpolate(numberSpring, [0, 1], [0.3, 1]);

  const isWide = totalCards <= 2;

  return (
    <div
      style={{
        width: isWide ? "46%" : "43%",
        opacity: cardSpring,
        transform: `translate(${translateX}px, ${translateY}px) scale(${scale})`,
        position: "relative",
      }}
    >
      {/* Glass card body */}
      <div
        style={{
          backgroundColor: "rgba(255, 255, 255, 0.04)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          borderRadius: 18,
          padding: "30px 28px 28px",
          backdropFilter: "blur(12px)",
          overflow: "hidden",
          position: "relative",
        }}
      >
        {/* Top accent glow line */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 3,
            background: `linear-gradient(90deg, ${accentColor}, ${accentColor}40)`,
            boxShadow: `0 0 16px ${accentColor}50`,
          }}
        />

        {/* Subtle inner glow at top-left corner */}
        <div
          style={{
            position: "absolute",
            top: -40,
            left: -40,
            width: 120,
            height: 120,
            borderRadius: "50%",
            background: `radial-gradient(circle, ${accentColor}10 0%, transparent 70%)`,
            pointerEvents: "none",
          }}
        />

        {/* Large number indicator */}
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            gap: 14,
            marginBottom: 16,
          }}
        >
          <span
            style={{
              color: accentColor,
              fontFamily: fonts.heading,
              fontSize: 44,
              fontWeight: 900,
              opacity: 0.9,
              transform: `scale(${numberScale})`,
              display: "inline-block",
              lineHeight: 1,
              textShadow: `0 0 20px ${accentColor}40`,
            }}
          >
            {String(index + 1).padStart(2, "0")}
          </span>
          <div
            style={{
              height: 2,
              flex: 1,
              maxWidth: 60,
              backgroundColor: `${accentColor}30`,
              borderRadius: 1,
            }}
          />
        </div>

        {/* Content text */}
        <p
          style={{
            color: colors.text,
            fontFamily: fonts.body,
            fontSize: 23,
            lineHeight: 1.55,
            margin: 0,
            letterSpacing: 0.2,
          }}
        >
          {text.length > 160 ? text.substring(0, 157) + "..." : text}
        </p>
      </div>
    </div>
  );
};

// ── Animated connecting line between cards ──────────────────────────────
const ConnectingLine: React.FC<{
  frame: number;
  delay: number;
  orientation: "horizontal" | "vertical";
  accentColor: string;
}> = ({ frame, delay, orientation, accentColor }) => {
  const progress = interpolate(
    frame,
    [delay, delay + 18],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }
  );

  if (progress <= 0) return null;

  const isHorizontal = orientation === "horizontal";

  return (
    <div
      style={{
        position: "absolute",
        ...(isHorizontal
          ? {
              width: `${progress * 100}%`,
              height: 1,
              left: 0,
              top: "50%",
              transformOrigin: "left center",
            }
          : {
              width: 1,
              height: `${progress * 100}%`,
              top: 0,
              left: "50%",
              transformOrigin: "center top",
            }),
        background: `linear-gradient(${isHorizontal ? "90deg" : "180deg"}, ${accentColor}00, ${accentColor}35, ${accentColor}00)`,
      }}
    />
  );
};

// ── Glass citation card ─────────────────────────────────────────────────
const GlassCitationCard: React.FC<{
  label: string;
  detail?: string;
  frame: number;
  fps: number;
  delay: number;
  fonts: { body: string };
  colors: BrandColors;
}> = ({ label, detail, frame, fps, delay, fonts, colors }) => {
  const localFrame = Math.max(0, frame - delay);
  const slideUp = spring({
    frame: localFrame,
    fps,
    config: { damping: 18, stiffness: 80 },
  });
  const translateY = interpolate(slideUp, [0, 1], [30, 0]);

  return (
    <div
      style={{
        opacity: slideUp,
        transform: `translateY(${translateY}px)`,
        backgroundColor: "rgba(255, 255, 255, 0.03)",
        border: `1px solid ${colors.accent}20`,
        borderRadius: 10,
        padding: "8px 18px",
        backdropFilter: "blur(10px)",
        display: "flex",
        alignItems: "center",
        gap: 8,
        maxWidth: 380,
      }}
    >
      <div
        style={{
          width: 5,
          height: 5,
          borderRadius: "50%",
          backgroundColor: colors.accent,
          flexShrink: 0,
          boxShadow: `0 0 6px ${colors.accent}50`,
        }}
      />
      <span
        style={{
          color: `${colors.text}c0`,
          fontFamily: fonts.body,
          fontSize: 14,
          fontWeight: 500,
        }}
      >
        {label}
        {detail && (
          <span style={{ opacity: 0.6, marginLeft: 4 }}>{detail}</span>
        )}
      </span>
    </div>
  );
};

// ── Evidence meter ──────────────────────────────────────────────────────
const EvidenceMeter: React.FC<{
  strength: string;
  color: string;
  frame: number;
  fps: number;
}> = ({ strength, color, frame, fps }) => {
  const levels: Record<string, number> = {
    weak: 1,
    mixed: 2,
    moderate: 3,
    strong: 4,
  };
  const level = levels[strength] || 0;

  return (
    <div style={{ display: "flex", gap: 3, alignItems: "flex-end" }}>
      {[1, 2, 3, 4].map((i) => {
        const barDelay = 12 + i * 3;
        const barSpring = spring({
          frame: Math.max(0, frame - barDelay),
          fps,
          config: { damping: 12, stiffness: 120 },
        });
        const barHeight = (6 + i * 5) * barSpring;
        const isActive = i <= level;

        return (
          <div
            key={i}
            style={{
              width: 5,
              height: barHeight,
              borderRadius: 2,
              backgroundColor: isActive ? color : `${color}25`,
              boxShadow: isActive ? `0 0 6px ${color}40` : "none",
              transition: "background-color 0.2s",
            }}
          />
        );
      })}
    </div>
  );
};

// ── Main component ──────────────────────────────────────────────────────
export const InfographicScene: React.FC<Props> = ({ scene, brand }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { colors, fonts } = brand;

  const cardAccentColors = [colors.accent, "#4DA8DA", colors.warning, colors.danger];

  // Header entrance
  const headerSpring = spring({
    frame,
    fps,
    config: { damping: 16, stiffness: 100 },
  });
  const headerSlideX = interpolate(headerSpring, [0, 1], [-40, 0]);

  // Extract narration parts for cards
  const narrationParts = scene.narration
    .split(/(?<=[.!?])\s+/)
    .filter((s) => s.trim().length > 0)
    .slice(0, 4);

  // Ken Burns on background
  const bgScale = interpolate(frame, [0, scene.durationFrames], [1.0, 1.06], {
    extrapolateRight: "clamp",
  });

  // Stagger timing: cards appear one at a time
  const cardStaggerFrames = 12;

  // Connecting lines appear after the second card
  const lineDelay = 10 + 2 * cardStaggerFrames;

  return (
    <AbsoluteFill style={{ backgroundColor: colors.primary }}>
      {/* ── Background image at 15% opacity ── */}
      {scene.imagePath && (
        <Img
          src={staticFile(scene.imagePath)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            position: "absolute",
            opacity: 0.15,
            transform: `scale(${bgScale})`,
            transformOrigin: "center center",
          }}
        />
      )}

      {/* ── Gradient overlay ── */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(160deg, ${colors.primary}f2 0%, ${colors.secondary || colors.primary}e8 100%)`,
        }}
      />

      {/* ── Grain ── */}
      <GrainOverlay />

      <EvidenceBadge scene={scene} brand={brand} />

      {/* ── Content ── */}
      <AbsoluteFill style={{ padding: "70px 90px" }}>
        {/* ── Header row ── */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 44,
          }}
        >
          {/* Heading with accent line */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 18,
              opacity: headerSpring,
              transform: `translateX(${headerSlideX}px)`,
            }}
          >
            <div
              style={{
                width: 4,
                height: 48,
                backgroundColor: colors.accent,
                borderRadius: 2,
                boxShadow: `0 0 10px ${colors.accent}40`,
              }}
            />
            <h2
              style={{
                color: colors.text,
                fontFamily: fonts.heading,
                fontSize: 50,
                fontWeight: 800,
                margin: 0,
                letterSpacing: -0.5,
                textShadow: "0 2px 12px rgba(0,0,0,0.3)",
              }}
            >
              {scene.heading}
            </h2>
          </div>

          {/* Evidence indicator */}
          {scene.evidenceStrength !== "none" && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                backgroundColor: `${scene.evidenceColor}12`,
                border: `1px solid ${scene.evidenceColor}28`,
                borderRadius: 20,
                padding: "8px 18px",
                backdropFilter: "blur(6px)",
                opacity: interpolate(frame, [10, 22], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              <EvidenceMeter
                strength={scene.evidenceStrength}
                color={scene.evidenceColor}
                frame={frame}
                fps={fps}
              />
              <span
                style={{
                  color: scene.evidenceColor,
                  fontSize: 14,
                  fontFamily: fonts.body,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: 1,
                }}
              >
                {scene.evidenceStrength}
              </span>
            </div>
          )}
        </div>

        {/* ── Card grid with connecting lines ── */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 24,
            justifyContent: "center",
            flex: 1,
            alignItems: "center",
            position: "relative",
          }}
        >
          {/* Connecting lines (center cross) */}
          {narrationParts.length >= 2 && (
            <>
              {/* Horizontal center line */}
              <div
                style={{
                  position: "absolute",
                  top: "50%",
                  left: "15%",
                  right: "15%",
                  height: 0,
                }}
              >
                <ConnectingLine
                  frame={frame}
                  delay={lineDelay}
                  orientation="horizontal"
                  accentColor={colors.accent}
                />
              </div>
              {/* Vertical center line */}
              {narrationParts.length >= 3 && (
                <div
                  style={{
                    position: "absolute",
                    left: "50%",
                    top: "15%",
                    bottom: "15%",
                    width: 0,
                  }}
                >
                  <ConnectingLine
                    frame={frame}
                    delay={lineDelay + 6}
                    orientation="vertical"
                    accentColor={colors.accent}
                  />
                </div>
              )}
            </>
          )}

          {/* Cards */}
          {narrationParts.map((text, i) => (
            <GlassCard
              key={i}
              text={text}
              index={i}
              accentColor={cardAccentColors[i % cardAccentColors.length]}
              frame={frame}
              fps={fps}
              delay={10 + i * cardStaggerFrames}
              totalCards={narrationParts.length}
              fonts={fonts}
              colors={colors}
            />
          ))}
        </div>

        {/* ── Glass citation cards ── */}
        {scene.citations && scene.citations.length > 0 && (
          <div
            style={{
              position: "absolute",
              bottom: 40,
              left: 90,
              right: 90,
              display: "flex",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            {scene.citations.slice(0, 3).map((cite, i) => (
              <GlassCitationCard
                key={i}
                label={cite.label}
                detail={cite.detail}
                frame={frame}
                fps={fps}
                delay={10 + narrationParts.length * cardStaggerFrames + 8 + i * 5}
                fonts={fonts}
                colors={colors}
              />
            ))}
          </div>
        )}
      </AbsoluteFill>

      {/* ── Bottom vignette ── */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse 120% 50% at 50% 115%, rgba(0,0,0,0.3) 0%, transparent 65%)",
          pointerEvents: "none",
        }}
      />

      <FallbackEvidencePanel scene={scene} brand={brand} />
    </AbsoluteFill>
  );
};
