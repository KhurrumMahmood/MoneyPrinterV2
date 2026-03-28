import React, { useEffect, useState } from "react";
import {
  AbsoluteFill,
  useVideoConfig,
  staticFile,
  delayRender,
  continueRender,
  Sequence,
  Audio,
} from "remotion";
import type { VideoCompositionProps, VideoSpec, SceneSpec } from "./types";
import { TitleScene } from "./components/scenes/TitleScene";
import { TalkingPointScene } from "./components/scenes/TalkingPointScene";
import { CitationScene } from "./components/scenes/CitationScene";
import { ImageScene } from "./components/scenes/ImageScene";
import { InfographicScene } from "./components/scenes/InfographicScene";
import { SourceListScene } from "./components/scenes/SourceListScene";
import {
  SubtitleOverlay,
  parseSrt,
} from "./components/shared/SubtitleOverlay";

export const VideoComposition: React.FC<VideoCompositionProps> = ({
  specFile,
}) => {
  const { fps } = useVideoConfig();
  const [spec, setSpec] = useState<VideoSpec | null>(null);
  const [subtitleCues, setSubtitleCues] = useState<
    Array<{ startMs: number; endMs: number; text: string }>
  >([]);
  const [handle] = useState(() => delayRender("Loading spec JSON"));

  useEffect(() => {
    const url = staticFile(specFile);
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load ${specFile}: ${res.status}`);
        return res.json();
      })
      .then((data: VideoSpec) => {
        setSpec(data);

        // Load subtitles if available
        if (data.audio?.srtPath) {
          return fetch(staticFile(data.audio.srtPath))
            .then((r) => (r.ok ? r.text() : ""))
            .then((srtText) => {
              if (srtText) {
                setSubtitleCues(parseSrt(srtText));
              }
            });
        }
      })
      .then(() => continueRender(handle))
      .catch((err) => {
        console.error(err);
        continueRender(handle);
      });
  }, [specFile, handle]);

  if (!spec) {
    return (
      <AbsoluteFill
        style={{
          backgroundColor: "#0f172a",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <span style={{ color: "#f8fafc", fontSize: 48 }}>Loading...</span>
      </AbsoluteFill>
    );
  }

  const { brand, scenes, sourcesList } = spec;

  // Build frame offset map
  let runningFrame = 0;
  const sceneFrames = scenes.map((scene) => {
    const startFrame = runningFrame;
    const durationFrames =
      scene.durationFrames || Math.ceil((scene.durationMs / 1000) * fps);
    runningFrame += durationFrames;
    return { scene, startFrame, durationFrames };
  });

  return (
    <AbsoluteFill style={{ backgroundColor: brand.colors.primary }}>
      {/* Global audio track (if provided) */}
      {spec.audio?.path && (
        <Audio src={staticFile(spec.audio.path)} volume={1} />
      )}

      {/* Scenes with per-scene audio */}
      {sceneFrames.map(({ scene, startFrame, durationFrames }, i) => (
        <Sequence
          key={scene.sceneId || i}
          from={startFrame}
          durationInFrames={durationFrames}
        >
          {/* Per-scene audio (takes priority over global track) */}
          {scene.audioPath && !spec.audio?.path && (
            <Audio src={staticFile(scene.audioPath)} volume={1} />
          )}
          <SceneRenderer
            scene={scene}
            brand={brand}
            sourcesList={sourcesList}
          />
        </Sequence>
      ))}

      {/* Subtitle overlay (always on top) */}
      {subtitleCues.length > 0 && (
        <SubtitleOverlay cues={subtitleCues} brand={brand} />
      )}
    </AbsoluteFill>
  );
};

// Route scene type to the correct component
const SceneRenderer: React.FC<{
  scene: SceneSpec;
  brand: VideoSpec["brand"];
  sourcesList?: VideoSpec["sourcesList"];
}> = ({ scene, brand, sourcesList }) => {
  switch (scene.type) {
    case "title":
      return <TitleScene scene={scene} brand={brand} />;
    case "talking_point":
      return <TalkingPointScene scene={scene} brand={brand} />;
    case "citation":
      return <CitationScene scene={scene} brand={brand} />;
    case "image":
      return <ImageScene scene={scene} brand={brand} />;
    case "infographic":
      return <InfographicScene scene={scene} brand={brand} />;
    case "source_list":
      return (
        <SourceListScene
          scene={scene}
          brand={brand}
          sourcesList={sourcesList}
        />
      );
    default:
      // Fallback for transition or unknown types
      return <TalkingPointScene scene={scene} brand={brand} />;
  }
};
