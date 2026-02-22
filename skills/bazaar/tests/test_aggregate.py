"""Tests for bazaar/scripts/aggregate.py.

@decision DEC-BAZAAR-005
@title Deterministic Python for aggregation — no LLM, no randomness
@status accepted
@rationale Tests exercise the real aggregate.py implementation directly with no mocks.
Covers: matrix construction, weighted averages, Gini coefficient, Kendall's W,
3% cutoff logic, re-normalization, edge cases (all judges fail, single judge,
unanimous agreement, malformed files). Deterministic math means tests are exact.

No mocks — all tests use the real implementation directly.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to path (tests/ -> bazaar/ -> scripts/)
SKILL_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import aggregate as agg


class TestBuildAllocationMatrix(unittest.TestCase):

    def test_basic_matrix_construction(self):
        judges = [
            {"allocations": [
                {"scenario_id": "alpha", "funding": 600},
                {"scenario_id": "beta", "funding": 400},
            ]},
            {"allocations": [
                {"scenario_id": "alpha", "funding": 300},
                {"scenario_id": "beta", "funding": 700},
            ]},
        ]
        ids, matrix = agg.build_allocation_matrix(judges)
        self.assertEqual(set(ids), {"alpha", "beta"})
        self.assertEqual(len(matrix), 2)
        self.assertAlmostEqual(sum(matrix[0]), 1.0, places=9)
        self.assertAlmostEqual(sum(matrix[1]), 1.0, places=9)

    def test_missing_scenario_in_one_judge(self):
        """Judge that doesn't mention a scenario gets 0 allocation for it."""
        judges = [
            {"allocations": [
                {"scenario_id": "alpha", "funding": 1000},
            ]},
            {"allocations": [
                {"scenario_id": "alpha", "funding": 500},
                {"scenario_id": "beta", "funding": 500},
            ]},
        ]
        ids, matrix = agg.build_allocation_matrix(judges)
        alpha_idx = ids.index("alpha")
        beta_idx = ids.index("beta")
        # Judge 0 put nothing on beta
        self.assertAlmostEqual(matrix[0][beta_idx], 0.0, places=9)
        self.assertAlmostEqual(matrix[0][alpha_idx], 1.0, places=9)

    def test_empty_judges(self):
        ids, matrix = agg.build_allocation_matrix([])
        self.assertEqual(ids, [])
        self.assertEqual(matrix, [])


class TestWeightedAverage(unittest.TestCase):

    def test_equal_judges(self):
        matrix = [
            [0.6, 0.4],
            [0.6, 0.4],
        ]
        result = agg.weighted_average(matrix)
        self.assertAlmostEqual(result[0], 0.6, places=9)
        self.assertAlmostEqual(result[1], 0.4, places=9)

    def test_divergent_judges(self):
        matrix = [
            [1.0, 0.0],
            [0.0, 1.0],
        ]
        result = agg.weighted_average(matrix)
        self.assertAlmostEqual(result[0], 0.5, places=9)
        self.assertAlmostEqual(result[1], 0.5, places=9)

    def test_sums_to_one(self):
        matrix = [[0.3, 0.5, 0.2], [0.1, 0.6, 0.3], [0.4, 0.4, 0.2]]
        result = agg.weighted_average(matrix)
        self.assertAlmostEqual(sum(result), 1.0, places=9)

    def test_empty_matrix(self):
        self.assertEqual(agg.weighted_average([]), [])


