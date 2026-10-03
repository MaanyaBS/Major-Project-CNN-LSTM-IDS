import io
import os

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

from model_service import service, FEATURE_COLS, SEQ_LEN
from shap_service import shap_service
from cert_in_mapping import DASHBOARD_CATEGORIES
import prevention_executor as pe
from prevention_runtime import (
    configure_from_env,
    runtime_info,
    find_source_ip_column,
    source_ip_for_window,
    execute_for_result,
    revoke,
)

MAX_CSV_WINDOWS = 2000
MODEL_METRICS = {
    "accuracy": 0.9842,
    "weighted_f1": 0.9864,
    "macro_f1": 0.5857,
    "version": "cnn_lstm_best_v2",
}

_last_upload = {"rows": None, "count": 0, "source_ips": None, "source_ip_column": None}
_stream = {"rows": None, "count": 0, "cursor": 0, "source_ips": None, "source_ip_column": None}

app = Flask(__name__)
CORS(app)


def _with_execution(result, source_ip):
    """
    Attach the real-execution outcome to a prediction, if one was attempted.

    Kept separate from the recommendation on purpose: `prevention` is what the
    policy says should happen, `execution` is what happened to this machine.
    A recommendation with no execution must never render as an executed action.
    """
    outcome = execute_for_result(result, source_ip)
    if outcome is not None:
        result["execution"] = outcome
    return result


def _read_source_ips(df):
    """Optional Source IP column -> (column_name, per_row_values)."""
    return find_source_ip_column(df)


@app.get("/api/health")
def health():
    return jsonify(
        {
            "status": "ok" if service.loaded else "loading",
            "shap_ready": shap_service.ready,
            "shap_background": shap_service.background_info(),
            "model": MODEL_METRICS,
            "prevention": runtime_info(),
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

    original_rows = len(df)
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURE_COLS)
    rows_dropped = original_rows - len(df)
    if len(df) < SEQ_LEN:
        return jsonify({"error": f"Need at least {SEQ_LEN} valid rows after cleaning"}), 400

    # Optional Source IP column. Read from the cleaned frame so its row indices
    # line up exactly with the rows that survive into windows.
    source_ip_column, source_ips = _read_source_ips(df)

    X_raw = df[FEATURE_COLS].to_numpy(dtype="float32")
    max_rows = MAX_CSV_WINDOWS * SEQ_LEN
    truncated = False
    if len(X_raw) > max_rows:
        X_raw = X_raw[:max_rows]
        truncated = True

    n_windows = len(X_raw) // SEQ_LEN
    _last_upload["rows"] = X_raw[: n_windows * SEQ_LEN]
    _last_upload["count"] = n_windows
    _last_upload["source_ips"] = source_ips
    _last_upload["source_ip_column"] = source_ip_column

    try:
        probs = service.predict_matrix(X_raw)
    except Exception as e:
        return jsonify({"error": f"Inference failed: {e}"}), 500

    results = [
        _with_execution(service._build_result(p), source_ip_for_window(source_ips, i))
        for i, p in enumerate(probs)
    ]
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
    executed = sum(1 for r in results if (r.get("execution") or {}).get("executed"))

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
                "rows_dropped_invalid": rows_dropped,
                # Counted separately from auto_actions on purpose: how many
                # actions were recommended is not how many were carried out.
                "actions_executed": executed,
            },
            "timeline": timeline,
            "results": results[:200],
            "prevention": {
                **runtime_info(),
                "source_ip_column": source_ip_column,
                "actions_executed": executed,
                "auto_actions_recommended": auto,
            },
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


@app.post("/api/stream/load")
def stream_load():
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

    source_ip_column, source_ips = _read_source_ips(df)

    X_raw = df[FEATURE_COLS].to_numpy(dtype="float32")
    n_windows = len(X_raw) // SEQ_LEN
    _stream["rows"] = X_raw[: n_windows * SEQ_LEN]
    _stream["count"] = n_windows
    _stream["cursor"] = 0
    _stream["source_ips"] = source_ips
    _stream["source_ip_column"] = source_ip_column
    return jsonify(
        {
            "total_windows": n_windows,
            "sequence_length": SEQ_LEN,
            "prevention": {**runtime_info(), "source_ip_column": source_ip_column},
        }
    )


@app.get("/api/stream/next")
def stream_next():
    rows = _stream.get("rows")
    if rows is None:
        return jsonify({"error": "No stream loaded — POST the CSV to /api/stream/load first"}), 409

    cursor = _stream["cursor"]
    if cursor >= _stream["count"]:
        return jsonify({"done": True, "window": cursor, "total": _stream["count"]})

    seq = rows[cursor * SEQ_LEN : (cursor + 1) * SEQ_LEN]
    try:
        probs = service.predict_matrix(seq)
    except Exception as e:
        return jsonify({"error": f"Inference failed: {e}"}), 500

    source_ip = source_ip_for_window(_stream.get("source_ips"), cursor)
    result = _with_execution(service._build_result(probs[0]), source_ip)
    result["window"] = cursor
    _stream["cursor"] += 1
    return jsonify(
        {
            "done": False,
            "total": _stream["count"],
            "result": result,
        }
    )


@app.post("/api/prevention/revoke")
def prevention_revoke():
    """
    Lift a persistent action (block_ip / isolate_host) after human review.

    Not in the original integration list, but block_ip and isolate_host stay
    applied until explicitly revoked, so the demo needs a supported way to undo
    one. Scoped by the engine's own safety boundary: revocation re-checks
    nothing, so it is deliberately restricted to the RFC 5737 demo ranges.
    """
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    target_ip = payload.get("target_ip")

    if not isinstance(action, str) or not action:
        return jsonify({"error": "'action' is required"}), 400
    if not isinstance(target_ip, str) or not target_ip:
        return jsonify({"error": "'target_ip' is required"}), 400

    try:
        pe.check_safe_to_execute(target_ip)
    except pe.ExecutionNotPermitted as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(revoke(action, target_ip))


def initialize():
    service.load()
    shap_service.init()

    # Real prevention execution is opt-in and off unless the environment
    # variable explicitly arms it. Must happen before the startup sweep, and
    # before any prediction can reach execute_action().
    enabled = configure_from_env()

    # Clean up temporary rules whose in-process expiry timer died with a
    # previous run of this backend. Safe to call repeatedly.
    swept = []
    try:
        swept = pe.sweep_expired_rules()
    except Exception as e:  # never block startup on cleanup
        app.logger.warning("Prevention rule sweep failed: %s", e)

    app.logger.info(
        "Prevention execution %s (env %s); swept %d expired rule(s)",
        "ENABLED" if enabled else "disabled",
        os.environ.get("IDS_PREVENTION_EXECUTION_ENABLED"),
        len(swept),
    )


if __name__ == "__main__":
    initialize()
    app.run(host="127.0.0.1", port=5000, debug=False)
