/**
 * Capture one representative frame per scene as PNG for QA review.
 *
 * Usage:
 *   npx tsx capture-frames.ts <spec-path> <output-dir>
 *
 * Example:
 *   npx tsx capture-frames.ts glycine-poc/spec.json ../workspace/glycine-poc/frames
 */

import path from "node:path";
import fs from "node:fs";
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";

interface SceneInfo {
  sceneId: string;
  durationMs: number;
  durationFrames: number;
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.error("Usage: tsx capture-frames.ts <spec-path> <output-dir>");
    console.error("  spec-path   Path to spec JSON (relative to public/)");
    console.error("  output-dir  Directory for output PNGs");
    process.exit(1);
  }

  const [specFile, outputDir] = args;
  const absoluteOutputDir = path.resolve(outputDir);

  // Read spec to get scene info
  const specPath = path.resolve(__dirname, "public", specFile);
  const spec = JSON.parse(fs.readFileSync(specPath, "utf-8"));
  const fps = spec.meta.fps || 30;

  // Create output directory
  fs.mkdirSync(absoluteOutputDir, { recursive: true });

  console.log(`[capture] Spec: ${specFile}`);
  console.log(`[capture] Output: ${absoluteOutputDir}`);
  console.log(`[capture] Scenes: ${spec.scenes.length}`);

  // Bundle
  console.log("[capture] Bundling...");
  const bundleLocation = await bundle({
    entryPoint: path.resolve(__dirname, "src/index.ts"),
    webpackOverride: (config) => config,
  });
  console.log("[capture] Bundle complete.");

  // Select composition
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: "HealthReview",
    inputProps: { specFile },
  });

  console.log(
    `[capture] Composition: ${composition.width}x${composition.height}, ` +
      `${composition.durationInFrames} frames`
  );

  // Calculate frame offsets for each scene
  let frameOffset = 0;
  const sceneFrames: Array<{ sceneId: string; startFrame: number; duration: number }> = [];

  for (const scene of spec.scenes) {
    const duration =
      scene.durationFrames || Math.ceil((scene.durationMs / 1000) * fps);
    sceneFrames.push({
      sceneId: scene.sceneId,
      startFrame: frameOffset,
      duration,
    });
    frameOffset += duration;
  }

  // Capture one frame per scene at 40% through (past intro animations)
  console.log("\n[capture] Rendering frames...");
  for (const { sceneId, startFrame, duration } of sceneFrames) {
    const targetFrame = startFrame + Math.floor(duration * 0.4);
    const outputPath = path.join(absoluteOutputDir, `${sceneId}.png`);

    console.log(
      `  ${sceneId}: frame ${targetFrame} (${(targetFrame / fps).toFixed(1)}s)...`
    );

    await renderStill({
      composition,
      serveUrl: bundleLocation,
      output: outputPath,
      frame: targetFrame,
      imageFormat: "png",
      inputProps: { specFile },
    });

    console.log(`  ${sceneId}: saved`);
  }

  console.log(`\n[capture] Done! ${sceneFrames.length} frames saved to ${absoluteOutputDir}`);
}

main().catch((err) => {
  console.error("[capture] Fatal error:", err);
  process.exit(1);
});
