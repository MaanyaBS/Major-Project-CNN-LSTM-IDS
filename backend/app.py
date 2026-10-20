import atexit
import io
import os
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

BACKEND_DIR = Path(__file__).resolve().parent
MODEL_DIR = BACKEND_DIR.parent / "model"
for _p in (str(BACKEND_DIR), str(MODEL_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from model_service import service, FEATURE_COLS, SEQ_LEN
from shap_service import shap_service
from cert_in_mapping import DASHBOARD_CATEGORIES
import prevention_executor as pe
from flow_features import flows_from_pcap
from prevention_runtime import (
    configure_from_env,
    runtime_info,
    find_source_ip_column,
    source_ip_for_window,
    execute_for_result,
    revoke,
    active_rules,
    prevention_engine_ready,
)

MAX_CSV_WINDOWS = 2000

# Largest capture accepted by /api/predict_pcap. Configurable because a scan
# capture can grow quickly, but a default cap still exists so one upload
# cannot fill the server's disk: the file is streamed to disk in chunks and
# rejected as soon as it passes the limit, not after it has all arrived.
try:
    MAX_PCAP_MB = int(os.environ.get("IDS_MAX_PCAP_MB", "200"))
    if MAX_PCAP_MB <= 0:
        raise ValueError
except ValueError:
    MAX_PCAP_MB = 200
MAX_PCAP_BYTES = MAX_PCAP_MB * 1024 * 1024

PCAP_EXTENSIONS = (".pcap", ".pcapng")
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


def analyze_frame(df):
    """
    Flow DataFrame -> the body of /api/predict_csv.

    Shared by the CSV and the capture endpoints on purpose: uploading a
    capture and uploading the flow CSV that `python model/flow_features.py
    <capture> -o x.csv` produces from it must give identical results, and the
    only way to guarantee that is for both to run the exact same code.

    Raises ValueError for anything that is the caller's fault (a 400);
    anything else propagates and is reported as a 500 by the caller.
    """
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Input is missing required columns: {missing}")

    original_rows = len(df)
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURE_COLS)
    rows_dropped = original_rows - len(df)
    if len(df) < SEQ_LEN:
        raise ValueError(
            f"Need at least {SEQ_LEN} valid rows after cleaning, got {len(df)} "
            "(one prediction needs a window of 10 flows)"
        )

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

    probs = service.predict_matrix(X_raw)

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

    return {
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


@app.post("/api/predict_csv")
def predict_csv():
    if "file" not in request.files:
        return jsonify({"error": "Attach a CSV file in the 'file' field"}), 400
    file = request.files["file"]
    try:
        df = pd.read_csv(io.BytesIO(file.read()))
    except Exception as e:
        return jsonify({"error": f"Could not parse CSV: {e}"}), 400

    try:
        return jsonify(analyze_frame(df))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Inference failed: {e}"}), 500


@app.post("/api/predict_pcap")
def predict_pcap():
    """
    Wireshark .pcap/.pcapng -> the same JSON as /api/predict_csv, plus
    "flows": the number of flows the capture was converted to.

    The capture is converted with Person B's packet -> flow -> 20-feature
    converter (model/flow_features.py), so a capture and the CSV that
    converter writes from it (`python model/flow_features.py cap.pcap -o
    x.csv`) run through one code path, analyze_frame(), and cannot disagree.
    """
    if "file" not in request.files:
        return jsonify({"error": "Attach a capture file in the 'file' field"}), 400
    file = request.files["file"]
    filename = file.filename or ""
    if not filename.lower().endswith(PCAP_EXTENSIONS):
        return jsonify(
            {"error": "Only .pcap and .pcapng captures are accepted here (CSVs go to /api/predict_csv)"}
        ), 400

    # Streamed to a temp file in chunks, so an oversized upload is refused
    # while it arrives instead of after it has all been read into memory.
    suffix = ".pcapng" if filename.lower().endswith(".pcapng") else ".pcap"
    tmp_path = None
    try:
        total = 0
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            while True:
                chunk = file.stream.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_PCAP_BYTES:
                    return jsonify(
                        {
                            "error": (
                                f"Capture exceeds the {MAX_PCAP_MB} MB upload limit. "
                                f"Trim it (e.g. in Wireshark: Edit -> Packet Range) or raise "
                                "IDS_MAX_PCAP_MB and restart the backend."
                            )
                        }
                    ), 413
                tmp.write(chunk)

        if total == 0:
            return jsonify({"error": "The uploaded capture is empty"}), 400

        try:
            df = flows_from_pcap(tmp_path)
        except ImportError as e:
            return jsonify(
                {"error": f"Reading captures needs scapy - pip install 'scapy>=2.6' ({e})"}
            ), 500
        except Exception as e:
            return jsonify({"error": f"Could not read capture: {e}"}), 400

        if len(df) == 0:
            return jsonify(
                {
                    "error": (
                        "No TCP/UDP flows found in this capture - the detector works on "
                        "IPv4 TCP/UDP flows, so an empty or non-IP capture cannot be analysed."
                    )
                }
            ), 400

        body = analyze_frame(df)
        body["flows"] = len(df)
        return jsonify(body)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Inference failed: {e}"}), 500
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@app.post("/api/explain_window")
def explain_window():
    # A malformed body must not silently fall back to window 0: the whole
    # point of this endpoint is to explain ONE specific window, so quietly
    # returning a confident explanation of the wrong window is worse than an
    # error. get_json(silent=True) returns None on unparseable JSON, which used
    # to make a bad request look like a valid request for window 0.
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Request body must be valid JSON"}), 400
    if "window" not in payload:
        return jsonify({"error": "Request body must include 'window'"}), 400

    window = payload["window"]
    rows = _last_upload.get("rows")
    if rows is None:
        return jsonify({"error": "Upload a CSV via /api/predict_csv first"}), 409
    if not isinstance(window, int) or isinstance(window, bool) or window < 0 or window >= _last_upload["count"]:
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
    one. Deliberately NOT gated on the kill switch: undoing must stay possible
    after a restart without the env var. The engine's revoke_action() does its
    own checks (TEST-NET scope + admin rights), never raises, and its verdict
    is surfaced as-is - a refusal is a 400, never a silent success.
    """
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    target_ip = payload.get("target_ip")

    if not isinstance(action, str) or not action:
        return jsonify({"error": "'action' is required"}), 400
    if not isinstance(target_ip, str) or not target_ip:
        return jsonify({"error": "'target_ip' is required"}), 400

    outcome = revoke(action, target_ip)
    if not outcome.get("revoked"):
        return jsonify(outcome), 400
    return jsonify(outcome)


@app.get("/api/prevention/active")
def prevention_active():
    """
    Firewall rules currently in force - what the dashboard's "Blocked devices"
    panel lists, refreshed on every live poll.

    Deliberately read-only: it never creates or removes anything, so it needs
    no kill switch. Revoking stays a separate, deliberate POST to
    /api/prevention/revoke.
    """
    # Always readable: active_rules() falls back to the engine's own registry
    # while pe.active_rules() is still pending, and `engine_ready` says which
    # of the two the list came from, rather than the panel implying the engine
    # reported rules it has not.
    try:
        return jsonify({"rules": active_rules(), "engine_ready": prevention_engine_ready()})
    except Exception as e:
        return jsonify({"error": f"Could not list active firewall rules: {e}"}), 500


# ============================================================
# Live capture
# ============================================================
# The capture engine (backend/live_capture.py) is Person B's and lands
# separately. Until it does, _StubLiveCapture answers the same four endpoints
# with deterministic demo data, so the Live capture UI can be built and shown
# against the exact contract instead of a mock server.


class _StubLiveCapture:
    """
    Stand-in for backend/live_capture.py: same interface, fake data.

    Two things it deliberately does NOT do:

    - It never touches the firewall. Fabricated detections must not create
      real rules, so its results carry an explicit "nothing was attempted"
      execution record instead of going through execute_for_result().
    - It never drops windows: a stub that reports dropped data would make the
      UI look broken for no reason. queue_depth still grows if polling lags,
      which is the part of the contract worth exercising.
    """

    INTERFACES = [
        {"name": "Wi-Fi", "description": "Stub adapter - capture engine not installed yet", "ip": "192.168.1.42"},
        {"name": "Ethernet", "description": "Stub adapter - capture engine not installed yet", "ip": "192.168.1.7"},
        {"name": "Loopback", "description": "Stub adapter - capture engine not installed yet", "ip": "127.0.0.1"},
    ]
    WINDOW_SECONDS = 2.0          # one fake window every 2 s of capture time
    FLOWS_PER_WINDOW = 10         # one model window
    PACKETS_PER_FLOW = 7
    # Mostly benign with a scan and a flood on a fixed cycle, so every state
    # of the live UI (clear / attack / held for review) is reachable.
    PATTERN = ["BENIGN", "BENIGN", "PortScan", "BENIGN", "BENIGN", "DDoS", "BENIGN", "Bot", "BENIGN", "BENIGN"]

    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._interface = None
        self._started = 0.0

    def list_interfaces(self):
        return [dict(i) for i in self.INTERFACES]

    def start(self, interface):
        with self._lock:
            self._running = True
            self._interface = interface
            self._started = time.monotonic()
        return {"running": True, "interface": interface}

    def stop(self):
        with self._lock:
            self._running = False
            self._interface = None
        return {"running": False}

    def _result(self, window):
        if not service.int_to_label:
            return None  # model not loaded yet - report nothing rather than a fake class
        name_to_int = {v: k for k, v in service.int_to_label.items()}
        n = max(service.int_to_label) + 1
        chosen = name_to_int.get(self.PATTERN[window % len(self.PATTERN)], 0)
        probs = np.full(n, (1.0 - 0.93) / max(1, n - 1), dtype="float64")
        probs[chosen] = 0.93

        result = service._build_result(probs)
        # RFC 5737 TEST-NET-1: inside the prevention engine's demo scope, so
        # the target shown in the UI is shaped like a real one.
        source_ip = f"192.0.2.{10 + (window % 20)}"
        result["window"] = window
        result["source_ip"] = source_ip
        result["time"] = datetime.fromtimestamp(
            self._started + window * self.WINDOW_SECONDS, timezone.utc
        ).isoformat()
        if result["prevention"]["status"] == "auto_action":
            result["execution"] = {
                "executed": False,
                "action": result["prevention"]["action"],
                "target_ip": source_ip,
                "reason": (
                    "Stub capture (backend/live_capture.py not installed yet): these "
                    "detections are demo data, so no firewall action was attempted."
                ),
            }
        return result

    def poll(self, after, limit=50):
        with self._lock:
            running, started = self._running, self._started

        produced = int((time.monotonic() - started) / self.WINDOW_SECONDS) if running else 0
        # Windows are numbered from 0 and `after` is exclusive: this call
        # hands back (after, produced], at most `limit` of them.
        first = max(after + 1, 0)
        last = min(produced, first + limit)
        results = [r for w in range(first, last) if (r := self._result(w)) is not None]

        return {
            "running": running,
            "packets": produced * self.FLOWS_PER_WINDOW * self.PACKETS_PER_FLOW,
            "flows": produced * self.FLOWS_PER_WINDOW,
            "windows": produced,
            "results": results,
            "skipped": 0,
            "queue_depth": max(0, produced - last),
            "dropped": 0,
        }


try:
    import live_capture as _live_engine
except Exception as _live_import_error:  # ImportError while it is missing; a half-built engine must not kill startup
    _live_engine = None
    _LIVE_IMPORT_ERROR = repr(_live_import_error)
else:
    _LIVE_IMPORT_ERROR = None

_live_stub = None if _live_engine is not None else _StubLiveCapture()
_live_state = {"started": False}


def _live():
    """The capture engine: Person B's module once it lands, the stub until then."""
    return _live_engine if _live_engine is not None else _live_stub


def _live_is_stub():
    return _live_engine is None


def _poll_engine(after, limit):
    """poll(after, limit) with a fallback for an engine that only takes `after`."""
    try:
        return _live().poll(after, limit)
    except TypeError:
        return _live().poll(after)  # pragma: no cover - defensive


@app.get("/api/live/interfaces")
def live_interfaces():
    try:
        interfaces = _live().list_interfaces() or []
    except Exception as e:
        return jsonify({"error": f"Could not list capture interfaces: {e}"}), 500
    body = {"interfaces": interfaces, "stub": _live_is_stub()}
    if _live_is_stub():
        body["note"] = (
            "Capture engine (backend/live_capture.py) not installed yet - these are "
            "stub interfaces and the feed below is demo data."
        )
        if _LIVE_IMPORT_ERROR:
            body["import_error"] = _LIVE_IMPORT_ERROR
    return jsonify(body)


@app.post("/api/live/start")
def live_start():
    payload = request.get_json(silent=True) or {}
    interface = payload.get("interface")
    if not isinstance(interface, str) or not interface.strip():
        return jsonify({"error": "'interface' is required"}), 400
    try:
        info = _live().start(interface.strip()) or {}
    except Exception as e:
        return jsonify({"error": f"Could not start capture on '{interface}': {e}"}), 500
    _live_state["started"] = True
    return jsonify({**info, "stub": _live_is_stub()})


@app.get("/api/live/poll")
def live_poll():
    """
    Results produced since `after` (the last window number the page has), at
    most `limit` per call (capped at 50) so a busy scan cannot freeze the page:
    the UI asks again on its next 1 s tick and picks up where it left off.
    """
    try:
        after = _query_int("after", -1, minimum=-1)   # -1 = "nothing yet", so window 0 is included
        limit = _query_int("limit", 50, minimum=1)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    limit = min(limit, 50)

    try:
        data = _poll_engine(after, limit) or {}
    except Exception as e:
        return jsonify({"error": f"Live poll failed: {e}"}), 500

    # The capture engine (backend/live_capture.py) runs prevention itself and
    # attaches "execution" to each result; the stub does the same for its
    # fabricated results. Never call the firewall from poll() - that would
    # execute the same recommendation a second time.
    data["results"] = data.get("results") or []
    # Defaults keep older/newer engines interchangeable at the client.
    data.setdefault("skipped", 0)
    data.setdefault("queue_depth", 0)
    data.setdefault("dropped", 0)
    data.setdefault("error", None)
    data["stub"] = _live_is_stub()
    return jsonify(data)


@app.post("/api/live/stop")
def live_stop():
    try:
        info = _live().stop() or {"running": False}
    except Exception as e:
        return jsonify({"error": f"Could not stop capture: {e}"}), 500
    _live_state["started"] = False
    return jsonify({**info, "stub": _live_is_stub()})


def _query_int(name, default, minimum=None, maximum=None):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"'{name}' must be an integer, got '{raw}'")
    if minimum is not None and value < minimum:
        raise ValueError(f"'{name}' must be >= {minimum}, got {value}")
    if maximum is not None and value > maximum:
        raise ValueError(f"'{name}' must be <= {maximum}, got {value}")
    return value


def _shutdown_live_capture():
    """Release the interface when the server exits, so the capture stops with it."""
    if not _live_state.get("started"):
        return
    try:
        _live().stop()
    except Exception:
        pass  # nothing useful to do while shutting down
    _live_state["started"] = False


atexit.register(_shutdown_live_capture)


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
