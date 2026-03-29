import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { Brand, SceneSpec } from "../../types";
import { deriveKeywords, getScenePalette, resolveSceneRegister } from "./sceneStyle";

interface Props {
  scene: SceneSpec;
  brand: Brand;
  layout?: "full" | "split";
  emphasize?: "left" | "right" | "center";
}

const curvePath = (height: number, strength: "spike" | "flat") =>
  strength === "spike"
    ? `M 0 ${height} C 50 ${height - 10}, 130 ${height - 130}, 190 26 S 280 38, 360 ${height - 40}`
    : `M 0 ${height} C 60 ${height - 8}, 125 ${height - 55}, 185 ${height - 70} S 286 ${height - 44}, 360 ${height - 54}`;

const chipGroups = {
  protein: ["Egg", "Tofu", "Chicken", "Shake"],
  fat: ["Avocado", "Nuts", "Fiber", "Seeds"],
  order: ["Veg First", "Protein", "Carbs Last"],
  grains: ["Steel-Cut", "Whole Fruit", "Intact Grain"],
  acid: ["Dilute", "Straw", "Meds"],
  lentils: ["Dal", "Soup", "$1.50", "Fiber"],
};

const keywordToChipSet = (scene: SceneSpec): string[] => {
  const text = `${scene.heading} ${scene.narration}`.toLowerCase();
  if (text.includes("protein")) return chipGroups.protein;
  if (text.includes("fat") || text.includes("fiber")) return chipGroups.fat;
  if (text.includes("order")) return chipGroups.order;
  if (text.includes("vinegar")) return chipGroups.acid;
  if (text.includes("grain") || text.includes("fruit")) return chipGroups.grains;
  if (text.includes("lentil")) return chipGroups.lentils;
  return deriveKeywords(scene);
};

const detectMealLabels = (
  scene: SceneSpec
): { before: string[]; after: string[] } | null => {
  const text = `${scene.heading} ${scene.narration} ${scene.visualNotes}`.toLowerCase();
  if (text.includes("bagel") && text.includes("orange juice")) {
    return {
      before: ["Bagel", "Orange Juice"],
      after: ["Bagel", "Orange Juice", "Peanut Butter"],
    };
  }

  if (text.includes("carbs") && (text.includes("protein") || text.includes("fiber"))) {
    return {
      before: ["Carbs"],
      after: ["Carbs", "Protein", "Fiber"],
    };
  }

  return null;
};

type FoodKind =
  | "bagel"
  | "orange-juice"
  | "peanut-butter"
  | "egg"
  | "tofu"
  | "chicken"
  | "shake"
  | "avocado"
  | "nuts"
  | "fiber"
  | "grain"
  | "leaf";

const labelToFoodKind = (label: string): FoodKind => {
  const normalized = label.toLowerCase();
  if (normalized.includes("bagel")) return "bagel";
  if (normalized.includes("orange")) return "orange-juice";
  if (normalized.includes("peanut")) return "peanut-butter";
  if (normalized.includes("protein")) return "chicken";
  if (normalized.includes("egg")) return "egg";
  if (normalized.includes("tofu")) return "tofu";
  if (normalized.includes("chicken")) return "chicken";
  if (normalized.includes("shake")) return "shake";
  if (normalized.includes("avocado")) return "avocado";
  if (normalized.includes("nut")) return "nuts";
  if (normalized.includes("carb")) return "grain";
  if (normalized.includes("fiber")) return "fiber";
  if (normalized.includes("grain")) return "grain";
  return "leaf";
};

