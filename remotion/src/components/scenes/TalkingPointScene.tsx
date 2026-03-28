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
import { KineticCaptions } from "../shared/KineticCaptions";
import { useLayout } from "../../hooks/useLayout";

interface Props {
  scene: SceneSpec;
  brand: Brand;
}

// ── Safety warning stamp effect ─────────────────────────────────────────
const SAFETY_KEYWORDS = ["HIDDEN", "RECKLESS", "DANGEROUS", "WARNING", "TOXIC", "HARMFUL"];

const SafetyStamp: React.FC<{
  word: string;
  frame: number;
  fps: number;
  delay: number;
  index: number;
  colors: BrandColors;
}> = ({ word, frame, fps, delay, index, colors }) => {
  const localFrame = Math.max(0, frame - delay);

  // Slam-in: starts large and snaps to final size
  const slamProgress = spring({
    frame: localFrame,
    fps,
    config: { damping: 8, stiffness: 300, mass: 0.6 },
  });

  const scale = interpolate(slamProgress, [0, 1], [3.5, 1]);
  const opacity = interpolate(slamProgress, [0, 0.3, 1], [0, 1, 1]);

  // Subtle screen shake on impact (first 4 frames after delay)
  const shakeFrame = Math.max(0, frame - delay);
  const shakeIntensity = interpolate(shakeFrame, [0, 1, 4], [0, 6, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const shakeX = shakeIntensity * Math.sin(shakeFrame * 15);
  const shakeY = shakeIntensity * Math.cos(shakeFrame * 12);

  // Rotation for stamp feel
  const rotations = [-3, 2, -1.5];
  const rotation = rotations[index % rotations.length];

  return (
    <div
      style={{
        display: "inline-block",
        transform: `scale(${scale}) rotate(${rotation}deg) translate(${shakeX}px, ${shakeY}px)`,
        opacity,
        color: colors.danger,
        fontWeight: 900,
        fontSize: 60,
        letterSpacing: 6,
        textTransform: "uppercase",
        textShadow: `0 0 40px ${colors.danger}60, 0 4px 20px rgba(0,0,0,0.5)`,
        border: `4px solid ${colors.danger}`,
        padding: "8px 32px",
        borderRadius: 4,
        margin: "8px 0",
      }}
    >
      {word}
    </div>
  );
};

// ── Sentence card (one-at-a-time display) ───────────────────────────────
const SentenceCard: React.FC<{
  text: string;
  frame: number;
  fps: number;
  enterFrame: number;
  exitFrame: number;
  fonts: { body: string };
  accentColor: string;
  colors: BrandColors;
}> = ({ text, frame, fps, enterFrame, exitFrame, fonts, accentColor, colors }) => {
  const enterLocalFrame = Math.max(0, frame - enterFrame);
  const enterSpring = spring({
    frame: enterLocalFrame,
    fps,
    config: { damping: 16, stiffness: 100 },
  });

  // Fade out near exit
  const fadeOutStart = exitFrame - 8;
  const exitOpacity = interpolate(frame, [fadeOutStart, exitFrame], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const isVisible = frame >= enterFrame && frame < exitFrame + 4;
  if (!isVisible) return null;

  const opacity = Math.min(enterSpring, exitOpacity);
  const translateY = interpolate(enterSpring, [0, 1], [30, 0]);

  // Highlight key phrases: words in ALL CAPS or numbers with units
  const highlightedText = highlightKeyPhrases(text, accentColor, fonts.body);

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px)`,
        padding: "28px 36px",
        backgroundColor: `${colors.text}08`,
        border: `1px solid ${colors.text}12`,
        borderLeft: `3px solid ${accentColor}`,
        borderRadius: 12,
        backdropFilter: "blur(4px)",
        maxWidth: 960,
      }}
    >
      <div
        style={{
          fontFamily: fonts.body,
          fontSize: 30,
          lineHeight: 1.6,
          color: colors.text,
          letterSpacing: 0.2,
        }}
      >
        {highlightedText}
      </div>
    </div>
  );
};

// ── Key phrase highlighting ─────────────────────────────────────────────
function highlightKeyPhrases(
  text: string,
  accentColor: string,
  fontFamily: string
): React.ReactNode {
  // Match: numbers with units (e.g., "300mg", "42%", "3x"), ALL-CAPS words 3+ chars,
  // and quoted phrases
  const pattern = /(\d+[\d,.]*\s*(?:mg|g|kg|ml|%|x|mcg|IU|fold|times))|(\b[A-Z]{3,}\b)|("[^"]+")/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    // Push text before match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    // Push highlighted match
    parts.push(
      <span
        key={match.index}
        style={{
          color: accentColor,
          fontWeight: 700,
          fontFamily,
        }}
      >
        {match[0]}
      </span>
    );
    lastIndex = match.index + match[0].length;
  }
  // Push remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? <>{parts}</> : text;
}

// ── Floating citation card ──────────────────────────────────────────────
const CitationCard: React.FC<{
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
  const translateY = interpolate(slideUp, [0, 1], [40, 0]);

  return (
    <div
      style={{
        opacity: slideUp,
        transform: `translateY(${translateY}px)`,
        backgroundColor: `${colors.accent}0c`,
        border: `1px solid ${colors.accent}25`,
        borderRadius: 10,
        padding: "10px 20px",
        backdropFilter: "blur(8px)",
        display: "flex",
        alignItems: "center",
        gap: 10,
        maxWidth: 340,
      }}
    >
      <div
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          backgroundColor: colors.accent,
          flexShrink: 0,
          boxShadow: `0 0 6px ${colors.accent}60`,
        }}
      />
      <div>
        <span
          style={{
            color: colors.text,
            fontFamily: fonts.body,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          {label}
        </span>
        {detail && (
          <span
            style={{
              color: `${colors.text}70`,
              fontFamily: fonts.body,
              fontSize: 14,
              marginLeft: 6,
            }}
          >
            {detail}
          </span>
        )}
      </div>
    </div>
  );
};

// ── Determine if scene is a safety warning ──────────────────────────────
function isSafetyWarning(heading: string): boolean {
  const upper = heading.toUpperCase();
  return (
    upper.includes("SAFETY WARNING") ||
    upper.includes("SAFETY CONCERN") ||
    upper.includes("DANGER") ||
    // Check for stamp pattern: multiple caps words separated by slashes or pipes
    /[A-Z]{4,}\s*[/|]\s*[A-Z]{4,}/.test(heading)
  );
}

function extractStampWords(heading: string): string[] {
  // Extract words that appear in caps, separated by / or |
  const slashWords = heading.match(/[A-Z]{3,}/g);
  if (slashWords && slashWords.length >= 2) {
    return slashWords.filter((w) =>
      SAFETY_KEYWORDS.some((kw) => w.toUpperCase().includes(kw))
    );
  }
  return [];
}

// ── Main component ──────────────────────────────────────────────────────
export const TalkingPointScene: React.FC<Props> = ({ scene, brand }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { colors, fonts } = brand;
  const layout = useLayout();

  const isSafety = isSafetyWarning(scene.heading);
  const stampWords = isSafety ? extractStampWords(scene.heading) : [];
  const showStampMode = stampWords.length >= 2;

  // Split narration into sentences
  const sentences = scene.narration
    .split(/(?<=[.!?])\s+/)
    .filter((s) => s.trim().length > 0)
    .slice(0, 6);

  // Calculate timing: use actual Sequence duration (not scene.durationFrames which may differ)
  const totalDuration = durationInFrames;
  const headingSettleFrame = 20;
  const citationReserveFrames = 30;
  const contentStartFrame = headingSettleFrame + 5;
  const contentEndFrame = totalDuration - citationReserveFrames;
  const contentDuration = contentEndFrame - contentStartFrame;
  const sentenceDuration = sentences.length > 0 ? contentDuration / sentences.length : contentDuration;

  // Heading animation
  const headingSpring = spring({
    frame,
    fps,
    config: { damping: 16, stiffness: 100 },
  });
  const headingSlideX = interpolate(headingSpring, [0, 1], [-50, 0]);

  // Ken Burns on background — alternate zoom in/out per scene
  const sceneNum = parseInt(scene.sceneId.replace(/\D/g, ""), 10) || 0;
  const zoomIn = sceneNum % 2 === 0;
  const bgScale = interpolate(
    frame,
    [0, totalDuration],
    zoomIn ? [1.0, 1.15] : [1.15, 1.0],
    { extrapolateRight: "clamp" }
  );
  const origins = ["center center", "top left", "bottom right", "top right", "bottom left"];
  const bgOrigin = origins[sceneNum % origins.length];

  return (
    <AbsoluteFill style={{ backgroundColor: colors.primary }}>
      {/* ── Background image at 65% opacity with alternating Ken Burns ── */}
      {scene.imagePath && (
        <Img
          src={staticFile(scene.imagePath)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            position: "absolute",
            opacity: 0.65,
            transform: `scale(${bgScale})`,
            transformOrigin: bgOrigin,
          }}
        />
      )}

      {/* ── Gradient overlay — light enough to let background show clearly ── */}
      <AbsoluteFill
        style={{
          background: showStampMode
            ? `linear-gradient(160deg, ${colors.primary}c0 0%, #1a0a0a 100%)`
            : `linear-gradient(160deg, ${colors.primary}50 0%, ${colors.secondary || colors.primary}30 50%, ${colors.primary}70 100%)`,
        }}
      />

      {/* ── Grain ── */}
      <GrainOverlay />

      {/* ── Content ── */}
      <AbsoluteFill style={{ padding: layout.contentPadding }}>
        {/* ── Heading with accent border ── */}
        {!showStampMode && (
          <h2
            style={{
              color: colors.text,
              fontFamily: fonts.heading,
              fontSize: layout.h2FontSize,
              fontWeight: 800,
              marginBottom: 44,
              marginTop: 10,
              transform: `translateX(${headingSlideX}px)`,
              opacity: headingSpring,
              borderLeft: `4px solid ${colors.accent}`,
              paddingLeft: 28,
              lineHeight: 1.2,
              letterSpacing: -0.5,
              textShadow: "0 2px 16px rgba(0,0,0,0.3)",
            }}
          >
            {scene.heading}
          </h2>
        )}

        {/* ── Safety stamp mode ── */}
        {showStampMode && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 24,
              marginTop: 20,
            }}
          >
            {/* Section label above stamps */}
            <div
              style={{
                color: `${colors.danger}90`,
                fontFamily: fonts.body,
                fontSize: 18,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: 6,
                marginBottom: 16,
                opacity: interpolate(frame, [0, 10], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              Safety Warning
            </div>
            {stampWords.map((word, i) => (
              <SafetyStamp
                key={i}
                word={word}
                frame={frame}
                fps={fps}
                delay={8 + i * 14}
                index={i}
                colors={colors}
              />
            ))}
          </div>
        )}

        {/* ── Narration text — sentence cards fallback (when no wordTimings) ── */}
        {!(scene.wordTimings && scene.wordTimings.length > 0) && (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              justifyContent: showStampMode ? "flex-start" : "center",
              gap: 16,
              marginTop: showStampMode ? 16 : 0,
            }}
          >
            {sentences.map((sentence, i) => {
              const enterFrame = contentStartFrame + i * sentenceDuration;
              const exitFrame = enterFrame + sentenceDuration;
              return (
                <SentenceCard
                  key={i}
                  text={sentence}
                  frame={frame}
                  fps={fps}
                  enterFrame={enterFrame}
                  exitFrame={exitFrame}
                  fonts={fonts}
                  accentColor={showStampMode ? colors.danger : colors.accent}
                  colors={colors}
                />
              );
            })}
          </div>
        )}

        {/* ── Floating citation cards ── */}
        {scene.citations && scene.citations.length > 0 && (
          <div
            style={{
              position: "absolute",
              bottom: layout.bottomInset,
              left: layout.edgeInset,
              right: layout.edgeInset,
              display: "flex",
              gap: 14,
              flexWrap: "wrap",
            }}
          >
            {scene.citations.slice(0, 4).map((cite, i) => (
              <CitationCard
                key={i}
                label={cite.label}
                detail={cite.detail}
                frame={frame}
                fps={fps}
                delay={contentEndFrame + i * 6}
                fonts={fonts}
                colors={colors}
              />
            ))}
          </div>
        )}
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
            accentColor={showStampMode ? colors.danger : colors.accent}
          />
        </div>
      )}
    </AbsoluteFill>
  );
};
