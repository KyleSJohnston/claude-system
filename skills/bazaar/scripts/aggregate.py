#!/usr/bin/env python3
"""Deterministic scenario funding aggregator for bazaar skill.

@decision DEC-BAZAAR-005
@title Deterministic Python for aggregation — no LLM, no randomness
@status accepted
@rationale Funding aggregation must be reproducible and auditable. Using LLMs
for math introduces non-determinism and hallucination risk. Pure Python with
stdlib math produces identical results from identical inputs, making the
funding process transparent and debuggable. Kendall's W measures inter-judge
agreement; Gini coefficient measures funding concentration.

Inputs: list of judge allocation JSON files (each from a judge archetype)
Output: funded_scenarios.json with percentages, rankings, and agreement metrics

Aggregation rules:
- Weighted average across all judges (equal weight)
- 3% cutoff: scenarios below 3% of total are eliminated
- Surviving scenarios are re-normalized to 100%
- Minimum viable: 2 judges must succeed; if all fail → equal allocation fallback
- Gini coefficient and Kendall's W are computed for transparency
"""

import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ── Constants ─────────────────────────────────────────────────────────────────

CUTOFF_FRACTION = 0.03      # 3% of total: scenarios below this are eliminated
MIN_JUDGES = 2              # minimum judges needed for a valid aggregation
TOTAL_UNITS = 1000          # judges allocate this many units total


# ── Loading ───────────────────────────────────────────────────────────────────

def load_judge_file(path: Path) -> Optional[Dict]:
    """Load and validate a judge allocation file.

    Returns None if the file is malformed or missing required fields.
    """
    try:
        with open(path) as f:
            data = json.load(f)
        allocations = data.get("allocations", [])
        if not allocations:
            return None
        # Validate structure
        for a in allocations:
            if "scenario_id" not in a or "funding" not in a:
                return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def load_judge_files(paths: List[Path]) -> List[Dict]:
    """Load all judge files, silently skipping malformed ones."""
    results = []
    for p in paths:
        judge = load_judge_file(p)
        if judge is not None:
            results.append(judge)
    return results


# ── Aggregation math ──────────────────────────────────────────────────────────

def build_allocation_matrix(
    judges: List[Dict],
) -> Tuple[List[str], List[List[float]]]:
    """Convert judge allocations to a matrix of normalized fractions.

    Returns:
        (scenario_ids, matrix) where matrix[i][j] is judge i's allocation
        fraction for scenario j (sums to 1.0 per judge).
    """
    # Collect all unique scenario IDs
    all_ids: List[str] = []
    seen = set()
    for judge in judges:
        for a in judge.get("allocations", []):
            sid = a["scenario_id"]
            if sid not in seen:
                all_ids.append(sid)
                seen.add(sid)

    if not all_ids:
        return [], []

    matrix = []
    for judge in judges:
        alloc_map = {
            a["scenario_id"]: float(a["funding"])
            for a in judge.get("allocations", [])
        }
        total = sum(alloc_map.values()) or TOTAL_UNITS
        row = [alloc_map.get(sid, 0.0) / total for sid in all_ids]
        matrix.append(row)

    return all_ids, matrix


def weighted_average(matrix: List[List[float]]) -> List[float]:
    """Equal-weight average across judges for each scenario.

    Args:
        matrix: [judges x scenarios] matrix of normalized fractions

    Returns:
        List of average fractions (sums to ~1.0)
    """
    if not matrix:
        return []
    n_judges = len(matrix)
    n_scenarios = len(matrix[0])
    return [
        sum(matrix[j][s] for j in range(n_judges)) / n_judges
        for s in range(n_scenarios)
    ]


def apply_cutoff(
    scenario_ids: List[str],
    averages: List[float],
    cutoff: float = CUTOFF_FRACTION,
) -> Tuple[List[str], List[float]]:
    """Eliminate scenarios below the cutoff fraction and re-normalize.

    Args:
        scenario_ids: List of scenario identifier strings
        averages: Corresponding average fractions (sum ≈ 1.0)
        cutoff: Minimum fraction to survive (default 3%)

    Returns:
        (surviving_ids, re_normalized_fractions)
    """
    surviving = [
        (sid, avg)
        for sid, avg in zip(scenario_ids, averages)
        if avg >= cutoff
    ]

    if not surviving:
        # All eliminated: equal allocation fallback
        n = len(scenario_ids)
        return scenario_ids[:], [1.0 / n] * n

    ids = [s[0] for s in surviving]
    fracs = [s[1] for s in surviving]
    total = sum(fracs)
    renorm = [f / total for f in fracs]
    return ids, renorm


def gini_coefficient(fractions: List[float]) -> float:
    """Compute Gini coefficient for funding concentration.

    0.0 = perfectly equal; 1.0 = fully concentrated.

    Uses the standard sorted-difference formula:
        G = (2 * sum(i * x_i) / (n * sum(x_i))) - (n+1)/n
    where x_i are sorted values and i is 1-indexed rank.
    """
    if not fractions or len(fractions) == 1:
        return 0.0
    n = len(fractions)
    s = sorted(fractions)
    total = sum(s)
    if total == 0:
        return 0.0
    weighted_sum = sum((i + 1) * x for i, x in enumerate(s))
    return (2 * weighted_sum / (n * total)) - (n + 1) / n


