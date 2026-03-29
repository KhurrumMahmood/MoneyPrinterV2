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
import { EvidenceBadge } from "../shared/EvidenceBadge";
import { FallbackEvidencePanel } from "../shared/FallbackEvidencePanel";
import { StructuredVisualLayer } from "../shared/StructuredVisualLayer";
import { deriveKeywords, getScenePalette, resolveSceneRegister } from "../shared/sceneStyle";
import { useLayout } from "../../hooks/useLayout";

interface Props {
  scene: SceneSpec;
  brand: Brand;
}

const RULE_LABELS = [
  {
    title: "Pair",
    detail: "Put protein, fat, or fiber next to the carbs.",
  },
  {
    title: "Order",
    detail: "Veg first. Protein next. Carbs last.",
  },
  {
    title: "Choose",
    detail: "Keep the grain intact whenever you can.",
  },
];

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
        padding: "24px 28px",
        backgroundColor: `${colors.text}07`,
        border: `1px solid ${colors.text}10`,
        borderLeft: `3px solid ${accentColor}`,
        borderRadius: 18,
        backdropFilter: "blur(6px)",
        maxWidth: 720,
        boxShadow: "0 22px 42px rgba(0,0,0,0.18)",
      }}
    >
      <div
        style={{
          fontFamily: fonts.body,
          fontSize: 28,
          lineHeight: 1.55,
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

function buildSentenceChunks(narration: string): string[] {
  const raw = narration
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => sentence.trim())
    .filter((sentence) => sentence.length > 0);

  const merged: string[] = [];
  for (let index = 0; index < raw.length; index += 1) {
    const sentence = raw[index];
    const shortSentence =
      sentence.length < 26 || sentence.split(/\s+/).length <= 3;
    const next = raw[index + 1];

    if (shortSentence && merged.length === 0 && next) {
      merged.push(`${sentence} ${next}`.trim());
      index += 1;
      continue;
    }

    if (shortSentence && merged.length > 0 && merged[merged.length - 1].length < 110) {
      merged[merged.length - 1] = `${merged[merged.length - 1]} ${sentence}`.trim();
      continue;
    }

    merged.push(sentence);
  }

  return merged;
}

function buildImageLeadChipLabels(scene: SceneSpec): string[] {
  const text = `${scene.heading} ${scene.narration} ${scene.visualNotes}`.toLowerCase();

  if (text.includes("fat") || text.includes("fiber")) {
    return ["Avocado", "Nuts", "Beans", "Seeds"];
  }

  if (text.includes("protein")) {
    return ["Egg", "Tofu", "Chicken", "Shake"];
  }

  if (text.includes("order")) {
    return ["Veg First", "Protein", "Carbs Last"];
  }

  if (text.includes("grain") || text.includes("fruit")) {
    return ["Intact Grain", "Whole Fruit", "Less Processed"];
  }

  const fallback = scene.keywords && scene.keywords.length > 0
    ? scene.keywords
    : deriveKeywords(scene);

  return fallback
    .filter((item) => !/^(first|rules?|rapid-fire|breakdown)$/i.test(item))
    .slice(0, 4);
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

const RulesOverview: React.FC<{
  frame: number;
  fps: number;
  accent: string;
  text: string;
}> = ({ frame, fps, accent, text }) => (
  <div
    style={{
      display: "flex",
      flexDirection: "column",
      gap: 16,
      maxWidth: 500,
      marginTop: 26,
    }}
  >
    {RULE_LABELS.map((rule, index) => {
      const appear = spring({
        frame: Math.max(0, frame - (10 + index * 6)),
        fps,
        config: { damping: 18, stiffness: 110, mass: 0.85 },
      });

      return (
        <div
          key={rule.title}
          style={{
            opacity: appear,
            transform: `translateY(${interpolate(appear, [0, 1], [28, 0])}px)`,
            padding: "18px 22px",
            borderRadius: 24,
            background: `linear-gradient(90deg, rgba(255,255,255,0.07), rgba(255,255,255,0.03))`,
            border: `1px solid ${accent}28`,
            boxShadow: `0 18px 36px ${accent}12`,
          }}
        >
          <div
            style={{
              color: "#fff6e9",
              fontSize: 34,
              fontWeight: 900,
              letterSpacing: -0.6,
              marginBottom: 6,
            }}
          >
            {rule.title}
          </div>
          <div
            style={{
              color: "rgba(255,244,228,0.86)",
              fontSize: 20,
              lineHeight: 1.45,
            }}
          >
            {rule.detail}
          </div>
        </div>
      );
    })}
    <div
      style={{
        marginTop: 6,
        padding: "16px 20px",
        borderRadius: 20,
        background: `${accent}16`,
        border: `1px solid ${accent}2e`,
        color: "#fff7eb",
        fontSize: 19,
        fontWeight: 700,
        lineHeight: 1.45,
      }}
    >
      {text}
    </div>
  </div>
);

const ImageLeadChipRow: React.FC<{
  items: string[];
  palette: BrandColors;
}> = ({ items, palette }) => (
  <div
    style={{
      display: "flex",
      flexWrap: "wrap",
      gap: 12,
      maxWidth: 760,
      marginTop: 6,
      marginBottom: 18,
    }}
  >
    {items.map((item, index) => (
      <div
        key={item}
        style={{
          padding: "10px 16px",
          borderRadius: 999,
          background: index % 2 === 0 ? `${palette.accent}20` : `${palette.textSecondary}1c`,
          border:
            index % 2 === 0
              ? `1px solid ${palette.accent}38`
              : `1px solid ${palette.textSecondary}38`,
          color: palette.text,
          fontSize: 15,
          fontWeight: 800,
          letterSpacing: 1,
          textTransform: "uppercase",
          boxShadow: "0 18px 40px rgba(0,0,0,0.18)",
          backdropFilter: "blur(12px)",
        }}
      >
        {item}
      </div>
    ))}
  </div>
);

// ── Main component ──────────────────────────────────────────────────────
export const TalkingPointScene: React.FC<Props> = ({ scene, brand }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { colors, fonts } = brand;
  const layout = useLayout();
  const palette = getScenePalette(scene, brand);
  const register = resolveSceneRegister(scene);
  const keywords = deriveKeywords(scene);

  const isSafety = isSafetyWarning(scene.heading);
  const stampWords = isSafety ? extractStampWords(scene.heading) : [];
  const showStampMode = stampWords.length >= 2;
  const isRulesScene = scene.heading.toLowerCase().includes("3 rules");
  const isRapidFireScene = scene.heading.toLowerCase().startsWith("rapid-fire");

  // Split narration into sentences
  const sentences = buildSentenceChunks(scene.narration).slice(0, 5);

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
  const showImageLedPortrait =
    layout.isPortrait && Boolean(scene.imagePath) && !showStampMode;
  const leadChipLabels = isRulesScene
    ? ["Pair", "Order", "Choose"]
    : buildImageLeadChipLabels(scene);

  const contentColumnWidth = layout.isPortrait
    ? showImageLedPortrait
      ? "100%"
      : isRulesScene
      ? "100%"
      : "54%"
    : isRulesScene
      ? "36%"
      : register === "clinical"
        ? "46%"
        : "40%";

  return (
    <AbsoluteFill style={{ backgroundColor: palette.background }}>
      {/* ── Background image at 65% opacity with alternating Ken Burns ── */}
      {scene.imagePath && (
        <Img
          src={staticFile(scene.imagePath)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            position: "absolute",
            opacity: showImageLedPortrait ? 1 : 0.65,
            transform: `scale(${bgScale})`,
            transformOrigin: bgOrigin,
          }}
        />
      )}

      {!showImageLedPortrait ? (
        <StructuredVisualLayer
          scene={scene}
          brand={brand}
          layout={layout.isPortrait ? "full" : "split"}
          emphasize={layout.isPortrait ? "center" : "right"}
        />
      ) : null}

      {/* ── Gradient overlay — light enough to let background show clearly ── */}
      <AbsoluteFill
        style={{
          background: showStampMode
            ? `linear-gradient(160deg, ${palette.background}c4 0%, ${palette.backgroundAlt}ea 100%)`
            : showImageLedPortrait
              ? `linear-gradient(180deg, ${palette.background}94 0%, ${palette.background}14 28%, ${palette.background}10 64%, ${palette.background}dd 100%)`
              : `linear-gradient(160deg, ${palette.background}58 0%, ${palette.backgroundAlt}2c 52%, ${palette.background}88 100%)`,
        }}
      />

      {/* ── Grain ── */}
      <GrainOverlay />

      <EvidenceBadge scene={scene} brand={brand} />

      {/* ── Content ── */}
      <AbsoluteFill style={{ padding: layout.contentPadding }}>
        {/* ── Heading with accent border ── */}
        {!showStampMode && (
          <div style={{ maxWidth: showImageLedPortrait ? "74%" : isRulesScene ? "34%" : "44%" }}>
            {isRapidFireScene ? (
              <div
                style={{
                  color: palette.textMuted,
                  fontFamily: fonts.body,
                  fontSize: 14,
                  fontWeight: 700,
                  letterSpacing: 3,
                  textTransform: "uppercase",
                  marginTop: 6,
                  marginBottom: 18,
                  opacity: headingSpring,
                }}
              >
                Rapid-Fire Breakdown
              </div>
            ) : null}
            <h2
              style={{
                color: palette.text,
                fontFamily: fonts.heading,
                fontSize: layout.h2FontSize,
                fontWeight: 800,
                marginBottom: isRulesScene ? 28 : 44,
                marginTop: 10,
                transform: `translateX(${headingSlideX}px)`,
                opacity: headingSpring,
                borderLeft: `4px solid ${palette.accent}`,
                paddingLeft: 28,
                lineHeight: 1.15,
                letterSpacing: -0.6,
                textShadow: "0 2px 16px rgba(0,0,0,0.3)",
                maxWidth: "100%",
              }}
            >
              {scene.heading}
            </h2>
            {showImageLedPortrait && leadChipLabels.length > 0 ? (
              <ImageLeadChipRow
                items={leadChipLabels}
                palette={{
                  ...colors,
                  text: palette.text,
                  textSecondary: palette.textMuted,
                  accent: palette.accent,
                  danger: palette.danger,
                }}
              />
            ) : null}
          </div>
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
              justifyContent: showStampMode ? "flex-start" : layout.isPortrait ? "flex-end" : "center",
              gap: 16,
              marginTop: showStampMode ? 16 : 0,
              maxWidth: showImageLedPortrait ? "72%" : contentColumnWidth,
              width: layout.isPortrait ? "100%" : undefined,
            }}
          >
            {isRulesScene ? (
              layout.isPortrait ? (
                <div
                  style={{
                    marginTop: "auto",
                    maxWidth: showImageLedPortrait ? 620 : 520,
                    padding: showImageLedPortrait ? "22px 24px" : "18px 20px",
                    borderRadius: 22,
                    background: showImageLedPortrait
                      ? `${palette.background}ba`
                      : `${palette.surface}d0`,
                    border: `1px solid ${palette.accent}${showImageLedPortrait ? "30" : "20"}`,
                    color: palette.text,
                    fontFamily: fonts.body,
                    fontSize: showImageLedPortrait ? 28 : 24,
                    fontWeight: 700,
                    lineHeight: 1.45,
                    boxShadow: showImageLedPortrait
                      ? "0 24px 56px rgba(0,0,0,0.24)"
                      : "0 18px 40px rgba(0,0,0,0.18)",
                  }}
                >
                  We checked 37 blood sugar hacks. These 3 ideas kept surviving.
                </div>
              ) : (
                <RulesOverview
                  frame={frame}
                  fps={fps}
                  accent={palette.accent}
                  text="We checked 37 blood sugar hacks. These 3 ideas kept surviving."
                />
              )
            ) : (
              sentences.map((sentence, i) => {
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
                    accentColor={showStampMode ? palette.danger : palette.accent}
                    colors={{
                      ...colors,
                      text: palette.text,
                      textSecondary: palette.textMuted,
                      accent: palette.accent,
                      danger: palette.danger,
                    }}
                  />
                );
              })
            )}
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
                colors={{
                  ...colors,
                  text: palette.text,
                  textSecondary: palette.textMuted,
                  accent: palette.accent,
                }}
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
              danger: palette.danger,
            }}
            fonts={fonts}
            accentColor={showStampMode ? palette.danger : palette.accent}
          />
        </div>
      )}

      <FallbackEvidencePanel scene={scene} brand={brand} />
    </AbsoluteFill>
  );
};
