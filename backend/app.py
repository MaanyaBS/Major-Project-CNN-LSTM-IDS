import io

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

from model_service import service, FEATURE_COLS, SEQ_LEN
from shap_service import shap_service
from cert_in_mapping import DASHBOARD_CATEGORIES

MAX_CSV_WINDOWS = 2000
MODEL_METRICS = {
    "accuracy": 0.9842,
    "weighted_f1": 0.9864,
    "macro_f1": 0.5857,
    "version": "cnn_lstm_best_v2",
}

_last_upload = {"rows": None, "count": 0}

app = Flask(__name__)
CORS(app)


@app.get("/api/health")
def health():
    return jsonify(
        {
            "status": "ok" if service.loaded else "loading",
            "shap_ready": shap_service.ready,
            "model": MODEL_METRICS,
        }
    )


@app.get("/api/meta")
def meta():
    return jsonify(
        {
            "feature_cols": FEATURE_COLS,
            "sequence_length": SEQ_LEN,
            "dashboard_categories": DASHBOARD_CATEGORIES,
            "label_mapping_int_to_name": service.int_to_label,
            "model": MODEL_METRICS,
        }
    )


def _extract_sequences(payload):
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object")
    if "sequences" in payload:
        sequences = payload["sequences"]
        if not isinstance(sequences, list) or not sequences:
            raise ValueError("'sequences' must be a non-empty list of 10-row sequences")
        return sequences, False
    if "flows" in payload:
        flows = payload["flows"]
        if not isinstance(flows, list) or not flows:
            raise ValueError("'flows' must be a non-empty list of flow rows")
        return [flows], True
    raise ValueError("Provide either 'flows' (one sequence) or 'sequences' (batch)")


@app.post("/api/predict")
def predict():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    try:
        sequences, single = _extract_sequences(payload)
        results = service.predict_batch(sequences)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Inference failed: {e}"}), 500

    body = {"results": results}
    attacks = sum(1 for r in results if r["predicted_class"] != "BENIGN")
    body["summary"] = {
        "total": len(results),
        "attacks": attacks,
        "normal": len(results) - attacks,
        "attack_rate": attacks / len(results) if results else 0.0,
    }
    if single:
        body["result"] = results[0]
    return jsonify(body)


@app.post("/api/explain")
def explain():
    payload = request.get_json(silent=True)
    if payload is None or "flows" not in payload:
        return jsonify({"error": "Provide 'flows': a list of exactly 10 flow rows"}), 400
    try:
        result = shap_service.explain(payload["flows"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Explanation failed: {e}"}), 500
    return jsonify(result)


@app.post("/api/predict_csv")
def predict_csv():
    if "file" not in request.files:
        return jsonify({"error": "Attach a CSV file in the 'file' field"}), 400
    file = request.files["file"]
    try:
        df = pd.read_csv(io.BytesIO(file.read()))
    except Exception as e:
        return jsonify({"error": f"Could not parse CSV: {e}"}), 400

    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        return jsonify({"error": f"CSV is missing required columns: {missing}"}), 400

    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURE_COLS)
    if len(df) < SEQ_LEN:
        return jsonify({"error": f"Need at least {SEQ_LEN} valid rows after cleaning"}), 400

    X_raw = df[FEATURE_COLS].to_numpy(dtype="float32")
    max_rows = MAX_CSV_WINDOWS * SEQ_LEN
    truncated = False
    if len(X_raw) > max_rows:
        X_raw = X_raw[:max_rows]
        truncated = True

    n_windows = len(X_raw) // SEQ_LEN
    _last_upload["rows"] = X_raw[: n_windows * SEQ_LEN]
    _last_upload["count"] = n_windows

    try:
        probs = service.predict_matrix(X_raw)
    except Exception as e:
        return jsonify({"error": f"Inference failed: {e}"}), 500

    results = [service._build_result(p) for p in probs]
    attacks = sum(1 for r in results if r["predicted_class"] != "BENIGN")

    class_counts = {}
    for r in results:
        class_counts[r["predicted_class"]] = class_counts.get(r["predicted_class"], 0) + 1

    timeline = []
    step = max(1, len(results) // 20)
    for i in range(0, len(results), step):
        chunk = results[i : i + step]
        threats = sum(1 for r in chunk if r["predicted_class"] != "BENIGN")
        timeline.append({"window": i, "threats": threats, "normal": len(chunk) - threats})

    held = sum(1 for r in results if r["prevention"]["status"] == "held_for_review")
    auto = sum(1 for r in results if r["prevention"]["status"] == "auto_action")

    return jsonify(
        {
            "summary": {
                "total_sequences": len(results),
                "attacks": attacks,
                "normal": len(results) - attacks,
                "attack_rate": attacks / len(results),
                "class_counts": class_counts,
                "auto_actions": auto,
                "held_for_review": held,
                "truncated": truncated,
                "rows_dropped_invalid": int(request.content_length and 0) or None,
            },
            "timeline": timeline,
            "results": results[:200],
        }
    )


@app.post("/api/explain_window")
def explain_window():
    payload = request.get_json(silent=True) or {}
    window = payload.get("window", 0)
    rows = _last_upload.get("rows")
    if rows is None:
        return jsonify({"error": "Upload a CSV via /api/predict_csv first"}), 409
    if not isinstance(window, int) or window < 0 or window >= _last_upload["count"]:
        return jsonify(
            {"error": f"'window' must be an integer in [0, {_last_upload['count'] - 1}]"}
        ), 400
    seq = rows[window * SEQ_LEN : (window + 1) * SEQ_LEN]
    try:
        result = shap_service.explain_matrix(seq)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Explanation failed: {e}"}), 500
    result["window"] = window
    return jsonify(result)


def initialize():
    service.load()
    shap_service.init()


if __name__ == "__main__":
    initialize()
    app.run(host="127.0.0.1", port=5000, debug=False)
