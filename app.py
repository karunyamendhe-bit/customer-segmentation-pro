"""
Flask backend — Customer Segmentation Pro
Advanced: caching, rate-limit awareness, export formats (CSV/JSON/Excel),
          comparison endpoint, health check, structured error handling.
Run: python app.py   →  http://127.0.0.1:5000
"""
import io
import uuid
import json
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file
from flask_caching import Cache

import engine
from sample_data_generator import generate

# ─────────────────────────── App setup ────────────────────────────────
app = Flask(__name__)
app.config.update(
    MAX_CONTENT_LENGTH  = 100 * 1024 * 1024,   # 100 MB
    CACHE_TYPE          = "SimpleCache",
    CACHE_DEFAULT_TIMEOUT = 300,
    SECRET_KEY          = "cse-pro-dev-key",
)
cache = Cache(app)

# In-memory result store with thread-safety
_lock          = threading.Lock()
RESULT_STORE   = {}       # rid → {"csv": str, "json": dict, "ts": datetime}
MAX_STORED     = 50


# ─────────────────────────── Helpers ──────────────────────────────────
def read_params():
    f = request.form
    k = f.get("k", "auto")
    return dict(
        k           = None if k in ("", "auto") else int(k),
        min_support = float(f.get("min_support", 0.05)),
        min_conf    = float(f.get("min_conf",    0.5)),
        min_lift    = float(f.get("min_lift",    1.1)),
        algorithm   = f.get("algorithm", "kmeans"),
    )


def store_result(rfm, result):
    rid = uuid.uuid4().hex
    csv_text  = rfm.reset_index().to_csv(index=False)
    with _lock:
        RESULT_STORE[rid] = {
            "csv":  csv_text,
            "json": result,
            "ts":   datetime.utcnow(),
        }
        # Evict oldest entries
        while len(RESULT_STORE) > MAX_STORED:
            RESULT_STORE.pop(next(iter(RESULT_STORE)))
    return rid


def respond(df_raw):
    params = read_params()
    result, rfm = engine.run_pipeline(df_raw, **params)
    rid = store_result(rfm, result)
    result["download_id"] = rid
    return jsonify(result)


# ─────────────────────────── Routes ───────────────────────────────────
@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify(status="ok", stored_results=len(RESULT_STORE),
                   timestamp=datetime.utcnow().isoformat())


@app.post("/api/analyze")
def analyze():
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify(error="Please choose a CSV or Excel file."), 400
    try:
        return respond(engine.load_table(file, file.filename))
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        return jsonify(error=f"Processing error: {e}"), 500


@app.post("/api/demo")
def demo():
    try:
        return respond(generate())
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        return jsonify(error=f"Demo error: {e}"), 500


# ── Sample download
@app.get("/api/sample.csv")
def sample_csv():
    buf = io.BytesIO(generate().to_csv(index=False).encode())
    return send_file(buf, mimetype="text/csv", as_attachment=True,
                     download_name="sample_transactions.csv")


# ── Download results as CSV
@app.get("/api/download/<rid>")
def download_csv(rid):
    with _lock:
        entry = RESULT_STORE.get(rid)
    if entry is None:
        return "Result expired. Run analysis again.", 404
    buf = io.BytesIO(entry["csv"].encode())
    return send_file(buf, mimetype="text/csv", as_attachment=True,
                     download_name="customer_segments.csv")


# ── Download results as JSON
@app.get("/api/download/<rid>/json")
def download_json(rid):
    with _lock:
        entry = RESULT_STORE.get(rid)
    if entry is None:
        return "Result expired.", 404
    buf = io.BytesIO(json.dumps(entry["json"], indent=2).encode())
    return send_file(buf, mimetype="application/json", as_attachment=True,
                     download_name="segmentation_results.json")


# ── Download Excel (segments + summary sheet)
@app.get("/api/download/<rid>/excel")
def download_excel(rid):
    with _lock:
        entry = RESULT_STORE.get(rid)
    if entry is None:
        return "Result expired.", 404
    import pandas as pd
    buf = io.BytesIO()
    df_seg  = pd.read_csv(io.StringIO(entry["csv"]))
    df_prof = pd.DataFrame(entry["json"]["profiles"])
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        df_seg.to_excel(xl,  sheet_name="Customer Segments", index=False)
        df_prof.to_excel(xl, sheet_name="Segment Profiles",  index=False)
    buf.seek(0)
    return send_file(buf,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name="customer_segments.xlsx")


