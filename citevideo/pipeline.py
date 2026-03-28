"""
CiteVideo Pipeline Orchestrator.

Runs the full pipeline or individual phases. All artifacts are saved
to workspace/{run_id}/ for iteration and reuse.

Usage:
    python -m citevideo.pipeline <transcript_path> [--from-phase N] [--run-id ID]
"""

import os
import sys
import json
import argparse
from uuid import uuid4
from datetime import datetime

# Ensure project root is importable
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from citevideo.config import ensure_run_dirs, get_run_dir


def _save_json(path: str, data: dict):
    """Write JSON with pretty formatting."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_json(path: str) -> dict:
    """Load JSON from file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_optional_json(path: str, default: dict | None = None) -> dict:
    if not os.path.exists(path):
        return default or {}
    return _load_json(path)


def _latest_script_path(run_dir: str) -> str | None:
    for candidate in ("script_v3.json", "script_v2.json", "script_v1.json"):
        path = os.path.join(run_dir, "production", candidate)
        if os.path.exists(path):
            return path
    return None


def run_package_exports(run_dir: str):
    """Build package, web, chat, and audit artifacts from current run state."""
    from citevideo.audits import (
        run_clarity_audit,
        run_coverage_audit,
        run_delivery_audit,
        run_policy_audit,
        run_trust_audit,
    )
    from citevideo.delivery.planner import build_delivery_manifest
    from citevideo.evidence.package import build_package_artifacts, ensure_package_layout
    from citevideo.web.export import export_web_payloads
    from citevideo.chat.indexer import export_chat_index

    layout = ensure_package_layout(run_dir)
    claims_data = _load_optional_json(os.path.join(run_dir, "claims.json"), {"claims": []})
    evidence = _load_optional_json(os.path.join(run_dir, "evidence.json"), {"ratings": []})
    script_path = _latest_script_path(run_dir)
    script = _load_optional_json(script_path, {}) if script_path else {}

    if script and evidence.get("ratings"):
        print("\n=== Package: Delivery manifest ===")
        delivery_manifest = build_delivery_manifest(script, evidence)
        _save_json(layout["delivery_manifest"], delivery_manifest)
        print(f"  Saved to {layout['delivery_manifest']}")

    print("\n=== Package: Canonical artifacts ===")
    paths = build_package_artifacts(run_dir)
    print(f"  Package directory: {paths['package_dir']}")

    evidence_graph = _load_optional_json(paths["evidence_graph"], {"claims": []})
    decision_table = _load_optional_json(paths["decision_table"], {"rows": []})
    corrections = _load_optional_json(paths["corrections"], {"items": []})
    source_registry = _load_optional_json(paths["source_registry"], {"sources": []})
    delivery_manifest = _load_optional_json(paths["delivery_manifest"], {})

    audits = {
        "coverage": run_coverage_audit(claims_data, evidence_graph, decision_table),
        "policy": run_policy_audit(script, decision_table),
        "clarity": run_clarity_audit(script),
        "trust": run_trust_audit(script, corrections, source_registry),
        "delivery": run_delivery_audit(script, delivery_manifest),
    }
    for audit_name, payload in audits.items():
        audit_path = os.path.join(layout["audits_dir"], f"{audit_name}.json")
        _save_json(audit_path, payload)
        print(f"  Audit saved: {audit_path}")

    export_web_payloads(run_dir)
    export_chat_index(run_dir)
    return paths


def run_phase_1(run_dir: str, transcript: str, video_title: str = "", video_url: str = ""):
    """Phase 1: Deep Research (claim extraction + Perplexity + counter-research + rating)."""
    from citevideo.research.extractor import extract_claims
    from citevideo.research.researcher import research_claims
    from citevideo.research.counter_researcher import research_counter_evidence
    from citevideo.research.rater import rate_evidence

    # Save transcript
    transcript_path = os.path.join(run_dir, "transcript.txt")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    # 1a: Extract claims
    print("\n=== Phase 1a: Extracting claims ===")
    claims_path = os.path.join(run_dir, "claims.json")
    claims_data = extract_claims(transcript, video_title=video_title)
    claims_data["video_url"] = video_url
    claims_data["extracted_at"] = datetime.now().isoformat()
    _save_json(claims_path, claims_data)
    print(f"  Saved to {claims_path}")

    # 1b: Primary research
    print("\n=== Phase 1b: Perplexity deep research ===")
    research_path = os.path.join(run_dir, "research_raw.json")

    def save_research(results):
        _save_json(research_path, results)

    primary_research = research_claims(claims_data, save_callback=save_research)
    _save_json(research_path, primary_research)
    print(f"  Saved to {research_path}")

    # 1c: Counter-research
    print("\n=== Phase 1c: Counter-research ===")
    counter_path = os.path.join(run_dir, "counter_research.json")

    def save_counter(results):
        _save_json(counter_path, results)

    counter_research = research_counter_evidence(
        claims_data, primary_research, save_callback=save_counter
    )
    _save_json(counter_path, counter_research)
    print(f"  Saved to {counter_path}")

    # 1e: Evidence rating (combines 1d consensus synthesis into the rating step)
    print("\n=== Phase 1e: Evidence rating & synthesis ===")
    evidence_path = os.path.join(run_dir, "evidence.json")
    evidence = rate_evidence(claims_data, primary_research, counter_research)
    evidence["run_id"] = os.path.basename(run_dir)
    evidence["rated_at"] = datetime.now().isoformat()
    _save_json(evidence_path, evidence)
    print(f"  Saved to {evidence_path}")

    run_package_exports(run_dir)

    return evidence


