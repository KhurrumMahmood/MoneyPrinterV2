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

Those checks confirm package generation, audits, dossier export, topic-hub aggregation, and grounded chat scaffolding are working on a real sample run.

## Known Gaps

- The grounded chat helper is retrieval-only and still needs a reader UI.
- Remotion changes are implemented, but full render verification in this isolated worktree is still pending.
- The evidence package is export-first today; interactive web surfaces come next.