# ── Segment comparison (compare two run results)
@app.get("/api/compare/<rid1>/<rid2>")
def compare(rid1, rid2):
    with _lock:
        e1 = RESULT_STORE.get(rid1)
        e2 = RESULT_STORE.get(rid2)
    if not e1 or not e2:
        return jsonify(error="One or both result IDs not found or expired."), 404
    return jsonify({
        "run1_summary": e1["json"]["summary"],
        "run2_summary": e2["json"]["summary"],
        "run1_profiles": e1["json"]["profiles"],
        "run2_profiles": e2["json"]["profiles"],
    })


# ── Customer Lookup by ID
@app.get("/api/lookup/<rid>/<customer_id>")
def customer_lookup(rid, customer_id):
    with _lock:
        entry = RESULT_STORE.get(rid)
    if entry is None:
        return jsonify(error="Result expired. Please run the analysis again."), 404

    import pandas as pd, io
    df_seg  = pd.read_csv(io.StringIO(entry["csv"]))
    profiles = entry["json"]["profiles"]
    rules    = entry["json"]["rules"]

    # Find the customer
    row = df_seg[df_seg["CustomerID"].astype(str) == str(customer_id)]
    if row.empty:
        return jsonify(error=f"Customer '{customer_id}' not found in this dataset."), 404

    r = row.iloc[0]
    segment  = str(r.get("Segment", "Unknown"))

    # Find matching profile
    profile = next((p for p in profiles if p["segment"] == segment), {})

    # Churn badge
    churn = float(r.get("ChurnRisk", 0))
    if churn >= 70:
        churn_label = "High Risk 🔴"
    elif churn >= 40:
        churn_label = "Medium Risk 🟡"
    else:
        churn_label = "Low Risk 🟢"

    # Anomaly flag
    anomaly = int(r.get("Anomaly", 1))
    anomaly_label = "⚠️ Flagged as anomaly" if anomaly == -1 else "✅ Normal"

    # Top rules for this segment
    seg_rules = rules.get(segment, [])
    top_rule  = seg_rules[0]["rule"] + f" (lift {seg_rules[0]['lift']})" if seg_rules else "No rules found"

    result = {
        "customer_id":   str(customer_id),
        "segment":       segment,
        "color":         profile.get("color", "#13a89e"),
        "action":        profile.get("action", ""),
        "recency":       float(r.get("Recency",    0)),
        "frequency":     float(r.get("Frequency",  0)),
        "monetary":      round(float(r.get("Monetary",   0)), 2),
        "avg_basket":    round(float(r.get("AvgBasket",  0)), 2),
        "num_products":  int(r.get("NumProducts", 0)),
        "tenure":        float(r.get("Tenure",    0)),
        "velocity":      round(float(r.get("Velocity",   0)), 3),
        "clv_12m":       round(float(r.get("CLV_12M",   0)), 2),
        "churn_risk":    round(churn, 1),
        "churn_label":   churn_label,
        "anomaly":       anomaly_label,
        "top_rule":      top_rule,
        "segment_rank":  profiles.index(profile) + 1 if profile in profiles else "—",
        "total_segments": len(profiles),
        "revenue_percentile": round(
            float((df_seg["Monetary"] <= r.get("Monetary", 0)).mean() * 100), 1
        ),
    }
    return jsonify(result)


# ── Search customer IDs (autocomplete helper)
@app.get("/api/customers/<rid>")
def list_customers(rid):
    with _lock:
        entry = RESULT_STORE.get(rid)
    if entry is None:
        return jsonify(error="Result expired."), 404
    import pandas as pd, io
    df_seg = pd.read_csv(io.StringIO(entry["csv"]))
    ids = df_seg["CustomerID"].astype(str).dropna().unique().tolist()
    return jsonify({"customers": sorted(ids)})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(debug=debug, host="0.0.0.0", port=port)