class TestApplyCutoff(unittest.TestCase):

    def test_all_above_threshold(self):
        ids = ["alpha", "beta", "gamma"]
        avgs = [0.70, 0.25, 0.05]  # all above 3%
        surviving_ids, fracs = agg.apply_cutoff(ids, avgs, cutoff=0.03)
        self.assertEqual(set(surviving_ids), {"alpha", "beta", "gamma"})

    def test_eliminates_tiny_scenario(self):
        ids = ["alpha", "beta", "tiny"]
        avgs = [0.60, 0.38, 0.02]  # tiny is 2%, below 3% cutoff
        surviving_ids, fracs = agg.apply_cutoff(ids, avgs, cutoff=0.03)
        self.assertNotIn("tiny", surviving_ids)
        self.assertIn("alpha", surviving_ids)
        self.assertIn("beta", surviving_ids)

    def test_renormalization_to_one(self):
        ids = ["alpha", "beta", "tiny"]
        avgs = [0.50, 0.48, 0.02]
        surviving_ids, fracs = agg.apply_cutoff(ids, avgs, cutoff=0.03)
        self.assertAlmostEqual(sum(fracs), 1.0, places=6)

    def test_all_eliminated_fallback(self):
        """When all scenarios are below cutoff, fall back to equal allocation."""
        ids = ["alpha", "beta"]
        avgs = [0.001, 0.001]
        surviving_ids, fracs = agg.apply_cutoff(ids, avgs, cutoff=0.03)
        self.assertEqual(len(surviving_ids), 2)
        self.assertAlmostEqual(fracs[0], 0.5, places=6)
        self.assertAlmostEqual(fracs[1], 0.5, places=6)

    def test_single_surviving_scenario(self):
        ids = ["alpha", "tiny1", "tiny2"]
        avgs = [0.95, 0.03, 0.02]  # only alpha survives (tiny2 below 3.5% cutoff)
        surviving_ids, fracs = agg.apply_cutoff(ids, avgs, cutoff=0.035)
        self.assertIn("alpha", surviving_ids)
        alpha_idx = surviving_ids.index("alpha")
        self.assertAlmostEqual(fracs[alpha_idx], 1.0, places=3)


class TestGiniCoefficient(unittest.TestCase):

    def test_perfect_equality(self):
        """Equal allocation → Gini = 0."""
        fracs = [0.25, 0.25, 0.25, 0.25]
        g = agg.gini_coefficient(fracs)
        self.assertAlmostEqual(g, 0.0, places=6)

    def test_perfect_concentration(self):
        """Winner-take-all → Gini near 1."""
        fracs = [1.0, 0.0, 0.0, 0.0]
        g = agg.gini_coefficient(fracs)
        # For n=4, perfect concentration gives G = (n-1)/n = 0.75
        self.assertGreater(g, 0.7)

    def test_moderate_concentration(self):
        fracs = [0.5, 0.3, 0.15, 0.05]
        g = agg.gini_coefficient(fracs)
        self.assertGreater(g, 0.0)
        self.assertLess(g, 1.0)

    def test_single_element(self):
        self.assertEqual(agg.gini_coefficient([1.0]), 0.0)

    def test_empty(self):
        self.assertEqual(agg.gini_coefficient([]), 0.0)


class TestKendallsW(unittest.TestCase):

    def test_perfect_agreement(self):
        """All judges rank identically → W = 1.0."""
        matrix = [
            [0.5, 0.3, 0.2],
            [0.5, 0.3, 0.2],
            [0.5, 0.3, 0.2],
        ]
        w = agg.kendalls_w(matrix)
        self.assertAlmostEqual(w, 1.0, places=6)

    def test_no_agreement(self):
        """Perfect disagreement → W near 0."""
        matrix = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
        w = agg.kendalls_w(matrix)
        self.assertGreaterEqual(w, 0.0)
        self.assertLessEqual(w, 0.5)

    def test_single_judge(self):
        """Single judge → W = 0.0 (no agreement measurable)."""
        matrix = [[0.6, 0.4]]
        w = agg.kendalls_w(matrix)
        self.assertEqual(w, 0.0)

    def test_empty_matrix(self):
        self.assertEqual(agg.kendalls_w([]), 0.0)

    def test_single_scenario(self):
        matrix = [[1.0], [1.0], [1.0]]
        w = agg.kendalls_w(matrix)
        self.assertEqual(w, 0.0)

    def test_partial_agreement(self):
        matrix = [
            [0.5, 0.3, 0.2],
            [0.4, 0.35, 0.25],
            [0.6, 0.25, 0.15],
        ]
        w = agg.kendalls_w(matrix)
        self.assertGreater(w, 0.5)  # should be moderate-high agreement


