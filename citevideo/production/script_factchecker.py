"""
Script Fact-Check Pass (Phase 3c).

Cross-references every claim in the script against evidence.json
to ensure nothing was dropped, exaggerated, or presented without
appropriate caveats.
"""

import os
import json
import re
from citevideo.llm import claude

FACTCHECK_SYSTEM = (
    "You are a rigorous science editor performing a final fact-check on a video script. "
    "Your job is to ensure every scientific claim is backed by the evidence file, "
    "appropriately caveated, and honestly presented. You will NOT let a misleading "
    "claim slip through. You respond with ONLY valid JSON."
)

FACTCHECK_PROMPT = """Perform a final fact-check on this video script by cross-referencing every claim against the evidence data.

## Script (Draft 2)
{script_json}

## Evidence Data (ground truth)
{evidence_json}

---

For each scene that references a scientific claim, verify:
1. Does the narration accurately reflect what the evidence says?
2. Are appropriate caveats present for weak/preliminary evidence?
3. Are citations present for every factual claim?
4. Is the evidence_strength rating correct?
5. Is there any exaggeration, even subtle?

Return a JSON object:

{{
  "issues_found": [
    {{
      "scene_id": "scene_003",
      "severity": "critical|major|minor",
      "issue": "Description of the problem",
      "evidence_says": "What the evidence actually says",
      "script_says": "What the script says",
      "fix": "Specific fix for the narration text"
    }}
  ],
  "missing_caveats": [
    {{
      "scene_id": "scene_005",
      "claim_id": "claim_012",
      "needed_caveat": "This was a mouse study, not human",
      "suggested_insertion": "In mouse studies — and we should note this hasn't been confirmed in humans yet — ..."
    }}
  ],
  "missing_citations": [
    {{
      "scene_id": "scene_004",
      "claim_text": "What's claimed without citation",
      "citation_to_add": {{
        "label": "Author (Year)",
        "detail": "Journal",
        "doi": "..."
      }}
    }}
  ],
  "dropped_claims": [
    "claim_ids from evidence that should be in the video but aren't"
  ],
  "accuracy_score": 1-10,
  "honest_presentation_score": 1-10,
  "summary": "Overall assessment of the script's scientific integrity"
}}

Be thorough. Every claim needs backup. Every weak claim needs a caveat."""

APPLY_FIXES_SYSTEM = (
    "You are a script editor applying fact-check corrections. You make precise edits "
    "to fix accuracy issues while preserving the script's voice and flow. "
    "You add disclaimer beats where evidence is weak. "
    "You respond with ONLY valid JSON in the same format as the input script."
)

APPLY_FIXES_PROMPT = """Apply these fact-check corrections to the video script.

## Current Script (Draft 2)
{script_json}

## Fact-Check Report
{factcheck_report}

---

Apply ALL fixes from the fact-check report:
1. Fix any accuracy issues (critical and major first)
2. Insert missing caveats where evidence is weak
3. Add missing citations
4. Fix evidence_strength ratings if incorrect
5. Add a brief disclaimer scene if there are significant caveats

Return the FULL corrected script in the same JSON format.
Preserve the script's engaging voice — caveats should feel natural, not clinical.
Add a "factcheck_notes" field listing all corrections applied."""


