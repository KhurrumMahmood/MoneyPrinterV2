import json
import os
import tempfile
import unittest

from citevideo.chat import answer_grounded_question
from citevideo.delivery.planner import build_delivery_manifest
from citevideo.evidence.package import build_package_artifacts, ensure_package_layout
from citevideo.intake import load_topic_bundle
from citevideo.web.hubs import aggregate_topic_hubs


class TopicPackageTests(unittest.TestCase):
    def test_build_package_artifacts_from_minimal_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = os.path.join(tmp, "sample-run")
            os.makedirs(os.path.join(run_dir, "production"), exist_ok=True)

            with open(os.path.join(run_dir, "transcript.txt"), "w", encoding="utf-8") as handle:
                handle.write("A sample transcript about glycine.")

            claims = {
                "video_title": "Sample Topic",
                "claims": [
                    {
                        "id": "claim_001",
                        "text": "Glycine may improve sleep quality.",
                        "category": "general_health_claim",
                    }
                ],
            }
            evidence = {
                "overall_assessment": "Mixed but promising.",
                "strongest_claims": ["claim_001"],
                "weakest_claims": [],
                "ratings": [
                    {
                        "claim_id": "claim_001",
                        "claim_text": "Glycine may improve sleep quality.",
                        "verification": {
                            "status": "partially_accurate",
                            "paper_found": True,
                            "what_study_actually_found": "Small trials suggest benefit.",
                        },
                        "evidence_rating": {
                            "evidence_label": "moderate",
                            "consensus_alignment": "mixed",
                            "missing_context": "Small sample sizes.",
                        },
                        "recommended_framing": "Promising but preliminary.",
                        "key_citations": [
                            {
                                "label": "Example et al. (2025)",
                                "detail": "Sleep Journal",
                                "doi": "10.1000/example",
                            }
                        ],
                    }
                ],
            }
            with open(os.path.join(run_dir, "claims.json"), "w", encoding="utf-8") as handle:
                json.dump(claims, handle)
            with open(os.path.join(run_dir, "evidence.json"), "w", encoding="utf-8") as handle:
                json.dump(evidence, handle)
            with open(os.path.join(run_dir, "production", "script_v3.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "title": "Sample Topic",
                        "scenes": [
                            {
                                "scene_id": "scene_001",
                                "heading": "Hook",
                                "narration": "Glycine may improve sleep quality.",
                                "claims_referenced": ["claim_001"],
                                "evidence_strength": "moderate",
                                "citations_to_show": [
                                    {"label": "Example et al. (2025)", "detail": "Sleep Journal"}
                                ],
                            }
                        ],
                    },
                    handle,
                )

            ensure_package_layout(run_dir)
            with open(
                os.path.join(run_dir, "production", "script_v3.json"),
                "r",
                encoding="utf-8",
            ) as handle:
                manifest = build_delivery_manifest(json.load(handle), evidence)
            with open(os.path.join(run_dir, "package", "delivery_manifest.json"), "w", encoding="utf-8") as handle:
                json.dump(manifest, handle)

            paths = build_package_artifacts(run_dir)
            self.assertTrue(os.path.exists(paths["topic_brief"]))
            self.assertTrue(os.path.exists(paths["web_dossier"]))
            self.assertTrue(os.path.exists(paths["chat_index"]))
            with open(paths["claims"], "r", encoding="utf-8") as handle:
                package_claims = json.load(handle)
            self.assertEqual(
                package_claims["claims"][0]["evidence_ids"],
                ["claim_001:evidence:01"],
            )

    def test_grounded_chat_refuses_high_risk_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = os.path.join(tmp, "sample-run")
            os.makedirs(os.path.join(run_dir, "package"), exist_ok=True)
            with open(os.path.join(run_dir, "package", "chat_index.json"), "w", encoding="utf-8") as handle:
                json.dump({"records": []}, handle)
            with open(os.path.join(run_dir, "package", "decision_table.json"), "w", encoding="utf-8") as handle:
                json.dump({"rows": []}, handle)
            with open(os.path.join(run_dir, "package", "web_dossier.json"), "w", encoding="utf-8") as handle:
                json.dump({}, handle)

            result = answer_grounded_question(run_dir, "What dose should I take for this supplement?")
            self.assertTrue(result["refused"])
            self.assertEqual(result["reason"], "treatment planning")

    def test_grounded_chat_answers_package_level_caveat_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = os.path.join(tmp, "sample-run")
            os.makedirs(os.path.join(run_dir, "package", "audits"), exist_ok=True)
            with open(os.path.join(run_dir, "package", "chat_index.json"), "w", encoding="utf-8") as handle:
                json.dump({"records": []}, handle)
            with open(os.path.join(run_dir, "package", "decision_table.json"), "w", encoding="utf-8") as handle:
                json.dump({"rows": []}, handle)
            with open(os.path.join(run_dir, "package", "topic_hub_fragment.json"), "w", encoding="utf-8") as handle:
                json.dump({"uncertainties": ["Precise-looking percentages often come from unidentifiable studies."]}, handle)
            with open(os.path.join(run_dir, "package", "web_dossier.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "page_id": "sample-run:dossier",
                        "title": "Sample Topic",
                        "topic_slug": "sample-topic",
                        "source_log": [{"source_id": "source-001"}],
                        "harms_and_caveats": ["Several claims still need stronger attribution."],
                        "what_this_does_not_mean": ["This package does not replace individualized medical advice."],
                        "practical_takeaway": "Use only the strongest-supported claims first.",
                    },
                    handle,
                )
            with open(os.path.join(run_dir, "package", "audits", "coverage.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "issues": [
                            {
                                "severity": "major",
                                "issue": "Some claims still have no attached evidence IDs",
                            }
                        ]
                    },
                    handle,
                )
            with open(os.path.join(run_dir, "package", "audits", "delivery.json"), "w", encoding="utf-8") as handle:
                json.dump({"issues": []}, handle)
            with open(os.path.join(run_dir, "package", "audits", "trust.json"), "w", encoding="utf-8") as handle:
                json.dump({"issues": []}, handle)

            result = answer_grounded_question(run_dir, "What are the biggest caveats in this package?")
            self.assertFalse(result["refused"])
            self.assertIn("traceability", result["answer"])
            self.assertIn("unidentifiable studies", result["answer"])
            self.assertIn("source-001", result["citations"][0]["source_ids"])

    def test_topic_hub_aggregation_groups_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            for run_id, rated_at in (("run-a", "2026-03-27T12:00:00"), ("run-b", "2026-03-28T12:00:00")):
                package_dir = os.path.join(tmp, run_id, "package")
                os.makedirs(package_dir, exist_ok=True)
                with open(os.path.join(package_dir, "topic_hub_fragment.json"), "w", encoding="utf-8") as handle:
                    json.dump(
                        {
                            "topic_id": f"{run_id}:topic",
                            "topic_slug": "glycine-sleep",
                            "title": "Glycine Sleep",
                            "summary": f"Summary for {run_id}",
                            "version": run_id,
                            "last_reviewed_at": rated_at,
                            "consensus": ["Strongest supported claim: claim_001"],
                            "uncertainties": ["Small sample sizes"],
                            "linked_pages": [{"kind": "dossier", "page_id": f"{run_id}:dossier"}],
                            "evidence_updates": [{"run_id": run_id, "rated_at": rated_at}],
                        },
                        handle,
                    )

            aggregated = aggregate_topic_hubs(tmp)
            self.assertEqual(len(aggregated["topics"]), 1)
            topic = aggregated["topics"][0]
            self.assertEqual(topic["topic_slug"], "glycine-sleep")
            self.assertEqual(topic["version"], "run-b")
            self.assertEqual(topic["runs"], ["run-b", "run-a"])

    def test_load_topic_bundle_combines_source_excerpts(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript_path = os.path.join(tmp, "source.json")
            with open(transcript_path, "w", encoding="utf-8") as handle:
                json.dump(
                    [
                        {"text": "First source segment.", "start": 0},
                        {"text": "Second source segment.", "start": 12},
                    ],
                    handle,
                )

            bundle_path = os.path.join(tmp, "bundle.json")
            with open(bundle_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "title": "Breakfast Pilot",
                        "topic": "Blood sugar breakfast habits",
                        "sources": [
                            {
                                "source_id": "src-001",
                                "title": "Source One",
                                "summary": "A useful source.",
                                "transcript_path": "source.json",
                                "start_seconds": 0,
                                "end_seconds": 20,
                            }
                        ],
                    },
                    handle,
                )

            loaded = load_topic_bundle(bundle_path)
            self.assertIn("First source segment.", loaded["transcript"])
            self.assertIn("Second source segment.", loaded["transcript"])
            self.assertEqual(loaded["bundle"]["title"], "Breakfast Pilot")
            self.assertTrue(loaded["bundle"]["external_research_notes"])


if __name__ == "__main__":
    unittest.main()
