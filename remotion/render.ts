/**
 * CLI render script for MoneyPrinterV2 Remotion videos.
 *
 * Usage:
 *   npx tsx render.ts <spec-path> <output-path>
 *
 * Example:
 *   npx tsx render.ts public/test-spec.json out/video.mp4
 */

import path from "node:path";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";

async function main() {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.error("Usage: tsx render.ts <spec-path> <output-path>");
    console.error("  spec-path   Path to the spec JSON (relative to public/)");
    console.error("  output-path Where to write the rendered MP4");
    process.exit(1);
  }

  const [specFile, outputPath] = args;
  const absoluteOutput = path.resolve(outputPath);

  console.log(`[render] Spec file : ${specFile}`);
  console.log(`[render] Output    : ${absoluteOutput}`);

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
    inputProps: { specFile },
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
    inputProps: { specFile },
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
