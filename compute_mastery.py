"""
Step 2: Compute per-tag mastery scores from a user's submission history.

Design choices (locked in for v1, per our earlier discussion):
- Solved / not-solved only - failed attempts don't count yet.
- No recency weighting - a solve from a year ago counts the same as one from
  yesterday. Both of these are easy to add later without changing the shape
  of the output, so we're not boxing ourselves in.

Mastery model:
  For each tag, mastery = (average rating of problems the user has SOLVED
  with that tag) / (user's overall average solved rating), capped at 1.0.

  Intuition: if you solve 1600-rated "dp" problems while your overall average
  is 1800, dp is relatively weak for you (mastery < 1.0). If you've never
  solved anything tagged "dp", mastery = 0.0 - the strongest possible signal
  that it's a gap.

This also directly feeds the metrics we discussed:
  - "weak tag" = mastery below a threshold (default 0.7)
  - overall_avg_rating becomes the baseline for "difficulty-band accuracy@k"
    in step 3 (target difficulty = overall_avg_rating + a growth margin)
"""

import json
from pathlib import Path
from statistics import mean

CACHE_DIR = Path("cf_cache")
WEAK_TAG_THRESHOLD = 0.7  # mastery below this counts as "weak" for coverage@k


def load_user_history(handle: str) -> list[dict]:
    path = CACHE_DIR / f"user_{handle}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No cached history for '{handle}' - run codeforces_data.py first"
        )
    return json.loads(path.read_text())


def compute_tag_mastery(history: list[dict]) -> dict:
    """
    Returns:
        {
          "overall_avg_rating": 1742.3,
          "tags": {
              "dp": {"solved_count": 4, "avg_rating": 1600.0, "mastery": 0.918},
              "graphs": {"solved_count": 0, "avg_rating": None, "mastery": 0.0},
              ...
          }
        }
    """
    # Dedupe: a problem can be submitted many times, we only care that it was
    # solved at least once. Key by (contestId, index) since that's CF's
    # unique problem identifier.
    solved_problems = {}
    for sub in history:
        if sub["verdict"] != "OK":
            continue
        p = sub["problem"]
        key = (p["contestId"], p["index"])
        solved_problems[key] = p  # overwrite is fine, same problem each time

    solved_list = list(solved_problems.values())

    if not solved_list:
        raise ValueError("User has no solved problems yet - nothing to score")

    overall_avg_rating = mean(p["rating"] for p in solved_list)

    # Collect solved ratings per tag
    ratings_by_tag: dict[str, list[int]] = {}
    for p in solved_list:
        for tag in p["tags"]:
            ratings_by_tag.setdefault(tag, []).append(p["rating"])

    tag_mastery = {}
    for tag, ratings in ratings_by_tag.items():
        avg_rating = mean(ratings)
        mastery = min(1.0, avg_rating / overall_avg_rating)
        tag_mastery[tag] = {
            "solved_count": len(ratings),
            "avg_rating": round(avg_rating, 1),
            "mastery": round(mastery, 3),
        }

    return {
        "overall_avg_rating": round(overall_avg_rating, 1),
        "tags": tag_mastery,
    }


def print_mastery_heatmap(mastery_data: dict, all_catalog_tags: set[str] | None = None):
    """Quick terminal 'heatmap' - sorted weakest to strongest. Demo-friendly."""
    tags = dict(mastery_data["tags"])

    # Include tags the user has NEVER solved (if we have the full catalog's
    # tag list) - these are mastery=0.0, the clearest gaps of all.
    if all_catalog_tags:
        for tag in all_catalog_tags:
            if tag not in tags:
                tags[tag] = {"solved_count": 0, "avg_rating": None, "mastery": 0.0}

    print(f"Overall avg solved rating: {mastery_data['overall_avg_rating']}\n")
    print(f"{'tag':<20} {'solved':>7} {'avg rating':>11} {'mastery':>8}  weak?")
    for tag, info in sorted(tags.items(), key=lambda kv: kv[1]["mastery"]):
        weak_flag = "  <-- WEAK" if info["mastery"] < WEAK_TAG_THRESHOLD else ""
        avg_r = info["avg_rating"] if info["avg_rating"] is not None else "-"
        print(f"{tag:<20} {info['solved_count']:>7} {str(avg_r):>11} {info['mastery']:>8}{weak_flag}")


def get_weak_tags(mastery_data: dict, all_catalog_tags: set[str], threshold: float = WEAK_TAG_THRESHOLD) -> list[str]:
    """Every tag below the mastery threshold, including never-attempted ones."""
    tags = mastery_data["tags"]
    weak = [t for t, info in tags.items() if info["mastery"] < threshold]
    unattempted = [t for t in all_catalog_tags if t not in tags]
    return sorted(set(weak) | set(unattempted))


if __name__ == "__main__":
    handle = "tourist"  # replace with your own handle
    history = load_user_history(handle)
    mastery_data = compute_tag_mastery(history)

    problems = json.loads((CACHE_DIR / "problems.json").read_text())
    all_tags = {t for p in problems for t in p["tags"]}

    print_mastery_heatmap(mastery_data, all_catalog_tags=all_tags)

    weak_tags = get_weak_tags(mastery_data, all_tags)
    print(f"\nWeak tags ({len(weak_tags)}): {weak_tags}")

    # Cache for step 3
    out_path = CACHE_DIR / f"mastery_{handle}.json"
    out_path.write_text(json.dumps(mastery_data, indent=2))
    print(f"\nSaved mastery profile to {out_path}")
