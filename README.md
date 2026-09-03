# codeGuru 🧭

**A personalized competitive programming problem recommender, built on real Codeforces data.**

codeGuru looks at your actual Codeforces solve history, figures out which topics you're weak in, and recommends your next 5 problems — each picked to target a genuine gap in your skills and pushed just far enough past your comfort zone to help you grow.

No generic "top 50 DP problems" lists. No guessing what to practice next. Just your data, scored and ranked. 🎯

---

## 💡 Why this exists

Most practice-problem lists are one-size-fits-all. codeGuru instead asks: *given everything this specific person has already solved, what should they solve next?* It's built as a from-scratch recommender system — no black-box ML API calls, no hidden logic — so every recommendation comes with a clear, human-readable explanation of why it was chosen.

Built during the **BuildSprint** hackathon by [LatentForce.ai](https://latentforce.ai), using LatentCode. 🚀

---

## ⚙️ How it works

1. **Fetch** — pulls your full public submission history and the entire Codeforces problem catalog (tags + difficulty ratings) from the official Codeforces API.
2. **Score mastery** — for every tag you've touched (e.g. `dp`, `graphs`, `greedy`), computes a mastery score by comparing the average difficulty of problems you've *solved* in that tag against your overall average solved difficulty. Never solved anything in a tag? Mastery = 0 — the clearest possible gap.
3. **Score candidates** — every problem you haven't attempted yet is scored on two axes:
   - **Weak-tag match** — how much it targets tags you're weak in
   - **Difficulty fit** — how close it sits to your "growth zone" (slightly above your current average, not wildly out of reach)
4. **Select top-k** — a heap-based selection pulls out your top 5 picks in `O(k log n)` instead of sorting the entire candidate pool, while enforcing tag diversity so you don't end up with five variations of the same topic.

```
Your browser  ──>  Flask backend (localhost)  ──>  Codeforces API
             <──  same-origin JSON            <──
```

The backend exists because Codeforces' API doesn't send CORS headers, so a browser can't call it directly — Flask fetches server-side (where that restriction doesn't apply) and re-serves the data from the same origin as the frontend.

---

## Features

- 🔍 Pulls real, live submission history for any public Codeforces handle
- 🎯 Per-tag mastery heatmap, weakest tags first
- 🧠 Transparent scoring — every recommendation shows exactly *why* it was picked
- 📊 Built-in evaluation metrics: weak-tag coverage, difficulty-band accuracy, tag diversity
- ⚡ Heap-based top-k selection instead of a full sort — a deliberate algorithmic choice, not just a convenience
- 🎨 Rating badges colored using Codeforces' own tier system (Newbie → Grandmaster)

---

## Tech stack

- **Backend:** Python, Flask
- **Frontend:** vanilla HTML/CSS/JS (no framework, no build step)
- **Data source:** [Codeforces public API](https://codeforces.com/apiHelp)

---

## Getting started

### Prerequisites
- Python 3
- pip

### Installation

```bash
git clone <this-repo-url>
cd codeguru

# Recommended: use a virtual environment
python3 -m venv venv
source venv/bin/activate
pip install flask

# Alternative if you hit an "externally managed environment" error:
# sudo apt install python3-flask
```

### Run it

```bash
python3 app.py
```

Then open **http://localhost:5000** in your browser, enter any public Codeforces handle, and hit **Get recommendations**.

---

## Project structure

```
codeguru/
├── app.py                  # Flask backend — proxies Codeforces API, serves the UI
├── codeforces_data.py       # Fetches & caches problem catalog + user submission history
├── compute_mastery.py       # Standalone prototype: per-tag mastery scoring (Python)
├── score_problems.py        # Standalone prototype: candidate scoring logic (Python)
├── top_k_selector.py         # Standalone prototype: heap-based top-k + diversity (Python)
├── codeGuru.html             # Frontend UI — full scoring pipeline reimplemented in JS
└── cf_cache/                 # Auto-created cache of fetched Codeforces data
```

> Note: `compute_mastery.py`, `score_problems.py`, and `top_k_selector.py` were built as standalone prototypes to design and validate the scoring logic step by step. The live app (`codeGuru.html`) reimplements that same logic in JavaScript so it can run entirely in-browser against data served by `app.py`.

---

## The scoring formula

For a candidate problem, given the user's overall average solved rating `R`:

```
weak_tag_score  = average(1 - mastery(tag))  across the problem's tags
difficulty_score = 1 - |problem.rating - (R + 150)| / 250   (clamped to [0, 1])

final_score = 0.6 × weak_tag_score + 0.4 × difficulty_score
```

- `+150` targets a deliberate "growth zone" slightly above comfortable
- The `250`-point tolerance window keeps recommendations from being wildly too easy or too hard
- Weights (0.6 / 0.4) favor closing skill gaps slightly more than exact difficulty fit — tunable in code

---

## Evaluation

Rather than relying on a black-box "trust me," every recommendation set reports:

- **Weak-tag coverage@k** — how many of the top-k picks target a genuinely weak tag
- **Difficulty-band accuracy@k** — how many land inside the target growth zone
- **Tag diversity** — how many distinct topics are represented in the top-k

---

## Roadmap

- [ ] Learn scoring weights from user feedback instead of fixed 0.6/0.4 (logistic regression)
- [ ] Held-out historical evaluation (hide recent solves, check overlap with recommendations)
- [ ] Recency-weighted mastery (recent solves count more than old ones)
- [ ] Account for failed attempts, not just solved/unsolved
- [ ] Optional LeetCode integration

---

## Acknowledgments

Built for the **BuildSprint** hackathon by [LatentForce.ai](https://latentforce.ai). Problem and user data courtesy of the [Codeforces API](https://codeforces.com/apiHelp).