class TestAggregateEndToEnd(unittest.TestCase):

    def setUp(self):
        self.fixtures_dir = Path(__file__).parent / "fixtures"
        self.sample_judges = json.loads(
            (self.fixtures_dir / "sample_judges.json").read_text()
        )

    def _write_judge_files(self, tmpdir: Path) -> list:
        """Write sample judge fixtures as individual files."""
        paths = []
        for i, judge in enumerate(self.sample_judges):
            path = tmpdir / f"judge_{i}.json"
            path.write_text(json.dumps(judge))
            paths.append(path)
        return paths

    def test_full_aggregation_from_fixtures(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            judge_paths = self._write_judge_files(tmp)
            output_path = tmp / "funded.json"

            result = agg.aggregate(judge_paths, output_path)

            self.assertIn("funded_scenarios", result)
            self.assertIn("metrics", result)
            self.assertTrue(output_path.exists())

            funded = result["funded_scenarios"]
            self.assertGreater(len(funded), 0)

            for s in funded:
                self.assertIn("scenario_id", s)
                self.assertIn("funding_percent", s)
                self.assertIn("rank", s)
                self.assertGreater(s["funding_percent"], 0)

    def test_funding_percentages_sum_to_100(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            judge_paths = self._write_judge_files(tmp)
            result = agg.aggregate(judge_paths)

            total_pct = sum(s["funding_percent"] for s in result["funded_scenarios"])
            self.assertAlmostEqual(total_pct, 100.0, places=1)

    def test_metrics_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            judge_paths = self._write_judge_files(tmp)
            result = agg.aggregate(judge_paths)

            metrics = result["metrics"]
            self.assertEqual(metrics["judge_count"], 4)
            self.assertIn("kendalls_w", metrics)
            self.assertIn("gini_coefficient", metrics)
            self.assertIn("agreement", metrics)

    def test_below_min_judges_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            judge_paths = self._write_judge_files(tmp)
            with self.assertRaises(ValueError):
                agg.aggregate(judge_paths[:1])  # only 1 judge, need 2

    def test_output_file_written(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            judge_paths = self._write_judge_files(tmp)
            output_path = tmp / "subdir" / "funded.json"

            agg.aggregate(judge_paths, output_path)
            self.assertTrue(output_path.exists())

            with open(output_path) as f:
                data = json.load(f)
            self.assertIn("funded_scenarios", data)

    def test_malformed_judge_file_skipped(self):
        """Malformed files are silently skipped; valid files still processed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            judge_paths = self._write_judge_files(tmp)

            bad_path = tmp / "bad_judge.json"
            bad_path.write_text("not valid json{{{")
            judge_paths.append(bad_path)

            result = agg.aggregate(judge_paths)
            self.assertEqual(result["metrics"]["judge_count"], 4)

    def test_unanimous_agreement_detected(self):
        """When all judges rank identically, Kendall's W should be 1.0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            uniform_judge = {
                "judge": "uniform",
                "allocations": [
                    {"scenario_id": "alpha", "funding": 500},
                    {"scenario_id": "beta", "funding": 300},
                    {"scenario_id": "gamma", "funding": 200},
                ],
                "total_allocated": 1000,
            }
            paths = []
            for i in range(3):
                p = tmp / f"judge_{i}.json"
                p.write_text(json.dumps(uniform_judge))
                paths.append(p)

            result = agg.aggregate(paths)
            self.assertAlmostEqual(result["metrics"]["kendalls_w"], 1.0, places=4)


if __name__ == "__main__":
    unittest.main()
