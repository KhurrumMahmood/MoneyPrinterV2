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
import { EvidenceBadge } from "../shared/EvidenceBadge";
import { FallbackEvidencePanel } from "../shared/FallbackEvidencePanel";
import { StructuredVisualLayer } from "../shared/StructuredVisualLayer";
import { getScenePalette } from "../shared/sceneStyle";
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
        justifyContent: "flex-start",
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
        textAlign: "left",
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
  const palette = getScenePalette({ ...scene, sceneRegister: "hook" }, brand);
  const showImageLedPortrait = layout.isPortrait && Boolean(scene.imagePath);

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
    <AbsoluteFill style={{ backgroundColor: palette.background }}>
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
        <GradientMeshBackground
          frame={frame}
          colors={{
            ...colors,
            primary: palette.background,
            secondary: palette.backgroundAlt,
            accent: palette.accent,
            text: palette.text,
            textSecondary: palette.textMuted,
          }}
        />
      )}

      {/* ── Layer 2: Dark gradient overlay (bottom-heavy) ── */}
      <AbsoluteFill
        style={{
          background: scene.imagePath
            ? showImageLedPortrait
              ? `linear-gradient(180deg, ${palette.background}8a 0%, ${palette.background}18 26%, ${palette.background}18 62%, ${palette.background}d9 100%)`
              : `linear-gradient(180deg, ${palette.background}85 0%, ${palette.background}35 24%, ${palette.background}c5 68%, ${palette.background}f2 100%)`
            : `linear-gradient(180deg, transparent 0%, ${palette.background}55 32%, ${palette.background}e8 100%)`,
        }}
      />

      {!showImageLedPortrait ? (
        <StructuredVisualLayer
          scene={{ ...scene, sceneRegister: "hook" }}
          brand={brand}
          layout={layout.isPortrait ? "full" : "split"}
          emphasize={layout.isPortrait ? "center" : "right"}
        />
      ) : null}

      {/* ── Layer 3: Grain overlay ── */}
      <GrainOverlay />

      <EvidenceBadge scene={scene} brand={brand} />

      {/* ── Layer 4: Content ── */}
      <AbsoluteFill
        style={{
          justifyContent: "flex-start",
          alignItems: "flex-start",
          padding: layout.titlePadding,
          paddingTop: showImageLedPortrait ? 88 : layout.isPortrait ? 70 : 98,
        }}
      >
        <div
          style={{
            color: palette.textMuted,
            fontFamily: fonts.body,
            fontSize: 15,
            fontWeight: 700,
            letterSpacing: 3.2,
            textTransform: "uppercase",
            marginBottom: 18,
            opacity: interpolate(frame, [0, 12], [0, 0.92], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          Evidence Review
        </div>

        {/* Word-by-word heading reveal */}
        <div style={{ maxWidth: showImageLedPortrait ? 720 : layout.isPortrait ? 640 : 760 }}>
          <WordReveal
            text={scene.heading}
            frame={frame}
            fps={fps}
            fonts={fonts}
            colors={{
              ...colors,
              text: palette.text,
              accent: palette.accent,
              textSecondary: palette.textMuted,
            }}
            startFrame={8}
          />
        </div>

        {/* Animated accent line */}
        <div
          style={{
            width: 132,
            height: 3,
            backgroundColor: "transparent",
            marginTop: 26,
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
              background: `linear-gradient(90deg, ${palette.accent}, ${palette.accentAlt})`,
              borderRadius: 2,
              boxShadow: `0 0 16px ${palette.accent}66`,
            }}
          />
        </div>

        <div
          style={{
            display: "flex",
            gap: 14,
            flexWrap: "wrap",
            marginTop: 22,
            maxWidth: 540,
          }}
        >
          {["Same bagel", "Same juice", "Different curve"].map((keyword) => (
            <div
              key={keyword}
              style={{
                padding: "10px 18px",
                borderRadius: 999,
                border: `1px solid ${palette.accent}40`,
                color: palette.textMuted,
                background: `${palette.surface}cc`,
                fontSize: 15,
                fontWeight: 700,
                letterSpacing: 1,
                textTransform: "uppercase",
              }}
            >
              {keyword}
            </div>
          ))}
        </div>

        {/* Typewriter fallback (when no word timings) */}
        {!(scene.wordTimings && scene.wordTimings.length > 0) &&
        firstSentence &&
        !showImageLedPortrait ? (
          <div
            style={{
              marginTop: 26,
              maxWidth: showImageLedPortrait ? 520 : layout.isPortrait ? 420 : 520,
              padding: "20px 24px",
              borderRadius: 22,
              background: `${palette.surface}c8`,
              border: `1px solid ${palette.accent}18`,
              boxShadow: `0 22px 48px ${palette.background}40`,
            }}
          >
            <TypewriterText
              text={firstSentence}
              frame={frame}
              startFrame={subtitleStartFrame}
              fonts={fonts}
              colors={{
                ...colors,
                text: palette.text,
                accent: palette.accent,
              }}
            />
          </div>
        ) : null}

        <div
          style={{
            marginTop: 24,
            padding: "14px 18px",
            borderRadius: 18,
            background: `${palette.accentAlt}14`,
            border: `1px solid ${palette.accentAlt}26`,
            color: palette.text,
            fontFamily: fonts.body,
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: 0.2,
            maxWidth: showImageLedPortrait ? 420 : layout.isPortrait ? 360 : 420,
            opacity: interpolate(frame, [18, 34], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          We checked dozens of blood sugar hacks. Three held up.
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
            colors={colors}
            fonts={fonts}
          />
        </div>
      )}
      <FallbackEvidencePanel scene={scene} brand={brand} />
    </AbsoluteFill>
  );
};
