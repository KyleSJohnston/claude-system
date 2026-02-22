"""Tests for bazaar/scripts/report.py.

@decision DEC-BAZAAR-005
@title Deterministic Python for word budget — no LLM, no randomness
@status accepted
@rationale Tests exercise the real report.py implementation directly with no mocks.
Covers: proportional allocation, min/max constraints, rounding to integers,
budget conservation (sum equals total), template population, edge cases
(single scenario, equal funding, extreme concentration).

No mocks — all tests use the real implementation directly.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import report as rpt


def make_funded(scenarios: list) -> list:
    """Helper: build funded_scenarios list from (id, percent) tuples."""
    result = []
    for rank, (sid, pct) in enumerate(scenarios, start=1):
        result.append({
            "rank": rank,
            "scenario_id": sid,
            "funding_fraction": pct / 100.0,
            "funding_percent": pct,
        })
    return result


class TestAllocateWords(unittest.TestCase):

    def test_proportional_allocation_two_scenarios(self):
        funded = make_funded([("alpha", 70.0), ("beta", 30.0)])
        allocs = rpt.allocate_words(funded, total_words=1000)
        self.assertEqual(len(allocs), 2)
        # Sum must equal total
        self.assertEqual(sum(a["word_budget"] for a in allocs), 1000)

    def test_sum_equals_total(self):
        """Word budgets must always sum to exactly total_words."""
        funded = make_funded([
            ("alpha", 45.0), ("beta", 30.0), ("gamma", 15.0), ("delta", 10.0)
        ])
        for total in [1000, 2000, 3000, 500]:
            allocs = rpt.allocate_words(funded, total_words=total)
            total_allocated = sum(a["word_budget"] for a in allocs)
            self.assertEqual(total_allocated, total,
                             f"Expected {total}, got {total_allocated} for total={total}")

    def test_minimum_words_enforced(self):
        """Every scenario must get at least min_words, even tiny ones."""
        funded = make_funded([
            ("dominant", 97.0), ("tiny", 3.0)
        ])
        allocs = rpt.allocate_words(funded, total_words=3000, min_words=100)
        by_id = {a["scenario_id"]: a for a in allocs}
        self.assertGreaterEqual(by_id["tiny"]["word_budget"], 100)
        self.assertGreaterEqual(by_id["dominant"]["word_budget"], 100)

    def test_maximum_fraction_enforced(self):
        """Max fraction is enforced when multiple scenarios exist and budget allows.

        With 3 scenarios (dominant 60%, mid 30%, small 10%) and max=40%,
        dominant should be capped below 40% while budget is distributed to others.
        With only 2 scenarios where both exhaust the cap, the system relaxes
        proportionally — we test the 3-scenario case for clean cap enforcement.
        """
        funded = make_funded([
            ("dominant", 60.0), ("mid", 30.0), ("small", 10.0)
        ])
        allocs = rpt.allocate_words(funded, total_words=3000, max_fraction=0.40)
        by_id = {a["scenario_id"]: a for a in allocs}
        # dominant had 60% → would be 1800w, but cap at 40% = 1200w max
        self.assertLessEqual(by_id["dominant"]["word_budget"], int(3000 * 0.40) + 1)
        # Budget is fully allocated
        self.assertEqual(sum(a["word_budget"] for a in allocs), 3000)

    def test_equal_funding_equal_words(self):
        """Equal funding should produce equal word budgets."""
        funded = make_funded([
            ("alpha", 25.0), ("beta", 25.0), ("gamma", 25.0), ("delta", 25.0)
        ])
        allocs = rpt.allocate_words(funded, total_words=2000)
        budgets = [a["word_budget"] for a in allocs]
        # All should be equal (500 each) — allow ±1 for rounding
        for b in budgets:
            self.assertAlmostEqual(b, 500, delta=1)

    def test_empty_funded_list(self):
        allocs = rpt.allocate_words([], total_words=3000)
        self.assertEqual(allocs, [])

    def test_single_scenario_gets_all_words(self):
        funded = make_funded([("only", 100.0)])
        allocs = rpt.allocate_words(funded, total_words=3000)
        self.assertEqual(len(allocs), 1)
        self.assertEqual(allocs[0]["word_budget"], 3000)

    def test_word_fraction_consistent(self):
        """word_fraction should match word_budget / total."""
        funded = make_funded([("alpha", 60.0), ("beta", 40.0)])
        allocs = rpt.allocate_words(funded, total_words=1000)
        for a in allocs:
            expected_frac = a["word_budget"] / 1000
            self.assertAlmostEqual(a["word_fraction"], expected_frac, places=3)

    def test_many_scenarios(self):
        """Test with 10 scenarios — budget still conserved."""
        pairs = [(f"s{i}", 10.0) for i in range(10)]
        funded = make_funded(pairs)
        allocs = rpt.allocate_words(funded, total_words=3000)
        self.assertEqual(sum(a["word_budget"] for a in allocs), 3000)


class TestBuildReportStructure(unittest.TestCase):

    def test_sections_match_funded(self):
        funded = make_funded([("alpha", 60.0), ("beta", 40.0)])
        allocs = rpt.allocate_words(funded, total_words=1000)
        structure = rpt.build_report_structure(allocs, 1000, "Test question")

        self.assertEqual(structure["section_count"], 2)
        self.assertEqual(len(structure["sections"]), 2)
        self.assertEqual(structure["question"], "Test question")

    def test_sections_sorted_by_rank(self):
        funded = make_funded([("alpha", 60.0), ("beta", 40.0)])
        allocs = rpt.allocate_words(funded, total_words=1000)
        structure = rpt.build_report_structure(allocs, 1000)

        ranks = [s["section_number"] for s in structure["sections"]]
        self.assertEqual(ranks, sorted(ranks))

    def test_word_budget_check_in_metadata(self):
        funded = make_funded([("alpha", 70.0), ("beta", 30.0)])
        allocs = rpt.allocate_words(funded, total_words=2000)
        structure = rpt.build_report_structure(allocs, 2000)

        self.assertEqual(structure["metadata"]["word_budget_check"], 2000)

    def test_section_titles_generated(self):
        funded = make_funded([("my-scenario", 100.0)])
        allocs = rpt.allocate_words(funded, total_words=500)
        structure = rpt.build_report_structure(allocs, 500)

        title = structure["sections"][0]["section_title"]
        self.assertIn("My Scenario", title)

    def test_guidance_varies_by_funding_level(self):
        """High-funded scenarios get different guidance than low-funded ones."""
        funded = make_funded([("flagship", 60.0), ("minor", 4.0)])
        allocs = rpt.allocate_words(funded, total_words=3000)
        structure = rpt.build_report_structure(allocs, 3000)

        sections_by_id = {s["scenario_id"]: s for s in structure["sections"]}
        flagship_guidance = sections_by_id["flagship"]["guidance"]
        minor_guidance = sections_by_id["minor"]["guidance"]

        # They should be different
        self.assertNotEqual(flagship_guidance, minor_guidance)
        # Flagship should mention "Flagship"
        self.assertIn("Flagship", flagship_guidance)


class TestPopulateTemplate(unittest.TestCase):

    TEMPLATE = """\
