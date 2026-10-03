"""
Wiring between the Flask backend and Person B's prevention execution engine
(model/prevention_executor.py).

This module owns three things, so that app.py stays a routing layer:

1. Turning real execution on/off from an environment variable. Real OS-level
   actions are opt-in and OFF by default. There is deliberately no HTTP way to
   flip this switch: an inbound request must never be able to authorise itself
   to touch the machine's firewall.
2. Reading an optional Source IP column out of an uploaded CSV.
3. Turning a *recommendation* into an *attempted execution*, keeping the two
   as separate fields so the API never claims an action happened when only a
   recommendation was made.

Contract reference: model/PREVENTION_EXECUTION_INTERFACE.md, Section 6.
"""

import os
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

import prevention_executor as pe

# Environment variable that arms real execution. Anything not explicitly
# truthy leaves the engine disabled, which is the safe default.
ENV_VAR = "IDS_PREVENTION_EXECUTION_ENABLED"
_TRUTHY = {"1", "true", "yes", "on"}

# Column names accepted as the prevention target, compared after
# normalisation (lower-cased, separators collapsed to single spaces).
# Listed most-specific first: if a CSV somehow has two of these, the earliest
# match here wins and the API reports which column was used.
SOURCE_IP_COLUMNS = (
    "source ip",
    "source ip address",
    "src ip",
    "src ip address",
    "sourceip",
    "srcip",
    "source address",
    "src address",
    "client ip",
    "ip address",
    "source",
    "src",
    "ip",
)

# Outcome recorded when the policy recommends an action but there is no IP to
# act on. Not an error: the model never sees source IPs, so this is the normal
# case for any upload without a Source IP column.
NO_TARGET_REASON = "No Source IP available for this window - recommendation only, nothing to act on."


def _normalise(name):
    return " ".join(str(name).strip().lower().replace("_", " ").replace("-", " ").split())


def _truthy(value):
    return str(value).strip().lower() in _TRUTHY


# pandas turns a blank CSV cell into NaN, which stringifies to the literal
# "nan". Passing that to the engine would be refused as malformed, but it would
# also produce a confusing reason and a pointless log entry, so blanks and NaN
# are normalised to None here and reported as "no target".
_MISSING = {"", "nan", "none", "null", "na", "n/a", "-", "<na>"}


def _clean_ip(value):
    if value is None:
        return None
    text = str(value).strip()
    return None if text.lower() in _MISSING else text


def configure_from_env():
    """Arm or disarm real execution from the environment. Call once in initialize()."""
    raw = os.environ.get(ENV_VAR)
    pe.PREVENTION_EXECUTION_ENABLED = _truthy(raw) if raw is not None else False
    return pe.PREVENTION_EXECUTION_ENABLED


def is_enabled():
    return bool(pe.PREVENTION_EXECUTION_ENABLED)


def runtime_info():
    """Describes the current execution posture, for /api/health and the UI."""
    return {
        "execution_enabled": is_enabled(),
        "env_var": ENV_VAR,
        "allowed_demo_ranges": [str(net) for net in pe.ALLOWED_DEMO_RANGES],
        "executable_actions": sorted(pe.ACTION_DURATIONS),
        # Documented honestly: rate_limit is a temporary full block, not QoS.
        "simulated_only_actions": ["sanitize_input", "terminate_session", "alert_only", "no_action"],
    }


def find_source_ip_column(df):
    """
    Returns (column_name, normalised_values) for the Source IP column, or
    (None, None) if the upload has none.

    Values are returned as a plain list of strings with blanks normalised to
    None, so a partially-missing column degrades to "some windows have no
    target" instead of raising.
    """
    lookup = {}
    for col in df.columns:
        lookup.setdefault(_normalise(col), col)

    for candidate in SOURCE_IP_COLUMNS:
        if candidate in lookup:
            col = lookup[candidate]
            return col, [_clean_ip(v) for v in df[col].tolist()]

    return None, None


def source_ip_for_window(values, window_index):
    """
    The prevention target for one window.

    predict_matrix() cuts a CSV into non-overlapping 10-row blocks, so a window
    maps to rows [window_index*10, window_index*10+10). The target is the Source
    IP of the window's first flow row - the model's window is ordered, so the
    first flow is the one that opened the sequence.
    """
    if values is None:
        return None
    start = window_index * 10
    if start >= len(values):
        return None
    return values[start]


def _attempt(action, target_ip, predicted_class, confidence):
    """Single funnel to the engine. execute_action never raises."""
    return pe.execute_action(
        action=action,
        target_ip=target_ip,
        predicted_class=predicted_class,
        confidence=float(confidence),
    )


def execute_for_result(result, source_ip):
    """
    Attempt the real action behind a prediction's prevention recommendation.

    Returns the engine's own dict (as-is) when an execution was attempted, or
    None when there was nothing to attempt. Callers attach the result under a
    separate "execution" key precisely so that
        prevention -> what the policy recommends
        execution  -> what actually happened to this machine
    can never be read as the same claim.
    """
    prevention = result.get("prevention") or {}
    if prevention.get("status") != "auto_action":
        return None

    action = prevention.get("action")
    if not action:
        return None

    if source_ip is None:
        return {
            "executed": False,
            "reason": NO_TARGET_REASON,
            "action": action,
            "target_ip": None,
        }

    outcome = _attempt(action, source_ip, result.get("predicted_class"), result.get("confidence", 0.0))
    # Echo the target back so the dashboard can show what was acted on without
    # having to correlate against the uploaded CSV.
    return {**outcome, "action": action, "target_ip": source_ip}


def revoke(action, target_ip):
    """Lift a persistent (non-expiring) action after human review."""
    pe.revoke_action(action=action, target_ip=target_ip)
    return {"revoked": True, "action": action, "target_ip": target_ip}