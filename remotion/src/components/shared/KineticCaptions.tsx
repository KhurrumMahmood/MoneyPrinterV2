import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";
import type { WordTiming, BrandColors, BrandFonts } from "../../types";
import { useLayout } from "../../hooks/useLayout";

interface Props {
  wordTimings: WordTiming[];
  colors: BrandColors;
  fonts: BrandFonts;
  accentColor?: string;
}

interface SentenceBoundary {
  startIdx: number;
  endIdx: number; // inclusive
}

function computeSentences(wordTimings: WordTiming[]): SentenceBoundary[] {
  const sentences: SentenceBoundary[] = [];
  let sentenceStart = 0;

  for (let i = 0; i < wordTimings.length; i++) {
    const word = wordTimings[i].word;
    const lastChar = word[word.length - 1];
    const isSentenceEnd = lastChar === "." || lastChar === "!" || lastChar === "?";

    if (isSentenceEnd || i === wordTimings.length - 1) {
      sentences.push({ startIdx: sentenceStart, endIdx: i });
      sentenceStart = i + 1;
    }
  }

  return sentences;
}

export const KineticCaptions: React.FC<Props> = ({
  wordTimings,
  colors,
  fonts,
  accentColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const layout = useLayout();
  const accent = accentColor || colors.accent;

  if (!wordTimings || wordTimings.length === 0) return null;

  const currentTimeMs = (frame / fps) * 1000;

  // Find the index of the current word being spoken
  let currentWordIndex = -1;
  for (let i = 0; i < wordTimings.length; i++) {
    if (currentTimeMs >= wordTimings[i].startMs && currentTimeMs < wordTimings[i].endMs) {
      currentWordIndex = i;
      break;
    }
    // If between words, show the most recently spoken word
    if (currentTimeMs >= wordTimings[i].endMs &&
        (i + 1 >= wordTimings.length || currentTimeMs < wordTimings[i + 1].startMs)) {
      currentWordIndex = i;
    }
  }

  if (currentWordIndex < 0 && currentTimeMs >= wordTimings[0].startMs) {
    currentWordIndex = wordTimings.length - 1;
  }

  // Before first word, don't show anything
  if (currentWordIndex < 0) return null;

  // Find the current sentence
  const sentences = computeSentences(wordTimings);
  const currentSentence = sentences.find(
    (s) => currentWordIndex >= s.startIdx && currentWordIndex <= s.endIdx
  );

  if (!currentSentence) return null;

  // Show words from sentence start through current word
  const visibleWords = wordTimings.slice(currentSentence.startIdx, currentWordIndex + 1);

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        alignItems: "center",
        gap: "8px 14px",
        maxWidth: layout.maxCaptionWidth,
      }}
    >
      {visibleWords.map((wt, i) => {
        const globalIndex = currentSentence.startIdx + i;
        const isCurrentWord = globalIndex === currentWordIndex;

        // Spring entrance when word first appears
        const wordStartFrame = Math.round((wt.startMs / 1000) * fps);
        const localFrame = Math.max(0, frame - wordStartFrame);

        const entranceSpring = spring({
          frame: localFrame,
          fps,
          config: { damping: 14, stiffness: 180, mass: 0.6 },
        });

        const opacity = isCurrentWord ? 1 : 0.8;
        const wordColor = isCurrentWord ? accent : colors.text;
        const fontWeight = isCurrentWord ? 900 : 600;

        return (
          <span
            key={`${globalIndex}-${wt.word}`}
            style={{
              display: "inline-block",
              transform: `scale(${entranceSpring})`,
              opacity,
              color: wordColor,
              fontFamily: fonts.heading,
              fontSize: layout.captionFontSize,
              fontWeight,
              lineHeight: 1.4,
              letterSpacing: -0.3,
              textShadow: isCurrentWord
                ? `0 0 20px ${accent}40, 0 2px 12px rgba(0,0,0,0.5)`
                : "0 2px 10px rgba(0,0,0,0.5)",
            }}
          >
            {wt.word}
          </span>
        );
      })}
    </div>
  );
};
