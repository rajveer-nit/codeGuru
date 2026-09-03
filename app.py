"""
Backend proxy for the Codeforces API + static file server for ladder.html.

Why this exists: Codeforces' API doesn't send CORS headers, so a browser
can't call it directly from JS. A server has no such restriction - CORS is
a browser-enforced rule, not a server-to-server one. So this Flask app
fetches from Codeforces on the backend and re-serves the JSON from our own
origin, which the frontend can then fetch with zero CORS issues.

Reuses the fetching functions from codeforces_data.py (step 1) - no new
fetch logic, just a thin HTTP layer around what we already built.

Run:
    pip install flask
    python app.py
Then open http://localhost:5000
"""

from flask import Flask, jsonify, send_from_directory

from codeforces_data import fetch_problem_catalog, fetch_user_history

app = Flask(__name__, static_folder=".", static_url_path="")


@app.route("/")
def index():
    return send_from_directory(".", "codeGuru.html")


@app.route("/api/problems")
def api_problems():
    try:
        problems = fetch_problem_catalog()
        return jsonify(problems)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/history/<handle>")
def api_history(handle):
    try:
        history = fetch_user_history(handle)
        return jsonify(history)
    except RuntimeError as e:
        # Codeforces returns a comment like "handle: User not found" for
        # bad handles - surface that directly rather than a generic 500.
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