const FoodGlyph: React.FC<{
  kind: FoodKind;
  size?: number;
}> = ({ kind, size = 28 }) => {
  const shell = {
    width: size,
    height: size,
    position: "relative" as const,
    flexShrink: 0,
  };

  if (kind === "bagel") {
    return (
      <div style={shell}>
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            background: "linear-gradient(180deg, #d1a05d, #8f6230)",
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: size * 0.26,
            borderRadius: "50%",
            background: "#162335",
          }}
        />
      </div>
    );
  }

  if (kind === "orange-juice") {
    return (
      <div style={shell}>
        <div
          style={{
            position: "absolute",
            left: size * 0.18,
            right: size * 0.18,
            bottom: size * 0.08,
            top: size * 0.12,
            borderRadius: size * 0.14,
            border: "2px solid rgba(255,255,255,0.55)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: "32% 0 0 0",
              background: "linear-gradient(180deg, #ffbf47, #ff7a18)",
            }}
          />
        </div>
        <div
          style={{
            position: "absolute",
            right: size * 0.14,
            top: size * 0.02,
            width: 2,
            height: size * 0.32,
            background: "#9fe0d4",
            transform: "rotate(18deg)",
            transformOrigin: "top center",
          }}
        />
      </div>
    );
  }

  if (kind === "peanut-butter") {
    return (
      <div style={shell}>
        <div
          style={{
            position: "absolute",
            left: size * 0.16,
            right: size * 0.16,
            top: size * 0.18,
            bottom: size * 0.08,
            borderRadius: size * 0.18,
            background: "linear-gradient(180deg, #a56b35, #7c4d22)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: size * 0.2,
            right: size * 0.2,
            top: size * 0.08,
            height: size * 0.14,
            borderRadius: size * 0.08,
            background: "#d8d8dc",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: size * 0.26,
            right: size * 0.26,
            top: size * 0.42,
            height: size * 0.18,
            borderRadius: size * 0.08,
            background: "rgba(255,244,227,0.75)",
          }}
        />
      </div>
    );
  }

  if (kind === "egg") {
    return (
      <div style={shell}>
        <div
          style={{
            position: "absolute",
            inset: "6% 18% 8% 18%",
            borderRadius: "48% 48% 52% 52% / 44% 44% 56% 56%",
            background: "#fff7ef",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: "38%",
            top: "42%",
            width: "24%",
            height: "24%",
            borderRadius: "50%",
            background: "#f6c44c",
          }}
        />
      </div>
    );
  }

  if (kind === "tofu") {
    return (
      <div style={shell}>
        <div
          style={{
            position: "absolute",
            inset: "16%",
            borderRadius: size * 0.12,
            background: "linear-gradient(135deg, #f7f4ea, #d9d4c3)",
            boxShadow: "inset -4px -4px 0 rgba(0,0,0,0.08)",
          }}
        />
      </div>
    );
  }

  if (kind === "chicken") {
    return (
      <div style={shell}>
        <div
          style={{
            position: "absolute",
            left: "20%",
            right: "22%",
            top: "22%",
            bottom: "18%",
            borderRadius: "55% 45% 52% 48%",
            background: "linear-gradient(135deg, #f0c28c, #b77d4e)",
          }}
        />
        <div
          style={{
            position: "absolute",
            right: "14%",
            top: "40%",
            width: "16%",
            height: "12%",
            borderRadius: 999,
            background: "#fff7ef",
          }}
        />
      </div>
    );
  }

  if (kind === "shake") {
    return (
      <div style={shell}>
        <div
          style={{
            position: "absolute",
            left: "24%",
            right: "24%",
            top: "18%",
            bottom: "12%",
            borderRadius: size * 0.12,
            background: "linear-gradient(180deg, #d9e9f0, #8bb8c8)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: "30%",
            right: "30%",
            top: "10%",
            height: "10%",
            borderRadius: 999,
            background: "#eff7fb",
          }}
        />
        <div
          style={{
            position: "absolute",
            right: "26%",
            top: "2%",
            width: 2,
            height: "28%",
            background: "#8fe7c8",
            transform: "rotate(-15deg)",
          }}
        />
      </div>
    );
  }

  if (kind === "avocado") {
    return (
      <div style={shell}>
        <div
          style={{
            position: "absolute",
            inset: "8% 18% 12% 18%",
            borderRadius: "45% 45% 55% 55% / 42% 42% 58% 58%",
            background: "#4aa865",
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: "20% 28% 24% 28%",
            borderRadius: "45% 45% 55% 55% / 42% 42% 58% 58%",
            background: "#bddf7b",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: "40%",
            top: "44%",
            width: "20%",
            height: "20%",
            borderRadius: "50%",
            background: "#8b5a2b",
          }}
        />
      </div>
    );
  }

  if (kind === "nuts") {
    return (
      <div style={shell}>
        <div
          style={{
            position: "absolute",
            left: "18%",
            top: "26%",
            width: "28%",
            height: "42%",
            borderRadius: "50% 48% 44% 52%",
            background: "#a26a38",
          }}
        />
        <div
          style={{
            position: "absolute",
            right: "18%",
            top: "22%",
            width: "30%",
            height: "46%",
            borderRadius: "48% 50% 42% 52%",
            background: "#c18b4d",
          }}
        />
      </div>
    );
  }

  if (kind === "fiber" || kind === "grain") {
    return (
      <div style={shell}>
        {[0, 1, 2].map((index) => (
          <div
            key={index}
            style={{
              position: "absolute",
              left: `${34 + index * 10}%`,
              top: "16%",
              width: 2,
              height: "64%",
              background: "#e0c36b",
              transform: `rotate(${index === 1 ? 0 : index === 0 ? -8 : 8}deg)`,
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div style={shell}>
      <div
        style={{
          position: "absolute",
          inset: "20%",
          borderRadius: "50%",
          background: "linear-gradient(135deg, #79d0ad, #4ba56f)",
        }}
      />
    </div>
  );
};

const FoodLabelChip: React.FC<{
  label: string;
  accent: string;
}> = ({ label, accent }) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 10,
      padding: "8px 14px",
      borderRadius: 999,
      color: "#fff8eb",
      fontSize: 14,
      fontWeight: 700,
      letterSpacing: 0.8,
      textTransform: "uppercase",
      background: `${accent}1c`,
      border: `1px solid ${accent}32`,
      boxShadow: `0 10px 28px ${accent}14`,
    }}
  >
    <FoodGlyph kind={labelToFoodKind(label)} />
    <span>{label}</span>
  </div>
);

const ChipRow: React.FC<{
  items: string[];
  accent: string;
}> = ({ items, accent }) => (
  <div
    style={{
      display: "flex",
      flexWrap: "wrap",
      gap: 10,
      marginBottom: 18,
    }}
  >
    {items.map((item) => (
      <FoodLabelChip key={item} label={item} accent={accent} />
    ))}
  </div>
);

const CurveCard: React.FC<{
  label: string;
  accent: string;
  muted: string;
  mode: "spike" | "flat";
  frame: number;
  fps: number;
  delay: number;
}> = ({ label, accent, muted, mode, frame, fps, delay }) => {
  const localFrame = Math.max(0, frame - delay);
  const rise = spring({
    frame: localFrame,
    fps,
    config: { damping: 16, stiffness: 110, mass: 0.8 },
  });
  const sweep = interpolate(localFrame, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        borderRadius: 28,
        padding: "26px 28px 24px",
        background: `linear-gradient(180deg, ${muted} 0%, rgba(255,255,255,0.03) 100%)`,
        border: `1px solid ${accent}28`,
        boxShadow: `0 30px 70px ${accent}15`,
        transform: `translateY(${interpolate(rise, [0, 1], [42, 0])}px)`,
        opacity: rise,
      }}
    >
      <div
        style={{
          color: "#f8fafc",
          fontSize: 18,
          fontWeight: 700,
          letterSpacing: 1.5,
          textTransform: "uppercase",
          marginBottom: 18,
          opacity: 0.88,
        }}
      >
        {label}
      </div>
      <svg width="100%" height="170" viewBox="0 0 360 170">
        <defs>
          <linearGradient id={`curve-${label}`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity={1} />
            <stop offset="100%" stopColor={accent} stopOpacity={0.35} />
          </linearGradient>
        </defs>
        <line x1="0" y1="140" x2="360" y2="140" stroke="rgba(255,255,255,0.12)" strokeWidth="2" />
        <path
          d={curvePath(140, mode)}
          fill="none"
          stroke={`url(#curve-${label})`}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray="500"
          strokeDashoffset={500 - sweep * 500}
          opacity={0.95}
        />
      </svg>
    </div>
  );
};

const RuleCard: React.FC<{
  label: string;
  sublabel: string;
  color: string;
  frame: number;
  fps: number;
  delay: number;
}> = ({ label, sublabel, color, frame, fps, delay }) => {
  const cardFrame = Math.max(0, frame - delay);
  const appear = spring({
    frame: cardFrame,
    fps,
    config: { damping: 18, stiffness: 120, mass: 0.75 },
  });

  return (
    <div
      style={{
        flex: 1,
        minHeight: 220,
        borderRadius: 28,
        padding: "26px 24px",
        background: `linear-gradient(180deg, ${color}24 0%, rgba(255,255,255,0.05) 100%)`,
        border: `1px solid ${color}55`,
        boxShadow: `0 24px 70px ${color}24`,
        transform: `translateY(${interpolate(appear, [0, 1], [36, 0])}px) scale(${interpolate(
          appear,
          [0, 1],
          [0.92, 1]
        )})`,
        opacity: appear,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: 16,
          background: `${color}22`,
          border: `1px solid ${color}44`,
        }}
      />
      <div>
        <div
          style={{
            color: "#fffaf0",
            fontSize: 42,
            fontWeight: 900,
            letterSpacing: -0.8,
            marginBottom: 10,
          }}
        >
          {label}
        </div>
        <div
          style={{
            color: "rgba(255,248,235,0.82)",
            fontSize: 19,
            lineHeight: 1.45,
          }}
        >
          {sublabel}
        </div>
      </div>
    </div>
  );
};

const OrbitChips: React.FC<{
  chips: string[];
  accent: string;
  alt: string;
  frame: number;
  fps: number;
}> = ({ chips, accent, alt, frame, fps }) => (
  <>
    {chips.slice(0, 4).map((chip, index) => {
      const delay = 10 + index * 5;
      const appear = spring({
        frame: Math.max(0, frame - delay),
        fps,
        config: { damping: 20, stiffness: 100 },
      });
      const angle = (Math.PI * 2 * index) / Math.max(chips.length, 4) + frame / 72;
      const radius = 168 + index * 10;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * (radius * 0.42);

      return (
        <div
          key={chip}
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            transform: `translate(${x}px, ${y}px) scale(${interpolate(appear, [0, 1], [0.6, 1])})`,
            opacity: appear,
            padding: "10px 14px",
            borderRadius: 999,
            color: "#fff9ef",
            fontSize: 18,
            fontWeight: 700,
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            background: `linear-gradient(90deg, ${index % 2 === 0 ? accent : alt}28, rgba(255,255,255,0.05))`,
            border: `1px solid ${index % 2 === 0 ? accent : alt}45`,
            boxShadow: `0 14px 30px ${index % 2 === 0 ? accent : alt}18`,
          }}
        >
          <FoodGlyph kind={labelToFoodKind(chip)} size={24} />
          {chip}
        </div>
      );
    })}
  </>
);

