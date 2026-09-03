"""
Step 4: Select the final top-k recommendations from the scored candidates.

Two things happen here:
  1. Heap-based top-k selection - instead of sorting the *entire* candidate
     list (O(n log n) over potentially tens of thousands of problems just to
     keep the top 5), we heapify once in O(n) and pop only what we need in
     O(k log n). This is the concrete DSA decision worth explaining in the
     demo: "we don't need a full sort, we need the top few, so a heap is the
     right tool."
  2. Tag diversity - without a constraint, the top-k often collapses into
     "5 dp problems" because dp happened to be the single weakest tag. We
     enforce a per-tag cap while popping from the heap, so recommendations
     spread across multiple weak areas instead of drilling one.
"""

import heapq
import json
from pathlib import Path

CACHE_DIR = Path("cf_cache")

DEFAULT_K = 5
MAX_PER_TAG = 2  # no more than this many recommendations share any one tag


def select_top_k(
    scored_candidates: list[dict],
    k: int = DEFAULT_K,
    max_per_tag: int = MAX_PER_TAG,
) -> list[dict]:
    """
    Heap-based top-k with a tag-diversity constraint.

    Build a max-heap (via negated scores) in O(n), then pop candidates in
    score order, skipping any that would push a tag over max_per_tag, until
    we have k picks or the heap is exhausted.
    """
    # heapq is a min-heap, so negate the score to simulate a max-heap.
    # Include an index as a tiebreaker so heapq never tries to compare dicts.
    heap = [(-c["final_score"], i, c) for i, c in enumerate(scored_candidates)]
    heapq.heapify(heap)  # O(n)

    tag_counts: dict[str, int] = {}
    selected: list[dict] = []

    while heap and len(selected) < k:
        neg_score, _, candidate = heapq.heappop(heap)  # O(log n) per pop
        problem = candidate["problem"]

        # Would picking this problem push any of its tags over the cap?
        if any(tag_counts.get(t, 0) >= max_per_tag for t in problem["tags"]):
            continue

        selected.append(candidate)
        for t in problem["tags"]:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    return selected


def explain_recommendation(candidate: dict, mastery_data: dict) -> str:
    """Human-readable 'why' for the demo - makes the scoring legible."""
    p = candidate["problem"]
    overall_avg = mastery_data["overall_avg_rating"]
    weakest_tags = sorted(
        p["tags"],
        key=lambda t: mastery_data["tags"].get(t, {"mastery": 0.0})["mastery"],
    )[:2]  # show the 1-2 weakest tags this problem targets

    return (
        f"{p['name']} (rating {p['rating']}, tags: {', '.join(p['tags'])})\n"
        f"  -> targets weak tag(s): {', '.join(weakest_tags)}\n"
        f"  -> difficulty is {p['rating'] - overall_avg:+.0f} vs your avg solved rating "
        f"({overall_avg:.0f}), aiming for a growth stretch\n"
        f"  -> score breakdown: weak_tag={candidate['weak_tag_score']}, "
        f"difficulty={candidate['difficulty_score']}, final={candidate['final_score']}"
    )


if __name__ == "__main__":
    handle = "DNR"  # replace with your own handle

    scored = json.loads((CACHE_DIR / f"scored_{handle}.json").read_text())
    mastery_data = json.loads((CACHE_DIR / f"mastery_{handle}.json").read_text())

    top_k = select_top_k(scored, k=DEFAULT_K, max_per_tag=MAX_PER_TAG)

    print(f"Top {len(top_k)} recommendations for '{handle}':\n")
    for i, candidate in enumerate(top_k, 1):
        print(f"{i}. {explain_recommendation(candidate, mastery_data)}\n")

    # These two lines ARE your weak-tag-coverage@k and difficulty-band-accuracy@k
    # metrics from earlier - average them across the top_k for a headline number.
    avg_weak_tag = sum(c["weak_tag_score"] for c in top_k) / len(top_k)
    avg_difficulty = sum(c["difficulty_score"] for c in top_k) / len(top_k)
    distinct_tags = {t for c in top_k for t in c["problem"]["tags"]}

    print("--- Metrics for this recommendation set ---")
    print(f"Avg weak-tag score:   {avg_weak_tag:.3f}")
    print(f"Avg difficulty score: {avg_difficulty:.3f}")
    print(f"Distinct tags covered: {len(distinct_tags)} ({sorted(distinct_tags)})")