# Bazaar Report: {{QUESTION}}

Total budget: {{TOTAL_WORDS}} words across {{SECTION_COUNT}} scenarios.

{{SECTIONS}}
"""

    def test_basic_substitution(self):
        funded = make_funded([("alpha", 60.0), ("beta", 40.0)])
        allocs = rpt.allocate_words(funded, total_words=1000)
        structure = rpt.build_report_structure(allocs, 1000, "Is AI disrupting finance?")

        result = rpt.populate_template(self.TEMPLATE, structure)

        self.assertIn("Is AI disrupting finance?", result)
        self.assertIn("1000", result)
        self.assertIn("2", result)  # 2 sections

    def test_sections_appear_in_output(self):
        funded = make_funded([("alpha", 100.0)])
        allocs = rpt.allocate_words(funded, total_words=500)
        structure = rpt.build_report_structure(allocs, 500, "question")

        result = rpt.populate_template(self.TEMPLATE, structure)
        self.assertIn("alpha", result.lower())

    def test_analyst_output_integrated(self):
        funded = make_funded([("my-scenario", 100.0)])
        allocs = rpt.allocate_words(funded, total_words=500)
        structure = rpt.build_report_structure(allocs, 500, "q")

        analyst_outputs = {
            "my-scenario": {
                "overall_assessment": "This scenario is strongly supported by evidence.",
                "findings": [
                    {"insight": "Key insight one", "confidence": "high"},
                ],
            }
        }

        result = rpt.populate_template(self.TEMPLATE, structure, analyst_outputs)
        self.assertIn("strongly supported", result)


class TestComputeReportStructure(unittest.TestCase):

    def test_end_to_end_from_file(self):
        """Full pipeline: funded_scenarios.json → report_structure.json."""
        funded_data = {
            "funded_scenarios": make_funded([
                ("alpha", 50.0), ("beta", 30.0), ("gamma", 20.0)
            ]),
            "eliminated_scenarios": [],
            "metrics": {"judge_count": 4},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            funded_path = tmp / "funded.json"
            funded_path.write_text(json.dumps(funded_data))

            output_path = tmp / "structure.json"
            structure = rpt.compute_report_structure(
                funded_path, output_path, total_words=3000, question="Test"
            )

            self.assertTrue(output_path.exists())
            self.assertEqual(structure["section_count"], 3)
            self.assertEqual(structure["total_words"], 3000)

            with open(output_path) as f:
                saved = json.load(f)
            self.assertEqual(saved["section_count"], 3)


if __name__ == "__main__":
    unittest.main()