def factcheck_and_fix(run_dir: str) -> dict:
    """
    Fact-check script v2 against evidence and produce final script v3.

    Args:
        run_dir: Run directory path

    Returns:
        Final script dict (v3)
    """
    prod_dir = os.path.join(run_dir, "production")

    # Load script v2 and evidence
    with open(os.path.join(prod_dir, "script_v2.json")) as f:
        script = json.load(f)

    with open(os.path.join(run_dir, "evidence.json")) as f:
        evidence = json.load(f)

    script_json = json.dumps(script, indent=2)

    # Build condensed evidence for fact-checking (full evidence.json is too large)
    evidence_lines = []
    for r in evidence.get("ratings", []):
        er = r.get("evidence_rating", {})
        v = r.get("verification", {})
        cid = r.get("claim_id", "?")
        text = r.get("claim_text", "")[:150]
        evidence_lines.append(f"### {cid}: {text}")
        evidence_lines.append(f"- Accuracy: {er.get('accuracy_score', '?')}/5 ({er.get('accuracy_label', '?')})")
        evidence_lines.append(f"- Evidence: {er.get('evidence_label', '?')}, Extrapolation risk: {er.get('extrapolation_risk', '?')}")
        if v.get("what_study_actually_found"):
            evidence_lines.append(f"- Study found: {v['what_study_actually_found'][:200]}")
        if v.get("discrepancy_notes"):
            evidence_lines.append(f"- Discrepancy: {v['discrepancy_notes'][:200]}")
        if r.get("recommended_framing"):
            evidence_lines.append(f"- Recommended framing: {r['recommended_framing'][:200]}")
        evidence_lines.append("")
    evidence_condensed = "\n".join(evidence_lines)

    # Run fact-check
    print(f"  Running fact-check pass... (script: {len(script_json)} chars, evidence: {len(evidence_condensed)} chars)")
    fc_response = claude(
        FACTCHECK_PROMPT.format(script_json=script_json, evidence_json=evidence_condensed),
        system_prompt=FACTCHECK_SYSTEM,
        timeout=600,
        label="factchecker:check",
    )

    fc_cleaned = fc_response.replace("```json", "").replace("```", "").strip()
    try:
        factcheck = json.loads(fc_cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", fc_cleaned, re.DOTALL)
        if match:
            factcheck = json.loads(match.group())
        else:
            raise RuntimeError(f"Failed to parse fact-check:\n{fc_cleaned[:500]}")

    # Save fact-check report
    fc_path = os.path.join(prod_dir, "factcheck_report.json")
    with open(fc_path, "w", encoding="utf-8") as f:
        json.dump(factcheck, f, indent=2, ensure_ascii=False)

    issues = factcheck.get("issues_found", [])
    caveats = factcheck.get("missing_caveats", [])
    citations = factcheck.get("missing_citations", [])
    accuracy = factcheck.get("accuracy_score", "?")
    honesty = factcheck.get("honest_presentation_score", "?")

    print(f"    Issues: {len(issues)} ({sum(1 for i in issues if i.get('severity') == 'critical')} critical)")
    print(f"    Missing caveats: {len(caveats)}")
    print(f"    Missing citations: {len(citations)}")
    print(f"    Accuracy: {accuracy}/10, Honesty: {honesty}/10")

    # Apply fixes if there are issues
    if issues or caveats or citations:
        print("  Applying fact-check fixes → draft 3...")
        fix_response = claude(
            APPLY_FIXES_PROMPT.format(
                script_json=script_json,
                factcheck_report=json.dumps(factcheck, indent=2),
            ),
            system_prompt=APPLY_FIXES_SYSTEM,
            timeout=600,
            label="factchecker:apply_fixes",
        )

        fix_cleaned = fix_response.replace("```json", "").replace("```", "").strip()
        try:
            script_v3 = json.loads(fix_cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", fix_cleaned, re.DOTALL)
            if match:
                script_v3 = json.loads(match.group())
            else:
                raise RuntimeError(f"Failed to parse corrected script:\n{fix_cleaned[:500]}")
    else:
        print("  No issues found — draft 2 passes fact-check!")
        script_v3 = script
        script_v3["factcheck_notes"] = ["Passed fact-check with no corrections needed"]

    # Save final script
    v3_path = os.path.join(prod_dir, "script_v3.json")
    with open(v3_path, "w", encoding="utf-8") as f:
        json.dump(script_v3, f, indent=2, ensure_ascii=False)

    scenes = script_v3.get("scenes", [])
    total_words = sum(len(s.get("narration", "").split()) for s in scenes)
    print(f"  Final script (v3): {len(scenes)} scenes, ~{total_words} words")
    print(f"  Saved to {v3_path}")

    return script_v3
