# CiteVideo

`citevideo/` is the experimental evidence-first health media system living alongside the legacy MPV2 app.

## What It Does

The pipeline is designed around a canonical `TopicEvidencePackage` for each run. Video, Shorts, dossier exports, topic hubs, and grounded chat all derive from the same package instead of inventing separate truth stores.

Current package outputs under `workspace/<run_id>/package/`:

- `topic_brief.json`
- `source_registry.json`
- `claims.json`
- `evidence_graph.json`
- `decision_table.json`
- `delivery_manifest.json`
- `web_dossier.json`
- `topic_hub_fragment.json`
- `chat_index.json`
- `corrections.json`
- `audits/*.json`

## Architecture

Main modules:

- `citevideo/models.py`
  Canonical dataclasses for evidence, delivery, dossier, topic hub, and chat records.
- `citevideo/pipeline.py`
  Orchestrates phases and now rebuilds package, audit, web, and chat outputs after key steps.
- `citevideo/backends/`
  Backend interfaces plus low-cost defaults for research/synthesis/review and paid-media backends for TTS, transcription, and image generation.
- `citevideo/audits/`
  Coverage, policy, clarity, trust, and delivery audits.
- `citevideo/delivery/planner.py`
  Builds long-form and Shorts delivery manifests from approved claims.
- `citevideo/web/`
  Export-first dossier and topic-hub generation.
- `citevideo/chat/`
  Retrieval-grounded chat index export plus a refusal-aware grounded answer helper.
- `citevideo/media/cache.py`
  Content-hash caching for paid media operations.

## Cost Model

Default behavior is intentionally conservative:

- Research, synthesis, review, and QA should prefer CLI-agent workflows.
- OpenRouter research is disabled unless `CITEVIDEO_ENABLE_OPENROUTER_RESEARCH` is explicitly enabled.
- Paid API usage is reserved for:
  - audio generation
  - transcription/alignment
  - image generation
- Media outputs are cached by content hash so unchanged scenes do not trigger repeat spend.

Useful backend environment variables:

- `CITEVIDEO_RESEARCH_BACKEND`
- `CITEVIDEO_SYNTHESIS_BACKEND`
- `CITEVIDEO_REVIEW_BACKEND`
- `CITEVIDEO_AUDIO_BACKEND`
- `CITEVIDEO_TRANSCRIPTION_BACKEND`
- `CITEVIDEO_IMAGE_BACKEND`
- `CITEVIDEO_ENABLE_OPENROUTER_RESEARCH`

## Remotion

The Remotion app in `remotion/` now understands delivery semantics directly:

- evidence badge metadata
- citation cards
- safety flags
- dossier anchors / CTAs
- fallback evidence panels
- long-form and short-form compositions

The renderer still needs a dedicated smoke pass in this worktree with clean local dependency resolution.

## Validation

Validated in this branch:

- `python3 -m unittest tests.test_topic_package`
- `python3 -m compileall citevideo`
- `python3 -c "from citevideo.pipeline import run_package_exports; run_package_exports('workspace/ben-azadi-stem-cells')"`
- `python3 -m citevideo.web.server workspace/ben-azadi-stem-cells --port 4174`
- Remotion preview render:
  `/Users/khurrummahmood/.nvm/versions/node/v22.21.1/bin/node node_modules/tsx/dist/cli.mjs render.ts spec.json ../workspace/ben-azadi-stem-cells/output/remotion-feedback.mp4`

Those checks confirm package generation, audits, dossier export, topic-hub aggregation, the local reader UI, grounded chat, and a Remotion preview render are working on a real sample run.

## Local Feedback Loop

Reader UI:

- Run `python3 -m citevideo.web.server workspace/<run_id> --port 4174`
- Open `http://127.0.0.1:4174`
- Review:
  - dossier summary
  - claim cards
  - harms / caveats
  - audit findings
  - grounded answers with citations

Render preview:

- Ensure `remotion/node_modules` is installed or linked locally.
- From `remotion/`, run:
  `/Users/khurrummahmood/.nvm/versions/node/v22.21.1/bin/node node_modules/tsx/dist/cli.mjs render.ts spec.json ../workspace/<run_id>/output/remotion-feedback.mp4`
- Extract preview frames or inspect the rendered MP4 before iterating on scripts, delivery manifests, or scene design.

## Known Gaps

- The grounded chat helper is retrieval-only; it is useful for evidence drill-down but not yet conversationally sophisticated.
- The reader UI is intentionally lightweight and local-first; a richer production web surface still needs to be designed.
- Remotion preview rendering works in this worktree when local dependencies are available, but the setup should be made more reproducible.
- The evidence package is export-first today; broader interactive web workflows come next.
