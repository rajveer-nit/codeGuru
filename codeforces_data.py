"""
Step 1: Fetch and cache data from the Codeforces public API.

Two endpoints, no auth required:
- problemset.problems -> the full catalog of problems (tags + difficulty rating)
- user.status?handle=... -> a specific user's full submission history

Codeforces asks that you don't hammer the API - keep to roughly 1 request/sec.
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

CF_API_BASE = "https://codeforces.com/api"
CACHE_DIR = Path("cf_cache")
CACHE_DIR.mkdir(exist_ok=True)


def _get(endpoint: str, params: dict | None = None) -> dict:
    """Low-level GET against the Codeforces API. Returns the 'result' payload."""
    url = f"{CF_API_BASE}/{endpoint}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"

    req = urllib.request.Request(url, headers={"User-Agent": "buildsprint-recommender/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Codeforces API HTTP error: {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Codeforces API unreachable: {e.reason}") from e

    if data.get("status") != "OK":
        # Codeforces puts a human-readable reason in 'comment', e.g. "handle not found"
        raise RuntimeError(f"Codeforces API error: {data.get('comment', 'unknown error')}")

    return data["result"]


def fetch_problem_catalog(force_refresh: bool = False) -> list[dict]:
    """
    Fetch every problem on Codeforces with its tags and difficulty rating.
    Cached to disk since this catalog only changes when new contests are added.

    Returns a list of dicts like:
        {"contestId": 4, "index": "A", "name": "Watermelon",
         "tags": ["math", "brute force"], "rating": 800}
    Problems without a rating (unrated / very old) are skipped.
    """
    cache_path = CACHE_DIR / "problems.json"
    if cache_path.exists() and not force_refresh:
        return json.loads(cache_path.read_text())

    result = _get("problemset.problems")
    problems = result["problems"]  # list of {contestId, index, name, rating, tags, ...}

    # Keep only problems that have a difficulty rating - unrated ones are hard to target
    rated_problems = [p for p in problems if "rating" in p]

    cache_path.write_text(json.dumps(rated_problems, indent=2))
    print(f"Cached {len(rated_problems)} rated problems to {cache_path}")
    return rated_problems


def fetch_user_history(handle: str, force_refresh: bool = False) -> list[dict]:
    """
    Fetch a user's full submission history.

    Returns a list of dicts like:
        {"problem": {"contestId": 4, "index": "A", "name": "Watermelon",
                     "tags": [...], "rating": 800},
         "verdict": "OK"}   # "OK" means accepted/solved; anything else means it failed
    """
    cache_path = CACHE_DIR / f"user_{handle}.json"
    if cache_path.exists() and not force_refresh:
        return json.loads(cache_path.read_text())

    result = _get("user.status", {"handle": handle})

    # We only need the problem info + verdict for scoring; trim the rest
    trimmed = [
        {"problem": s["problem"], "verdict": s.get("verdict", "UNKNOWN")}
        for s in result
    ]

    cache_path.write_text(json.dumps(trimmed, indent=2))
    print(f"Cached {len(trimmed)} submissions for handle '{handle}' to {cache_path}")
    return trimmed


if __name__ == "__main__":
    # Quick manual test - replace "tourist" with your own CF handle
    problems = fetch_problem_catalog()
    time.sleep(1)  # be polite between calls
    history = fetch_user_history("DNR")

    solved_count = len({
        (s["problem"]["contestId"], s["problem"]["index"])
        for s in history if s["verdict"] == "OK"
    })
    print(f"Problem catalog size: {len(problems)}")
    print(f"Unique problems solved by handle: {solved_count}")