const StageShell: React.FC<{
  accent: string;
  alt: string;
  minHeight?: number;
  children: React.ReactNode;
}> = ({ accent, alt, minHeight, children }) => (
  <div
    style={{
      width: "100%",
      height: "100%",
      minHeight,
      borderRadius: 34,
      position: "relative",
      overflow: "hidden",
      background: `radial-gradient(circle at 22% 18%, ${accent}22 0%, transparent 28%), radial-gradient(circle at 78% 20%, ${alt}18 0%, transparent 26%), linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%)`,
      border: `1px solid ${accent}22`,
      boxShadow: `0 36px 120px ${accent}12`,
    }}
  >
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundImage:
          "linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px)",
        backgroundSize: "32px 32px",
        opacity: 0.26,
      }}
    />
    <div
      style={{
        position: "absolute",
        inset: "6% 8%",
        borderRadius: 32,
        border: "1px solid rgba(255,255,255,0.04)",
      }}
    />
    {children}
  </div>
);

const MealPlateVisual: React.FC<{
  labels: string[];
  accent: string;
  alt: string;
  size?: number;
}> = ({ labels, accent, alt, size = 320 }) => {
  const normalized = labels.map((label) => labelToFoodKind(label));
  const items: FoodKind[] = normalized.length > 0 ? normalized : ["grain"];
  const layouts =
    items.length >= 3
      ? [
          { left: "30%", top: "44%", rotate: -12 },
          { left: "70%", top: "34%", rotate: 8 },
          { left: "56%", top: "72%", rotate: -4 },
          { left: "76%", top: "66%", rotate: 10 },
        ]
      : items.length === 2
        ? [
            { left: "34%", top: "48%", rotate: -10 },
            { left: "68%", top: "40%", rotate: 8 },
          ]
        : [{ left: "50%", top: "48%", rotate: 0 }];

  return (
    <div
      style={{
        position: "relative",
        width: size,
        height: size,
        borderRadius: "50%",
        background: "radial-gradient(circle at 35% 30%, rgba(255,255,255,0.98) 0%, rgba(246,240,232,0.96) 42%, rgba(214,206,194,0.92) 72%, rgba(146,137,126,0.55) 100%)",
        boxShadow: "0 38px 72px rgba(0,0,0,0.34), inset 0 10px 16px rgba(255,255,255,0.52), inset 0 -18px 36px rgba(0,0,0,0.10)",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: "9%",
          borderRadius: "50%",
          border: "2px solid rgba(255,255,255,0.64)",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: "17%",
          borderRadius: "50%",
          background: `radial-gradient(circle at 50% 45%, rgba(255,255,255,0.72) 0%, rgba(243,235,223,0.78) 48%, ${accent}12 100%)`,
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: "-8% -8% 62% 10%",
          borderRadius: "50%",
          background: `radial-gradient(circle, ${alt}30 0%, transparent 72%)`,
          filter: "blur(18px)",
          opacity: 0.55,
        }}
      />
      {items.map((kind, index) => {
        const layout = layouts[index] || layouts[layouts.length - 1];
        const glyphSize = items.length >= 3 ? size * 0.23 : items.length === 2 ? size * 0.28 : size * 0.34;
        return (
          <div
            key={`${kind}-${index}`}
            style={{
              position: "absolute",
              left: layout.left,
              top: layout.top,
              transform: `translate(-50%, -50%) rotate(${layout.rotate}deg)`,
              width: glyphSize + 46,
              height: glyphSize + 46,
              borderRadius: "50%",
              background: "radial-gradient(circle at 35% 30%, rgba(255,255,255,0.95) 0%, rgba(250,242,235,0.88) 45%, rgba(231,223,211,0.60) 100%)",
              boxShadow: "0 16px 28px rgba(15,23,42,0.16)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <FoodGlyph kind={kind} size={glyphSize} />
          </div>
        );
      })}
    </div>
  );
};

const MiniCurve: React.FC<{
  accent: string;
  secondary: string;
  mode: "spike" | "flat";
}> = ({ accent, secondary, mode }) => (
  <svg width="100%" height="92" viewBox="0 0 360 92">
    <line x1="0" y1="70" x2="360" y2="70" stroke="rgba(255,255,255,0.12)" strokeWidth="2" />
    <path
      d={curvePath(68, mode)}
      fill="none"
      stroke={accent}
      strokeWidth="8"
      strokeLinecap="round"
      opacity={0.95}
    />
    <path
      d={curvePath(68, mode === "spike" ? "flat" : "spike")}
      fill="none"
      stroke={secondary}
      strokeWidth="4"
      strokeLinecap="round"
      opacity={0.28}
    />
  </svg>
);

const MealComparisonCard: React.FC<{
  title: string;
  accent: string;
  secondary: string;
  labels: string[];
  mode: "spike" | "flat";
  curveLabel: string;
}> = ({ title, accent, secondary, labels, mode, curveLabel }) => (
  <StageShell accent={accent} alt={secondary} minHeight={560}>
    <div
      style={{
        position: "absolute",
        inset: "8% 8% 7% 8%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <div
          style={{
            color: "#fff8ec",
            fontSize: 20,
            fontWeight: 800,
            letterSpacing: 1.8,
            textTransform: "uppercase",
          }}
        >
          {title}
        </div>
        <div
          style={{
            width: 12,
            height: 12,
            borderRadius: "50%",
            background: accent,
            boxShadow: `0 0 22px ${accent}88`,
          }}
        />
      </div>
      <ChipRow items={labels} accent={accent} />
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "8px 0 4px",
        }}
      >
        <MealPlateVisual labels={labels} accent={accent} alt={secondary} size={300} />
      </div>
      <div
        style={{
          marginTop: 18,
          padding: "18px 18px 14px",
          borderRadius: 24,
          background: "rgba(15,23,42,0.34)",
          border: `1px solid ${accent}22`,
        }}
      >
        <div
          style={{
            color: "rgba(248,250,252,0.72)",
            fontSize: 13,
            fontWeight: 700,
            letterSpacing: 1.4,
            textTransform: "uppercase",
            marginBottom: 8,
          }}
        >
          Glucose response
        </div>
        <div
          style={{
            color: "#fff9ef",
            fontSize: 24,
            fontWeight: 800,
            lineHeight: 1.2,
            marginBottom: 8,
          }}
        >
          {curveLabel}
        </div>
        <MiniCurve accent={accent} secondary={secondary} mode={mode} />
      </div>
    </div>
  </StageShell>
);

const RuleStage: React.FC<{
  palette: ReturnType<typeof getScenePalette>;
  frame: number;
  fps: number;
}> = ({ palette, frame, fps }) => {
  const rules = [
    {
      title: "Pair",
      subtitle: "Protein, fat, or fiber with the carbs",
      accent: palette.positive,
      labels: ["Egg", "Avocado"],
    },
    {
      title: "Order",
      subtitle: "Veg first. Carbs later.",
      accent: palette.accentAlt,
      labels: ["Veg First", "Protein", "Carbs Last"],
    },
    {
      title: "Choose",
      subtitle: "Keep the grain intact",
      accent: palette.accent,
      labels: ["Intact Grain", "Whole Fruit"],
    },
  ];

  return (
    <StageShell accent={palette.accent} alt={palette.accentAlt}>
      <div
        style={{
          position: "absolute",
          inset: "8% 7% 8% 7%",
          display: "grid",
          gridTemplateColumns: "1.05fr 0.95fr",
          gap: 24,
          alignItems: "center",
        }}
      >
        <div
          style={{
            position: "relative",
            minHeight: 540,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              width: 380,
              height: 380,
              borderRadius: "50%",
              background: `conic-gradient(from -70deg, ${palette.positive}66 0deg 118deg, ${palette.accentAlt}55 118deg 238deg, ${palette.accent}66 238deg 360deg)`,
              boxShadow: `0 34px 90px ${palette.accent}18`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative",
            }}
          >
            <div
              style={{
                width: 286,
                height: 286,
                borderRadius: "50%",
                background: "radial-gradient(circle at 35% 30%, rgba(255,255,255,0.98) 0%, rgba(240,234,224,0.96) 58%, rgba(202,194,182,0.82) 100%)",
                boxShadow: "inset 0 10px 18px rgba(255,255,255,0.50), inset 0 -16px 32px rgba(0,0,0,0.08)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#102033",
                fontSize: 54,
                fontWeight: 900,
                letterSpacing: -1.2,
              }}
            >
              3 Rules
            </div>
          </div>
          {[0, 1, 2].map((index) => {
            const angle = [-140, -10, 115][index];
            const appear = spring({
              frame: Math.max(0, frame - (8 + index * 7)),
              fps,
              config: { damping: 18, stiffness: 100 },
            });
            const radius = 250;
            const x = Math.cos((angle * Math.PI) / 180) * radius;
            const y = Math.sin((angle * Math.PI) / 180) * radius;
            return (
              <div
                key={rules[index].title}
                style={{
                  position: "absolute",
                  left: "50%",
                  top: "50%",
                  width: 170,
                  height: 170,
                  borderRadius: 28,
                  transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px)) scale(${interpolate(
                    appear,
                    [0, 1],
                    [0.84, 1]
                  )})`,
                  opacity: appear,
                  background: `linear-gradient(180deg, ${rules[index].accent}1a 0%, rgba(255,255,255,0.05) 100%)`,
                  border: `1px solid ${rules[index].accent}40`,
                  boxShadow: `0 18px 42px ${rules[index].accent}18`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <div
                  style={{
                    color: "#fff8eb",
                    fontSize: 42,
                    fontWeight: 900,
                    letterSpacing: -0.8,
                  }}
                >
                  {rules[index].title}
                </div>
              </div>
            );
          })}
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 18,
          }}
        >
          {rules.map((rule, index) => {
            const appear = spring({
              frame: Math.max(0, frame - (14 + index * 6)),
              fps,
              config: { damping: 18, stiffness: 110, mass: 0.84 },
            });
            return (
              <div
                key={rule.title}
                style={{
                  padding: "22px 24px",
                  borderRadius: 28,
                  background: `linear-gradient(180deg, ${rule.accent}18 0%, rgba(255,255,255,0.05) 100%)`,
                  border: `1px solid ${rule.accent}36`,
                  boxShadow: `0 22px 44px ${rule.accent}12`,
                  opacity: appear,
                  transform: `translateY(${interpolate(appear, [0, 1], [26, 0])}px)`,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 16,
                    marginBottom: 8,
                  }}
                >
                  <div
                    style={{
                      width: 42,
                      height: 42,
                      borderRadius: 14,
                      background: `${rule.accent}24`,
                      border: `1px solid ${rule.accent}42`,
                    }}
                  />
                  <div
                    style={{
                      color: "#fff8eb",
                      fontSize: 32,
                      fontWeight: 900,
                      letterSpacing: -0.6,
                    }}
                  >
                    {rule.title}
                  </div>
                </div>
                <div
                  style={{
                    color: "rgba(255,245,231,0.88)",
                    fontSize: 20,
                    lineHeight: 1.45,
                    marginBottom: 12,
                  }}
                >
                  {rule.subtitle}
                </div>
                <ChipRow items={rule.labels} accent={rule.accent} />
              </div>
            );
          })}
        </div>
      </div>
    </StageShell>
  );
};

const RapidMealStage: React.FC<{
  palette: ReturnType<typeof getScenePalette>;
  frame: number;
  fps: number;
  keywords: string[];
  chips: string[];
}> = ({ palette, frame, fps, keywords, chips }) => {
  const primary = chips.slice(0, 4);

  return (
    <StageShell accent={palette.accent} alt={palette.accentAlt}>
      <div
        style={{
          position: "absolute",
          inset: "8% 7% 8% 7%",
          display: "grid",
          gridTemplateRows: "1fr auto",
          gap: 20,
        }}
      >
        <div
          style={{
            position: "relative",
            minHeight: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: "8% 15% 18% 15%",
              borderRadius: 34,
              background: "linear-gradient(180deg, rgba(15,23,42,0.24) 0%, rgba(15,23,42,0.08) 100%)",
              border: `1px solid ${palette.accent}18`,
            }}
          />
          <MealPlateVisual
            labels={primary.length > 0 ? primary : ["Protein", "Carbs"]}
            accent={palette.accent}
            alt={palette.accentAlt}
            size={336}
          />
          {primary.slice(0, 4).map((chip, index) => {
            const angle = [-145, -25, 30, 140][index] ?? 0;
            const appear = spring({
              frame: Math.max(0, frame - (10 + index * 6)),
              fps,
              config: { damping: 18, stiffness: 110, mass: 0.82 },
            });
            const radius = 250;
            const x = Math.cos((angle * Math.PI) / 180) * radius;
            const y = Math.sin((angle * Math.PI) / 180) * (radius * 0.78);
            return (
              <div
                key={chip}
                style={{
                  position: "absolute",
                  left: "50%",
                  top: "50%",
                  transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px)) scale(${interpolate(
                    appear,
                    [0, 1],
                    [0.86, 1]
                  )})`,
                  opacity: appear,
                }}
              >
                <FoodLabelChip label={chip} accent={index % 2 === 0 ? palette.accent : palette.accentAlt} />
              </div>
            );
          })}
          <div
            style={{
              position: "absolute",
              top: 16,
              left: 16,
              padding: "12px 18px",
              borderRadius: 999,
              background: "rgba(15,23,42,0.42)",
              border: `1px solid ${palette.accent}20`,
              color: "#fff8eb",
              fontSize: 18,
              fontWeight: 800,
              letterSpacing: 1.2,
              textTransform: "uppercase",
            }}
          >
            {keywords.slice(0, 2).join(" + ") || "Pairing"}
          </div>
        </div>
        <div
          style={{
            padding: "20px 20px 16px",
            borderRadius: 26,
            background: "rgba(15,23,42,0.34)",
            border: `1px solid ${palette.accentAlt}22`,
            boxShadow: `0 18px 50px ${palette.accentAlt}10`,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 10,
            }}
          >
            <div
              style={{
                color: "rgba(248,250,252,0.72)",
                fontSize: 13,
                fontWeight: 700,
                letterSpacing: 1.4,
                textTransform: "uppercase",
              }}
            >
              Glucose response
            </div>
            <div
              style={{
                color: palette.positive,
                fontSize: 14,
                fontWeight: 800,
                letterSpacing: 1,
                textTransform: "uppercase",
              }}
            >
              flatter curve
            </div>
          </div>
          <div
            style={{
              color: "#fff9ef",
              fontSize: 28,
              fontWeight: 800,
              lineHeight: 1.2,
              marginBottom: 12,
            }}
          >
            {keywords.slice(0, 2).join(" + ") || "Pairing slows the spike"}
          </div>
          <MiniCurve accent={palette.positive} secondary={palette.caution} mode="flat" />
        </div>
      </div>
    </StageShell>
  );
};

