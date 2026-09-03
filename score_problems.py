"""
Step 3: Score every problem the user HASN'T touched yet.

Score = weighted combination of:
  1. weak_tag_score  - how much this problem hits tags the user is weak in
  2. difficulty_score - how close the problem's rating is to the user's
                         "growth zone" (slightly above their current average)

We deliberately don't pick the top-k here - that's step 4's job (heap-based
selection). This step just produces a scored candidate list.
"""

import json
from pathlib import Path

CACHE_DIR = Path("cf_cache")

# --- Tunable knobs -----------------------------------------------------
GROWTH_MARGIN = 150       # target difficulty = overall_avg_rating + this
DIFFICULTY_TOLERANCE = 250  # how far from target before difficulty_score hits 0
WEAK_TAG_WEIGHT = 0.6
DIFFICULTY_WEIGHT = 0.4
# ------------------------------------------------------------------------


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text())


def get_attempted_problem_keys(history: list[dict]) -> set[tuple]:
    """Any problem the user has ever submitted to (solved OR failed) -
    we don't recommend problems they've already seen, in v1."""
    return {(s["problem"]["contestId"], s["problem"]["index"]) for s in history}


def tag_mastery_lookup(mastery_data: dict) -> dict[str, float]:
    """tag -> mastery score, defaulting to 0.0 (max weak) for unlisted tags."""
    lookup = {tag: info["mastery"] for tag, info in mastery_data["tags"].items()}
    return lookup


def weak_tag_score(problem: dict, mastery_lookup: dict[str, float]) -> float:
    """
    Average (1 - mastery) across the problem's tags.
    A problem tagged entirely with tags the user has never solved (mastery=0
    for all) scores 1.0. A problem tagged entirely with tags the user is
    already strong in scores close to 0.0.
    """
    if not problem["tags"]:
        return 0.0
    gaps = [1.0 - mastery_lookup.get(tag, 0.0) for tag in problem["tags"]]
    return sum(gaps) / len(gaps)


def difficulty_score(problem: dict, overall_avg_rating: float) -> float:
    """
    1.0 at the exact target rating (avg + GROWTH_MARGIN), falling off
    linearly to 0.0 at +/- DIFFICULTY_TOLERANCE away from that target.
    """
    target = overall_avg_rating + GROWTH_MARGIN
    distance = abs(problem["rating"] - target)
    score = 1.0 - (distance / DIFFICULTY_TOLERANCE)
    return max(0.0, min(1.0, score))


def score_candidates(
    catalog: list[dict],
    history: list[dict],
    mastery_data: dict,
) -> list[dict]:
    """
    Returns a list of dicts, one per UNSEEN problem:
        {"problem": {...}, "weak_tag_score": .., "difficulty_score": ..,
         "final_score": ..}
    Not sorted / not trimmed - step 4 handles top-k selection.
    """
    attempted = get_attempted_problem_keys(history)
    mastery_lookup = tag_mastery_lookup(mastery_data)
    overall_avg = mastery_data["overall_avg_rating"]

    scored = []
    for p in catalog:
        key = (p["contestId"], p["index"])
        if key in attempted:
            continue  # skip anything the user has already seen

        wts = weak_tag_score(p, mastery_lookup)
        ds = difficulty_score(p, overall_avg)
        final = WEAK_TAG_WEIGHT * wts + DIFFICULTY_WEIGHT * ds

        scored.append({
            "problem": p,
            "weak_tag_score": round(wts, 3),
            "difficulty_score": round(ds, 3),
            "final_score": round(final, 3),
        })

    return scored


if __name__ == "__main__":
    handle = "DNR"  # replace with your own handle

    catalog = load_json(CACHE_DIR / "problems.json")
    history = load_json(CACHE_DIR / f"user_{handle}.json")
    mastery_data = load_json(CACHE_DIR / f"mastery_{handle}.json")

    scored = score_candidates(catalog, history, mastery_data)
    print(f"Scored {len(scored)} unseen problems "
          f"(target difficulty ~{mastery_data['overall_avg_rating'] + GROWTH_MARGIN:.0f})\n")

    # Sanity-check preview only - real top-k selection happens in step 4
    preview = sorted(scored, key=lambda x: x["final_score"], reverse=True)[:10]
    print(f"{'name':<35} {'rating':>6} {'weak':>6} {'diff':>6} {'final':>6}")
    for s in preview:
        p = s["problem"]
        print(f"{p['name'][:34]:<35} {p['rating']:>6} "
              f"{s['weak_tag_score']:>6} {s['difficulty_score']:>6} {s['final_score']:>6}")

    out_path = CACHE_DIR / f"scored_{handle}.json"
    out_path.write_text(json.dumps(scored, indent=2))
    print(f"\nSaved {len(scored)} scored candidates to {out_path}")
