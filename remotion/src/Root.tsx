import React from "react";
import { Composition, staticFile } from "remotion";
import { VideoComposition } from "./VideoComposition";
import type { VideoSpec } from "./types";

const FPS = 30;

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="HealthReview"
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        component={VideoComposition as React.ComponentType<any>}
        width={1920}
        height={1080}
        fps={FPS}
        defaultProps={{
          specFile: "spec.json",
        }}
        calculateMetadata={async ({ props }) => {
          const specFile = (props as Record<string, string>).specFile;

          let spec: VideoSpec;
          try {
            const url = staticFile(specFile);
            const res = await fetch(url);
            if (!res.ok) throw new Error(`${res.status}`);
            spec = (await res.json()) as VideoSpec;
          } catch {
            // Fallback: if fetch fails (e.g. during bundling), use a
            // reasonable default so the composition still registers.
            return {
              durationInFrames: FPS * 10,
              props,
            };
          }

          const totalMs = spec.scenes.reduce(
            (sum, scene) => sum + scene.durationMs,
            0
          );
          const durationInFrames = Math.max(
            1,
            Math.ceil((totalMs / 1000) * FPS)
          );

          return {
            durationInFrames,
            width: spec.meta.width ?? 1080,
            height: spec.meta.height ?? 1920,
            props,
          };
        }}
      />
      <Composition
        id="HealthShort"
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        component={VideoComposition as React.ComponentType<any>}
        width={1080}
        height={1920}
        fps={FPS}
        defaultProps={{
          specFile: "spec.json",
        }}
        calculateMetadata={async ({ props }) => {
          const specFile = (props as Record<string, string>).specFile;
          try {
            const url = staticFile(specFile);
            const res = await fetch(url);
            if (!res.ok) throw new Error(`${res.status}`);
            const spec = (await res.json()) as VideoSpec;
            return {
              durationInFrames: Math.max(
                1,
                Math.ceil((spec.meta.totalDurationMs / 1000) * FPS)
              ),
              width: 1080,
              height: 1920,
              props,
            };
          } catch {
            return {
              durationInFrames: FPS * 10,
              props,
            };
          }
        }}
      />
    </>
  );
};