export const StructuredVisualLayer: React.FC<Props> = ({
  scene,
  brand,
  layout = "split",
  emphasize = "right",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const isPortrait = height > width;
  const palette = getScenePalette(scene, brand);
  const register = resolveSceneRegister(scene);
  const keywords = deriveKeywords(scene);
  const chipSet = keywordToChipSet(scene);
  const mealLabels = detectMealLabels(scene);
  const mode =
    scene.visualType === "hook_card"
      ? "hook"
      : scene.visualType === "comparison_table"
        ? "comparison"
        : scene.type === "citation" || scene.visualType === "study_card"
          ? "study"
          : scene.heading.toLowerCase().includes("3 rules")
            ? "rules"
            : register === "warning"
              ? "warning"
              : "rapid";

  const canvasSpring = spring({
    frame: Math.max(0, frame - 4),
    fps,
    config: { damping: 20, stiffness: 90, mass: 0.85 },
  });

  const panelShift = interpolate(canvasSpring, [0, 1], [48, 0]);
  const panelOpacity = interpolate(canvasSpring, [0, 1], [0.15, 1]);

  const justify =
    emphasize === "center" ? "center" : emphasize === "left" ? "flex-start" : "flex-end";
  const visualInset = isPortrait
    ? mode === "hook" || mode === "comparison"
      ? "34% 4% 10% 4%"
      : mode === "rules"
        ? "20% 4% 16% 4%"
        : "18% 4% 12% 4%"
    : layout === "full"
      ? "18% 6% 14% 6%"
      : "15% 5% 14% 5%";

  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(circle at 18% 20%, ${palette.accent}20 0%, transparent 30%), radial-gradient(circle at 82% 24%, ${palette.accentAlt}16 0%, transparent 28%), linear-gradient(160deg, ${palette.background} 0%, ${palette.backgroundAlt} 100%)`,
        }}
      />

      <div
        style={{
          position: "absolute",
          left: 42,
          right: 42,
          bottom: 28,
          height: 2,
          borderRadius: 999,
          background: `linear-gradient(90deg, transparent, ${palette.rule}, transparent)`,
          opacity: 0.9,
        }}
      />

      <div
        style={{
          position: "absolute",
          inset: visualInset,
          display: "flex",
          justifyContent: justify,
          alignItems: "stretch",
          gap: 24,
          transform: `translateY(${panelShift}px)`,
          opacity: panelOpacity,
        }}
      >
        {(mode === "hook" || mode === "comparison") && (
          <div
            style={{
              width: "100%",
              maxWidth: isPortrait ? 980 : 1180,
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: isPortrait ? 16 : 26,
              alignSelf: isPortrait ? "center" : "flex-end",
              transform: `translateY(${isPortrait ? 0 : layout === "full" ? 54 : 22}px)`,
            }}
          >
            <MealComparisonCard
              title="Before"
              accent={palette.danger}
              secondary={palette.accentAlt}
              labels={mealLabels?.before || ["Carbs"]}
              mode="spike"
              curveLabel="Sharp rise"
            />
            <MealComparisonCard
              title="After"
              accent={palette.positive}
              secondary={palette.accent}
              labels={mealLabels?.after || ["Carbs", "Protein", "Fiber"]}
              mode="flat"
              curveLabel="Flatter response"
            />
          </div>
        )}

        {mode === "rules" && (
          <div
            style={{
              width: isPortrait ? "100%" : layout === "split" ? "58%" : "100%",
              maxWidth: isPortrait ? 920 : 980,
              display: "block",
              alignSelf: "center",
              marginLeft: isPortrait ? 0 : layout === "split" ? "28%" : 0,
              height: isPortrait ? 860 : 640,
            }}
          >
            <RuleStage palette={palette} frame={frame} fps={fps} />
          </div>
        )}

        {mode === "rapid" && (
          <div
            style={{
              marginLeft: isPortrait ? 0 : layout === "split" ? "28%" : 0,
              width: isPortrait ? "100%" : layout === "split" ? "68%" : "100%",
              minWidth: 0,
              position: "relative",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: isPortrait ? 860 : undefined,
            }}
          >
            <div
              style={{
                width: isPortrait ? "100%" : 880,
                maxWidth: 980,
                height: isPortrait ? 860 : 620,
              }}
            >
              <RapidMealStage
                palette={palette}
                frame={frame}
                fps={fps}
                keywords={keywords}
                chips={chipSet}
              />
            </div>
          </div>
        )}

        {mode === "study" && (
          <div
            style={{
              width: "100%",
              maxWidth: 920,
              marginLeft: layout === "split" ? "26%" : 0,
              alignSelf: "center",
              position: "relative",
            }}
          >
            <div
              style={{
                position: "absolute",
                right: -26,
                top: -26,
                width: 240,
                height: 240,
                borderRadius: 32,
                background: `${palette.accent}18`,
                filter: "blur(18px)",
              }}
            />
            <div
              style={{
                position: "relative",
                padding: "34px 36px",
                borderRadius: 32,
                background: `linear-gradient(180deg, ${palette.surface} 0%, rgba(255,255,255,0.04) 100%)`,
                border: `1px solid ${palette.accent}2c`,
                boxShadow: `0 28px 80px ${palette.accent}18`,
                transform: "rotate(-2deg)",
              }}
            >
              <div
                style={{
                  color: palette.textMuted,
                  fontSize: 16,
                  fontWeight: 700,
                  letterSpacing: 1.6,
                  textTransform: "uppercase",
                  marginBottom: 14,
                }}
              >
                Reviewed study
              </div>
              <div
                style={{
                  color: palette.text,
                  fontSize: 38,
                  fontWeight: 800,
                  lineHeight: 1.1,
                  marginBottom: 18,
                  maxWidth: 620,
                }}
              >
                {scene.citationCard?.label || scene.heading}
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr auto",
                  gap: 20,
                  alignItems: "end",
                }}
              >
                <div
                  style={{
                    color: palette.textMuted,
                    fontSize: 19,
                    lineHeight: 1.5,
                  }}
                >
                  {scene.citationCard?.detail ||
                    "Evidence is shown visually, not hidden in the description."}
                </div>
                <div
                  style={{
                    padding: "12px 18px",
                    borderRadius: 18,
                    color: palette.text,
                    fontSize: 18,
                    fontWeight: 800,
                    background: `${palette.positive}18`,
                    border: `1px solid ${palette.positive}40`,
                  }}
                >
                  Source checked
                </div>
              </div>
            </div>
          </div>
        )}

        {mode === "warning" && (
          <div
            style={{
              marginLeft: layout === "split" ? "36%" : 0,
              width: layout === "split" ? "58%" : "100%",
              maxWidth: 940,
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 18,
              alignSelf: "flex-end",
            }}
          >
            {["Teeth", "Esophagus", "Medication"].map((label, index) => (
              <RuleCard
                key={label}
                label={label}
                sublabel={
                  index === 0
                    ? "Acid can wear enamel with repeated use."
                    : index === 1
                      ? "Regular irritation is not a harmless tradeoff."
                      : "Interactions matter if you are on diabetes meds."
                }
                color={[palette.caution, palette.danger, palette.accentAlt][index]}
                frame={frame}
                fps={fps}
                delay={index * 5}
              />
            ))}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
