#!/usr/bin/env python3
"""Word budget computation and report structure generation for bazaar skill.

@decision DEC-BAZAAR-005
@title Deterministic Python for word budget and report structure
@status accepted
@rationale Report word allocation must be reproducible given identical funding
percentages. Min/max constraints (100 words floor, 40% ceiling) prevent
over-compression of small scenarios and over-dominance of large ones.
The output feeds directly into the report template — no LLM involvement
in the math layer. Template population is string substitution only.

Inputs: funded_scenarios.json from aggregate.py, optional word budget
Output: report_structure.json with per-section word targets, filled template

Budget rules:
- Total budget: configurable (default 3000 words)
- Min per section: 100 words
- Max per section: 40% of total
- Allocation is proportional after applying min/max constraints
- Iteration to convergence when constraints cause budget over/underflow
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_TOTAL_WORDS = 3000
MIN_WORDS_PER_SECTION = 100
MAX_FRACTION_PER_SECTION = 0.40   # no scenario gets more than 40% of total


# ── Core allocation ───────────────────────────────────────────────────────────

def allocate_words(
    funded: List[Dict],
    total_words: int = DEFAULT_TOTAL_WORDS,
    min_words: int = MIN_WORDS_PER_SECTION,
    max_fraction: float = MAX_FRACTION_PER_SECTION,
) -> List[Dict]:
    """Compute word budgets for each funded scenario.

    Uses iterative proportional allocation with floor/ceiling constraints:
    1. Apply proportional allocation from funding_fraction
    2. Enforce min_words floor and max_fraction ceiling
    3. Re-distribute surplus/deficit to unconstrained scenarios
    4. Repeat until stable (usually 2-3 iterations)

    Args:
        funded: List of funded scenario dicts from funded_scenarios.json
        total_words: Total word budget for all scenario sections
        min_words: Minimum words per scenario section
        max_fraction: Maximum fraction of total any one scenario can receive

    Returns:
        List of dicts with scenario_id, funding_percent, word_budget, word_fraction
    """
    if not funded:
        return []

    n = len(funded)
    fractions = [s["funding_fraction"] for s in funded]
    max_words = int(total_words * max_fraction)

    # Iterative proportional allocation with persistent pinning.
    #
    # Key insight: once a scenario is pinned to min or max, it stays pinned.
    # Budget freed from capped scenarios (or needed for floored ones) is
    # redistributed proportionally to the remaining free scenarios.
    # Iteration terminates when no new scenarios are pinned.
    #
    # This is equivalent to solving:
    #   allocate total_words across n scenarios proportional to fractions,
    #   subject to: min_words <= alloc[i] <= max_words for all i.
    # The greedy pinning algorithm converges in at most n iterations.

    pinned = [None] * n  # None = free, value = pinned word count
    remaining_fracs = fractions[:]
    remaining_budget = total_words

    changed = True
    while changed:
        changed = False
        free_indices = [i for i in range(n) if pinned[i] is None]
        if not free_indices:
            break

        free_total_frac = sum(remaining_fracs[i] for i in free_indices)
        if free_total_frac <= 0:
            # Equal split among free
            share = remaining_budget / len(free_indices)
            for i in free_indices:
                remaining_fracs[i] = share
            free_total_frac = remaining_budget

        # Tentative allocation for each free scenario
        tentative = {
            i: (remaining_fracs[i] / free_total_frac) * remaining_budget
            for i in free_indices
        }

        # Pin any that violate constraints
        for i in free_indices:
            if tentative[i] < min_words:
                pinned[i] = min_words
                remaining_budget -= min_words
                remaining_fracs[i] = 0.0
                changed = True
            elif tentative[i] > max_words:
                pinned[i] = max_words
                remaining_budget -= max_words
                remaining_fracs[i] = 0.0
                changed = True

    # Assign final values: pinned scenarios get their pinned value,
    # free scenarios split the remaining budget proportionally.
    free_indices = [i for i in range(n) if pinned[i] is None]
    raw = [0.0] * n
    for i in range(n):
        if pinned[i] is not None:
            raw[i] = float(pinned[i])

    if free_indices:
        free_total_frac = sum(remaining_fracs[i] for i in free_indices)
        if free_total_frac <= 0:
            equal = remaining_budget / len(free_indices)
            for i in free_indices:
                raw[i] = equal
        else:
            for i in free_indices:
                raw[i] = (remaining_fracs[i] / free_total_frac) * remaining_budget

    # Round to integers, respecting constraints
    final = [max(min_words, min(max_words, int(round(raw[i])))) for i in range(n)]

    # Adjust rounding error by modifying the largest unconstrained section
    remainder = total_words - sum(final)
    if remainder != 0:
        # Find the index with the most room for adjustment
        idx = max(range(n), key=lambda i: final[i])
        final[idx] += remainder

    result = []
    for funded_s, words in zip(funded, final):
        result.append({
            "scenario_id": funded_s["scenario_id"],
            "rank": funded_s["rank"],
            "funding_percent": funded_s["funding_percent"],
            "word_budget": words,
            "word_fraction": round(words / total_words, 4),
        })

    return result


# ── Report structure ──────────────────────────────────────────────────────────

def build_report_structure(
    allocations: List[Dict],
    total_words: int,
    question: str = "",
    template_path: Optional[Path] = None,
) -> Dict:
    """Build the report structure dict with section definitions.

    Args:
        allocations: Output from allocate_words()
        total_words: Total word budget (for metadata)
        question: The original analytical question (for report header)
        template_path: Optional path to report-template.md for inclusion

    Returns:
        report_structure dict with sections and metadata
    """
    sections = []
    for a in sorted(allocations, key=lambda x: x["rank"]):
        sections.append({
            "section_number": a["rank"],
            "scenario_id": a["scenario_id"],
            "word_budget": a["word_budget"],
            "word_fraction": a["word_fraction"],
            "funding_percent": a["funding_percent"],
            "section_title": f"Scenario {a['rank']}: {a['scenario_id'].replace('-', ' ').title()}",
            "guidance": _section_guidance(a["funding_percent"], a["word_budget"]),
        })

    structure = {
        "question": question,
        "total_words": total_words,
        "section_count": len(sections),
        "sections": sections,
        "metadata": {
            "min_words_per_section": MIN_WORDS_PER_SECTION,
            "max_fraction_per_section": MAX_FRACTION_PER_SECTION,
            "word_budget_check": sum(s["word_budget"] for s in sections),
        },
    }

    if template_path and template_path.exists():
        structure["template"] = template_path.read_text()

    return structure


def _section_guidance(funding_percent: float, word_budget: int) -> str:
    """Generate writing guidance based on funding level."""
    if funding_percent >= 30:
        return (
            f"Flagship scenario ({word_budget} words). Lead with the thesis, "
            "provide full evidence chain, discuss implications in depth, "
            "include monitoring indicators."
        )
    elif funding_percent >= 15:
        return (
            f"Core scenario ({word_budget} words). Clear thesis, key evidence, "
            "primary implications. Concise but complete."
        )
    elif funding_percent >= 5:
        return (
            f"Supporting scenario ({word_budget} words). Thesis + 2-3 evidence "
            "points + key implication. Tight."
        )
    else:
        return (
            f"Minority scenario ({word_budget} words). One-paragraph treatment: "
            "what, why, and the single most important implication."
        )


# ── Template population ───────────────────────────────────────────────────────

def populate_template(
    template: str,
    structure: Dict,
    analyst_outputs: Optional[Dict[str, Dict]] = None,
) -> str:
    """Populate the report template with structure and analyst content.

    Simple string substitution — no LLM, no magic. The template uses
    {{PLACEHOLDER}} markers that this function replaces.

    Args:
        template: Template string from report-template.md
        structure: Report structure from build_report_structure()
        analyst_outputs: Optional dict of scenario_id -> analyst JSON output

    Returns:
        Populated report string (Markdown)
    """
    question = structure.get("question", "Analytical Question")
    total_words = structure["total_words"]
    sections = structure["sections"]

    # Build sections content
    sections_content = []
    for section in sections:
        sid = section["scenario_id"]
        title = section["section_title"]
        guidance = section["guidance"]
        budget = section["word_budget"]
        pct = section["funding_percent"]

        analyst_text = ""
        if analyst_outputs and sid in analyst_outputs:
            ao = analyst_outputs[sid]
            # Format analyst findings into prose stub
            findings = ao.get("findings", [])
            if findings:
                analyst_text = "\n".join(
                    f"- **{f.get('insight', '')}** ({f.get('confidence', '')} confidence)"
                    for f in findings[:3]
                )
            overall = ao.get("overall_assessment", "")
            if overall:
                analyst_text = f"{overall}\n\n{analyst_text}"

        section_md = (
            f"## {title}\n\n"
            f"*Funding: {pct:.1f}% | Target: ~{budget} words*\n\n"
        )
        if analyst_text:
            section_md += analyst_text + "\n\n"
        else:
            section_md += f"*[{guidance}]*\n\n"

        sections_content.append(section_md)

    result = template
    result = result.replace("{{QUESTION}}", question)
    result = result.replace("{{TOTAL_WORDS}}", str(total_words))
    result = result.replace("{{SECTION_COUNT}}", str(len(sections)))
    result = result.replace("{{SECTIONS}}", "\n".join(sections_content))

    return result


# ── Entry point ───────────────────────────────────────────────────────────────

def compute_report_structure(
    funded_path: Path,
    output_path: Optional[Path] = None,
    total_words: int = DEFAULT_TOTAL_WORDS,
    question: str = "",
    template_path: Optional[Path] = None,
) -> Dict:
    """Load funded_scenarios.json and produce report_structure.json.

    Args:
        funded_path: Path to funded_scenarios.json from aggregate.py
        output_path: If provided, write result here
        total_words: Total word budget
        question: Original analytical question for report header
        template_path: Optional path to report-template.md

    Returns:
        report_structure dict
    """
    with open(funded_path) as f:
        data = json.load(f)

    funded = data.get("funded_scenarios", [])
    allocations = allocate_words(funded, total_words=total_words)
    structure = build_report_structure(allocations, total_words, question, template_path)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(structure, f, indent=2)

    return structure


def main():
    """CLI: report.py <funded.json> <output.json> [total_words] [question]"""
    if len(sys.argv) < 3:
        print(
            "Usage: report.py <funded.json> <output.json> [total_words] [question]",
            file=sys.stderr,
        )
        sys.exit(1)

    funded_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    total_words = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_TOTAL_WORDS
    question = sys.argv[4] if len(sys.argv) > 4 else ""

    structure = compute_report_structure(funded_path, output_path, total_words, question)
    print(f"Report structure: {structure['section_count']} sections, {structure['total_words']} words total")
    for s in structure["sections"]:
        print(f"  #{s['section_number']} {s['scenario_id']}: {s['word_budget']} words ({s['funding_percent']:.1f}%)")


if __name__ == "__main__":
    main()