def kendalls_w(matrix: List[List[float]]) -> float:
    """Compute Kendall's W (coefficient of concordance) for judge agreement.

    W = 1.0: judges perfectly agree on rankings.
    W = 0.0: no agreement beyond chance.

    Uses the standard formula based on rank sums:
        W = 12 * S / (m^2 * (n^3 - n))
    where S = sum of squared deviations of rank sums from mean rank sum,
    m = number of judges, n = number of scenarios.

    Returns 0.0 for degenerate inputs (0 or 1 judge/scenario).
    """
    if not matrix or len(matrix) < 2:
        return 0.0
    m = len(matrix)       # judges
    n = len(matrix[0])    # scenarios
    if n < 2:
        return 0.0

    # Convert fractions to ranks (1 = lowest funding, n = highest)
    def rank_row(row: List[float]) -> List[float]:
        indexed = sorted(enumerate(row), key=lambda x: x[1])
        ranks = [0.0] * len(row)
        for rank, (idx, _) in enumerate(indexed):
            ranks[idx] = float(rank + 1)
        return ranks

    rank_matrix = [rank_row(row) for row in matrix]

    # Column rank sums
    col_sums = [sum(rank_matrix[j][s] for j in range(m)) for s in range(n)]
    mean_col_sum = sum(col_sums) / n
    S = sum((cs - mean_col_sum) ** 2 for cs in col_sums)

    denom = m * m * (n ** 3 - n)
    if denom == 0:
        return 0.0
    return 12 * S / denom


# ── Output assembly ───────────────────────────────────────────────────────────

def build_output(
    scenario_ids: List[str],
    fractions: List[float],
    all_scenario_ids: List[str],
    all_averages: List[float],
    matrix: List[List[float]],
    judge_count: int,
    fallback_used: bool,
) -> Dict:
    """Assemble the funded_scenarios.json output structure."""
    # Sort by funding (descending)
    ranked = sorted(zip(scenario_ids, fractions), key=lambda x: -x[1])

    funded = [
        {
            "rank": i + 1,
            "scenario_id": sid,
            "funding_fraction": round(frac, 6),
            "funding_percent": round(frac * 100, 2),
        }
        for i, (sid, frac) in enumerate(ranked)
    ]

    # Eliminated scenarios
    surviving_set = set(scenario_ids)
    eliminated = [
        {
            "scenario_id": sid,
            "average_fraction": round(avg, 6),
            "reason": f"below {CUTOFF_FRACTION*100:.0f}% cutoff",
        }
        for sid, avg in zip(all_scenario_ids, all_averages)
        if sid not in surviving_set
    ]

    w = kendalls_w(matrix) if matrix else 0.0
    g = gini_coefficient(fractions)

    agreement_label = (
        "high" if w >= 0.7
        else "moderate" if w >= 0.4
        else "low"
    )

    return {
        "funded_scenarios": funded,
        "eliminated_scenarios": eliminated,
        "metrics": {
            "judge_count": judge_count,
            "scenario_count_before_cutoff": len(all_scenario_ids),
            "scenario_count_funded": len(funded),
            "kendalls_w": round(w, 4),
            "agreement": agreement_label,
            "gini_coefficient": round(g, 4),
            "cutoff_fraction": CUTOFF_FRACTION,
            "fallback_used": fallback_used,
        },
    }


# ── Entry point ───────────────────────────────────────────────────────────────

def aggregate(judge_paths: List[Path], output_path: Optional[Path] = None) -> Dict:
    """Main aggregation entry point.

    Args:
        judge_paths: Paths to judge allocation JSON files
        output_path: If provided, write result to this path

    Returns:
        The funded_scenarios dict (also written to output_path if given)

    Raises:
        ValueError: If fewer than MIN_JUDGES valid judge files are found
    """
    judges = load_judge_files(judge_paths)

    if len(judges) < MIN_JUDGES:
        raise ValueError(
            f"Need at least {MIN_JUDGES} valid judge files, got {len(judges)}"
        )

    all_ids, matrix = build_allocation_matrix(judges)

    if not all_ids:
        raise ValueError("No scenario IDs found in judge files")

    averages = weighted_average(matrix)
    surviving_ids, surviving_fracs = apply_cutoff(all_ids, averages)

    # Detect if equal fallback was triggered
    fallback_used = len(surviving_ids) == len(all_ids) and all(
        abs(f - surviving_fracs[0]) < 1e-9 for f in surviving_fracs
    )

    result = build_output(
        scenario_ids=surviving_ids,
        fractions=surviving_fracs,
        all_scenario_ids=all_ids,
        all_averages=averages,
        matrix=matrix,
        judge_count=len(judges),
        fallback_used=fallback_used,
    )

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

    return result


def main():
    """CLI entry point: aggregate <output.json> <judge1.json> [judge2.json ...]"""
    if len(sys.argv) < 3:
        print(
            "Usage: aggregate.py <output.json> <judge1.json> [judge2.json ...]",
            file=sys.stderr,
        )
        sys.exit(1)

    output_path = Path(sys.argv[1])
    judge_paths = [Path(p) for p in sys.argv[2:]]

    try:
        result = aggregate(judge_paths, output_path)
        funded = result["funded_scenarios"]
        metrics = result["metrics"]
        print(f"Funded {metrics['scenario_count_funded']} scenarios "
              f"(eliminated {metrics['scenario_count_before_cutoff'] - metrics['scenario_count_funded']})")
        print(f"Kendall's W: {metrics['kendalls_w']} ({metrics['agreement']} agreement)")
        print(f"Gini: {metrics['gini_coefficient']}")
        for s in funded:
            print(f"  #{s['rank']} {s['scenario_id']}: {s['funding_percent']:.1f}%")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
