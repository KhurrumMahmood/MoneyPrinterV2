// ── Brand ────────────────────────────────────────────────────────────────

export interface BrandColors {
  primary: string;
  secondary: string;
  accent: string;
  text: string;
  textSecondary: string;
  success: string;
  warning: string;
  danger: string;
}

export interface BrandFonts {
  heading: string;
  body: string;
}

export interface Brand {
  colors: BrandColors;
  fonts: BrandFonts;
}

// ── Citation ─────────────────────────────────────────────────────────────

export interface Citation {
  label: string;
  detail?: string;
  doi?: string;
  timestamp?: string;
}

export interface CitationCardData {
  label: string;
  detail?: string;
  doi?: string;
}

export interface VisualBeat {
  timeOffset: number;
  type: "zoom" | "reveal" | "highlight" | "transition" | "overlay-enter" | "overlay-exit";
  target?: string;
}

// ── Word Timing (for kinetic captions) ───────────────────────────────────

export interface WordTiming {
  word: string;
  startMs: number;
  endMs: number;
}

// ── Scene ────────────────────────────────────────────────────────────────

export interface SceneSpec {
  sceneId: string;
  type:
    | "title"
    | "talking_point"
    | "citation"
    | "infographic"
    | "image"
    | "source_list"
    | "transition";
  heading: string;
  narration: string;
  durationMs: number;
  durationFrames: number;
  mood: string;
  evidenceStrength: "strong" | "moderate" | "weak" | "mixed" | "none";
  evidenceColor: string;
  claimsReferenced: string[];
  visualNotes: string;
  keywords?: string[];
  wordTimings?: WordTiming[];
  imagePath?: string;
  audioPath?: string;
  citations?: Citation[];
  visualType?:
    | "hook_card"
    | "study_card"
    | "evidence_overlay"
    | "comparison_table"
    | "source_stack"
    | "mechanism_diagram";
  benefitHarmMode?: "benefit" | "harm" | "balanced" | "caution";
  citationCard?: CitationCardData;
  visualBeats?: VisualBeat[];
  safetyFlags?: string[];
  allowedOutOfContext?: boolean;
  ctaTarget?: string;
  dossierAnchorId?: string;
  evidenceIds?: string[];
  sceneRegister?: "hook" | "kitchen" | "clinical" | "warning" | "action" | "neutral";
}

// ── Source ────────────────────────────────────────────────────────────────

export interface SourceEntry {
  label: string;
  full_citation?: string;
  doi?: string;
}

// ── Audio ────────────────────────────────────────────────────────────────

export interface AudioSpec {
  path: string;
  srtPath: string;
}

// ── Video Meta ──────────────────────────────────────────────────────────

export interface VideoMeta {
  runId: string;
  title: string;
  fps: number;
  width: number;
  height: number;
  totalDurationFrames: number;
  totalDurationMs: number;
}

// ── Top-Level Spec ──────────────────────────────────────────────────────

export interface VideoSpec {
  meta: VideoMeta;
  brand: Brand;
  audio: AudioSpec;
  scenes: SceneSpec[];
  sourcesList: SourceEntry[];
  disclaimer: string;
  web?: {
    dossierAnchorBase?: string;
  };
  corrections?: Array<Record<string, string>>;
  delivery?: {
    shorts?: Array<Record<string, unknown>>;
  };
}

// ── Composition Props ───────────────────────────────────────────────────

export interface VideoCompositionProps {
  specFile: string;
}
