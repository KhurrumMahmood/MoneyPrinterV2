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
import { GradientMeshBackground } from "../shared/GradientMeshBackground";
import { KineticCaptions } from "../shared/KineticCaptions";
import { useLayout } from "../../hooks/useLayout";

interface Props {
  scene: SceneSpec;
  brand: Brand;
}

// ── Word-by-word reveal ─────────────────────────────────────────────────
const WordReveal: React.FC<{
  text: string;
  frame: number;
  fps: number;
  fonts: { heading: string };
  colors: BrandColors;
  startFrame?: number;
}> = ({ text, frame, fps, fonts, colors, startFrame = 0 }) => {
  const words = text.split(/\s+/);
  const staggerFrames = 4;

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        gap: "0 20px",
        maxWidth: 960,
        lineHeight: 1.15,
      }}
    >
      {words.map((word, i) => {
        const wordDelay = startFrame + i * staggerFrames;
        const localFrame = Math.max(0, frame - wordDelay);
        const wordSpring = spring({
          frame: localFrame,
          fps,
          config: { damping: 18, stiffness: 120, mass: 0.8 },
        });
        const yOffset = interpolate(wordSpring, [0, 1], [35, 0]);
        const wordOpacity = interpolate(wordSpring, [0, 1], [0, 1]);

        return (
          <span
            key={i}
            style={{
              color: colors.text,
              fontFamily: fonts.heading,
              fontSize: 64,
              fontWeight: 900,
              letterSpacing: -1,
              transform: `translateY(${yOffset}px)`,
              opacity: wordOpacity,
              display: "inline-block",
              textShadow: "0 4px 30px rgba(0,0,0,0.5)",
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};

// ── Typewriter subtitle ─────────────────────────────────────────────────
const TypewriterText: React.FC<{
  text: string;
  frame: number;
  startFrame: number;
  fonts: { body: string };
  colors: BrandColors;
}> = ({ text, frame, startFrame, fonts, colors }) => {
  const elapsed = Math.max(0, frame - startFrame);
  // ~2 characters per frame for a brisk but readable type speed
  const charsToShow = Math.min(Math.floor(elapsed * 2), text.length);
  const visibleText = text.slice(0, charsToShow);
  const showCursor = elapsed > 0 && charsToShow < text.length;
  const fadeIn = interpolate(elapsed, [0, 6], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <p
      style={{
        color: `${colors.text}cc`,
        fontFamily: fonts.body,
        fontSize: 30,
        textAlign: "center",
        maxWidth: 960,
        lineHeight: 1.7,
        opacity: fadeIn,
        margin: 0,
        letterSpacing: 0.3,
        textShadow: "0 2px 12px rgba(0,0,0,0.4)",
      }}
    >
      {visibleText}
      {showCursor && (
        <span style={{ color: colors.accent, fontWeight: 300 }}>|</span>
      )}
    </p>
  );
};

// ── Main component ──────────────────────────────────────────────────────
export const TitleScene: React.FC<Props> = ({ scene, brand }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { colors, fonts } = brand;
  const layout = useLayout();

  // Timing
  const words = scene.heading.split(/\s+/);
  const headingCompleteFrame = 8 + words.length * 4 + 10; // start + stagger + settle
  const subtitleStartFrame = headingCompleteFrame + 5;
  const lineStartFrame = headingCompleteFrame - 5;

  // Ken Burns zoom on background image — slow push-in from bottom
  const kenBurnsScale = interpolate(frame, [0, durationInFrames], [1.0, 1.2], {
    extrapolateRight: "clamp",
  });

  // Accent line draw animation
  const lineProgress = interpolate(
    frame,
    [lineStartFrame, lineStartFrame + 25],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }
  );

  // First sentence of narration for subtitle
  const firstSentence = scene.narration
    ? scene.narration.split(/(?<=[.!?])\s+/)[0] || ""
    : "";

  return (
    <AbsoluteFill style={{ backgroundColor: colors.primary }}>
      {/* ── Layer 1: Background image with Ken Burns ── */}
      {scene.imagePath ? (
        <Img
          src={staticFile(scene.imagePath)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            position: "absolute",
            transform: `scale(${kenBurnsScale})`,
            transformOrigin: "bottom center",
          }}
        />
      ) : (
        <GradientMeshBackground frame={frame} colors={colors} />
      )}

      {/* ── Layer 2: Dark gradient overlay (bottom-heavy) ── */}
      <AbsoluteFill
        style={{
          background: scene.imagePath
            ? `linear-gradient(180deg, ${colors.primary}90 0%, ${colors.primary}40 30%, ${colors.primary}b0 65%, ${colors.primary}f5 100%)`
            : `linear-gradient(180deg, transparent 0%, ${colors.primary}60 100%)`,
        }}
      />

      {/* ── Layer 3: Grain overlay ── */}
      <GrainOverlay />

      {/* ── Layer 4: Content ── */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: layout.titlePadding,
        }}
      >
        {/* Word-by-word heading reveal */}
        <WordReveal
          text={scene.heading}
          frame={frame}
          fps={fps}
          fonts={fonts}
          colors={colors}
          startFrame={8}
        />

        {/* Animated accent line */}
        <div
          style={{
            width: layout.dividerWidth,
            height: 3,
            backgroundColor: "transparent",
            marginTop: 36,
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: `${lineProgress * 100}%`,
              height: "100%",
              background: `linear-gradient(90deg, ${colors.accent}, ${colors.accent}80)`,
              borderRadius: 2,
              boxShadow: `0 0 12px ${colors.accent}60`,
            }}
          />
        </div>

        {/* Typewriter fallback (when no word timings) */}
        {!(scene.wordTimings && scene.wordTimings.length > 0) && firstSentence ? (
          <div style={{ marginTop: 32 }}>
            <TypewriterText
              text={firstSentence}
              frame={frame}
              startFrame={subtitleStartFrame}
              fonts={fonts}
              colors={colors}
            />
          </div>
        ) : null}
      </AbsoluteFill>

      {/* ── Bottom caption gradient ── */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "35%",
          background: `linear-gradient(transparent, ${colors.primary}dd)`,
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
            colors={colors}
            fonts={fonts}
          />
        </div>
      )}
    </AbsoluteFill>
  );
};
