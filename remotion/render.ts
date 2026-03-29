/**
 * CLI render script for MoneyPrinterV2 Remotion videos.
 *
 * Usage:
 *   npx tsx render.ts <spec-path> <output-path> [--frame-range=0-1799]
 *
 * Example:
 *   npx tsx render.ts public/test-spec.json out/video.mp4
 */

import path from "node:path";
import fs from "node:fs";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";

async function main() {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.error("Usage: tsx render.ts <spec-path> <output-path> [--frame-range=0-1799]");
    console.error("  spec-path   Path to the spec JSON (relative to public/)");
    console.error("  output-path Where to write the rendered MP4");
    process.exit(1);
  }

  const [specFile, outputPath, ...extraArgs] = args;
  const absoluteOutput = path.resolve(outputPath);
  const absoluteSpecInput = path.resolve(specFile);
  let publicSpecFile = specFile;
  let frameRange: [number, number] | null = null;

  for (const arg of extraArgs) {
    if (arg.startsWith("--frame-range=")) {
      const value = arg.slice("--frame-range=".length);
      const [start, end] = value.split("-").map((part) => Number.parseInt(part, 10));
      if (Number.isFinite(start) && Number.isFinite(end)) {
        frameRange = [start, end];
      }
    }
  }

  if (path.isAbsolute(specFile)) {
    const runId = path.basename(path.dirname(path.dirname(absoluteSpecInput)));
    const publicDir = path.resolve(__dirname, "public", "assets", runId);
    fs.mkdirSync(publicDir, { recursive: true });
    const publicSpecPath = path.join(publicDir, "spec.json");
    fs.copyFileSync(absoluteSpecInput, publicSpecPath);
    publicSpecFile = `assets/${runId}/spec.json`;
  }

  console.log(`[render] Spec file : ${publicSpecFile}`);
  console.log(`[render] Output    : ${absoluteOutput}`);
  if (frameRange) {
    console.log(`[render] Frames    : ${frameRange[0]}-${frameRange[1]}`);
  }

  // ── Step 1: Bundle the Remotion project ──────────────────────────────
  console.log("[render] Bundling Remotion project...");
  const bundleLocation = await bundle({
    entryPoint: path.resolve(__dirname, "src/index.ts"),
    webpackOverride: (config) => config,
  });
  console.log("[render] Bundle complete.");

  // ── Step 2: Select the composition ───────────────────────────────────
  console.log("[render] Selecting composition...");
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: "HealthReview",
    inputProps: { specFile: publicSpecFile },
  });

  console.log(
    `[render] Composition: ${composition.id}, ` +
      `${composition.durationInFrames} frames @ ${composition.fps}fps ` +
      `(${(composition.durationInFrames / composition.fps).toFixed(1)}s)`
  );

  // ── Step 3: Render ───────────────────────────────────────────────────
  console.log("[render] Rendering...");
  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: "h264",
    outputLocation: absoluteOutput,
    inputProps: { specFile: publicSpecFile },
    frameRange,
    onProgress: ({ progress }) => {
      const pct = (progress * 100).toFixed(1);
      process.stdout.write(`\r[render] Progress: ${pct}%`);
    },
  });

  console.log(`\n[render] Done! Output: ${absoluteOutput}`);
}

main().catch((err) => {
  console.error("[render] Fatal error:", err);
  process.exit(1);
});