def run_phase_2(run_dir: str):
    """Phase 2: Multi-agent roundtable + content plan synthesis."""
    from citevideo.roundtable.orchestrator import run_roundtable

    # Load required inputs
    transcript_path = os.path.join(run_dir, "transcript.txt")
    evidence_path = os.path.join(run_dir, "evidence.json")

    with open(transcript_path, "r") as f:
        transcript = f.read()
    evidence = _load_json(evidence_path)

    print("\n=== Phase 2: Multi-agent roundtable ===")
    content_plan = run_roundtable(run_dir, transcript, evidence)

    plan_path = os.path.join(run_dir, "roundtable", "content_plan.json")
    _save_json(plan_path, content_plan)
    print(f"  Content plan saved to {plan_path}")

    return content_plan


def run_phase_3(run_dir: str):
    """Phase 3: Script development (3 drafts with specialist review)."""
    from citevideo.production.scriptwriter import write_script
    from citevideo.production.script_reviewer import review_and_revise
    from citevideo.production.script_factchecker import factcheck_and_fix

    print("\n=== Phase 3a: Script draft 1 ===")
    write_script(run_dir)

    print("\n=== Phase 3b: Engagement & clarity review → draft 2 ===")
    review_and_revise(run_dir)

    print("\n=== Phase 3c: Fact-check → draft 3 ===")
    script = factcheck_and_fix(run_dir)
    run_package_exports(run_dir)
    return script


def run_phase_4(run_dir: str):
    """Phase 4: Asset generation + spec assembly."""
    from citevideo.production.asset_generator import generate_all_assets
    from citevideo.production.spec_builder import build_spec

    print("\n=== Phase 4a: Asset generation ===")
    generate_all_assets(run_dir)

    print("\n=== Phase 4c: Spec assembly ===")
    spec = build_spec(run_dir)
    run_package_exports(run_dir)
    return spec


def run_phase_5(run_dir: str):
    """Phase 5: Remotion rendering."""
    import subprocess as sp

    prod_dir = os.path.join(run_dir, "production")
    spec_path = os.path.join(prod_dir, "spec.json")
    output_dir = os.path.join(run_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "video.mp4")

    remotion_root = os.path.join(os.path.dirname(os.path.dirname(run_dir)), "remotion")
    render_script = os.path.join(remotion_root, "render.ts")

    if not os.path.exists(render_script):
        print("  WARNING: Remotion render script not found, skipping render")
        return None

    print(f"\n=== Phase 5: Remotion render ===")
    print(f"  Spec: {spec_path}")
    print(f"  Output: {output_path}")

    result = sp.run(
        ["npx", "tsx", render_script, spec_path, output_path],
        cwd=remotion_root,
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        print(f"  Render FAILED: {result.stderr[:500]}")
        return None

    print(f"  Render complete: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="CiteVideo Pipeline")
    parser.add_argument("transcript", help="Path to transcript file")
    parser.add_argument("--title", default="", help="Video title")
    parser.add_argument("--url", default="", help="Video URL")
    parser.add_argument("--run-id", default=None, help="Resume a specific run")
    parser.add_argument("--from-phase", type=int, default=1, help="Start from phase N")
    args = parser.parse_args()

    # Read transcript
    with open(args.transcript, "r", encoding="utf-8") as f:
        transcript = f.read()

    # Setup run directory
    run_id = args.run_id or f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run_dir = ensure_run_dirs(run_id)

    print(f"CiteVideo Pipeline")
    print(f"  Run ID: {run_id}")
    print(f"  Run dir: {run_dir}")
    print(f"  Transcript: {len(transcript)} chars")
    print(f"  Starting from phase: {args.from_phase}")

    if args.from_phase <= 1:
        run_phase_1(run_dir, transcript, video_title=args.title, video_url=args.url)

    if args.from_phase <= 2:
        run_phase_2(run_dir)

    if args.from_phase <= 3:
        run_phase_3(run_dir)

    if args.from_phase <= 4:
        run_phase_4(run_dir)

    if args.from_phase <= 5:
        run_phase_5(run_dir)

    # Save cost report
    from citevideo.llm import get_tracker
    tracker = get_tracker()
    tracker.save(os.path.join(run_dir, "cost_report.json"))
    tracker.print_summary()

    print(f"\n=== Pipeline complete ===")
    print(f"  All artifacts in: {run_dir}")


if __name__ == "__main__":
    main()
