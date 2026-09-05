"""
Step 13: Evaluation harness.

Run against a small golden set of transcripts with known-correct action
items/decisions/dates and known-correct hard-trigger hits, and measure:
  - Precision/recall on action items and decisions (fuzzy text match)
  - Hallucination rate: fraction of extracted items that fail grounding verification
  - False-negative rate on hard triggers (should be ~0 -- these are safety-critical)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import List, Dict, Any
from core.schema import CallReport


@dataclass
class GoldenCase:
    call_id: str
    call_date: str
    call_type: str
    transcript_text: str
    expected_decisions: List[str] = field(default_factory=list)
    expected_action_items: List[str] = field(default_factory=list)
    expected_triggers: List[str] = field(default_factory=list)  # e.g. ["cease_and_desist"]


def _fuzzy_match(a: str, b: str, threshold: float = 0.55) -> bool:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold


def _precision_recall(expected: List[str], predicted: List[str]) -> Dict[str, float]:
    if not expected and not predicted:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    matched_expected = set()
    matched_predicted = set()
    for i, e in enumerate(expected):
        for j, p in enumerate(predicted):
            if j in matched_predicted:
                continue
            if _fuzzy_match(e, p):
                matched_expected.add(i)
                matched_predicted.add(j)
                break
    precision = len(matched_predicted) / len(predicted) if predicted else 0.0
    recall = len(matched_expected) / len(expected) if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


def score_report(golden: GoldenCase, report: CallReport, n_failed_grounding: int, n_total_extracted: int) -> Dict[str, Any]:
    decision_scores = _precision_recall(golden.expected_decisions, [d.text for d in report.decisions])
    action_scores = _precision_recall(golden.expected_action_items, [a.text for a in report.action_items])

    detected_trigger_kinds = {t.kind for t in report.special_triggers}
    trigger_recall = (
        len(detected_trigger_kinds & set(golden.expected_triggers)) / len(golden.expected_triggers)
        if golden.expected_triggers else 1.0
    )
    trigger_false_negatives = set(golden.expected_triggers) - detected_trigger_kinds

    hallucination_rate = round(n_failed_grounding / n_total_extracted, 3) if n_total_extracted else 0.0

    return {
        "call_id": golden.call_id,
        "decisions": decision_scores,
        "action_items": action_scores,
        "trigger_recall": round(trigger_recall, 3),
        "trigger_false_negatives": sorted(trigger_false_negatives),
        "hallucination_rate": hallucination_rate,
    }


def run_eval_suite(cases_and_reports: List[tuple]) -> Dict[str, Any]:
    """cases_and_reports: list of (GoldenCase, CallReport, n_failed, n_total) tuples."""
    results = [score_report(g, r, nf, nt) for g, r, nf, nt in cases_and_reports]
    avg = lambda key, sub: sum(r[key][sub] for r in results) / len(results) if results else 0.0
    summary = {
        "n_cases": len(results),
        "avg_decision_f1": round(avg("decisions", "f1"), 3),
        "avg_action_item_f1": round(avg("action_items", "f1"), 3),
        "avg_trigger_recall": round(sum(r["trigger_recall"] for r in results) / len(results), 3) if results else 0.0,
        "avg_hallucination_rate": round(sum(r["hallucination_rate"] for r in results) / len(results), 3) if results else 0.0,
        "any_trigger_false_negatives": any(r["trigger_false_negatives"] for r in results),
    }
    return {"summary": summary, "per_case": results}
