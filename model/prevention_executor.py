"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Prevention Execution Engine - Safety Boundary
Author  : Person B (Model Development)
==========================================================
Defines the safety boundary for REAL automated prevention actions.
This module does not execute anything by itself (that's the OS-level
execution engine built on top of it) - it defines the rules that
govern what execution is allowed to touch, checked independently of
and before any OS-level command is ever run.

Three independent layers, all of which must pass:

1. Global kill switch (PREVENTION_EXECUTION_ENABLED). Defaults to
   False - real execution is opt-in, never on by default.
2. Scope allow-list. The target IP must fall within one of the
   RFC 5737 "TEST-NET" ranges (192.0.2.0/24, 198.51.100.0/24,
   203.0.113.0/24) - ranges permanently reserved for documentation
   and testing, guaranteed to never route on the real internet. This
   means real execution can never reach a real destination, by
   construction, regardless of what a demo happens to feed it.
3. Explicit deny-list. Defense in depth: loopback and broadcast
   addresses are always refused even if a bug somehow got them past
   the allow-list.
"""

import ipaddress
import json
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

try:
    import ctypes
except ImportError:  # pragma: no cover - Windows-only module
    ctypes = None

# Layer 1: global kill switch. Must be flipped explicitly - never
# defaults to executing.
PREVENTION_EXECUTION_ENABLED = False

# Layer 2: only these ranges are ever eligible for real execution.
# RFC 5737 TEST-NET-1/2/3 - reserved for documentation/testing,
# never assigned to real hosts on the real internet.
ALLOWED_DEMO_RANGES = [
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
]

# Layer 3: always refused, regardless of the allow-list result.
NEVER_BLOCK = {
    "0.0.0.0",
    "127.0.0.1",
    "255.255.255.255",
}


class ExecutionNotPermitted(Exception):
    """Raised when a target/action fails the safety boundary check."""


def check_safe_to_execute(target_ip: str) -> None:
    """
    Raises ExecutionNotPermitted if target_ip is not safe to act on
    for real. Call this before any real OS-level action is attempted.
    Returns None (silently passes) only if the target is within the
    allowed demo scope and execution is enabled.
    """
    if not PREVENTION_EXECUTION_ENABLED:
        raise ExecutionNotPermitted(
            "Real execution is disabled (PREVENTION_EXECUTION_ENABLED=False). "
            "This is the default - flip it explicitly to enable real actions."
        )
    check_in_scope(target_ip)


def check_in_scope(target_ip: str) -> None:
    """
    Layers 2 and 3 without the kill switch: raises ExecutionNotPermitted
    unless target_ip is a single address inside the TEST-NET demo ranges.
    Used on its own only to UNDO an action (revoke_action), which must
    stay possible after the kill switch is turned off again.
    """
    if not isinstance(target_ip, str):
        raise ExecutionNotPermitted(f"Target must be an IP address string, got {type(target_ip).__name__}.")

    if target_ip in NEVER_BLOCK:
        raise ExecutionNotPermitted(f"{target_ip} is on the permanent deny-list.")

    try:
        addr = ipaddress.ip_address(target_ip)
    except ValueError:
        raise ExecutionNotPermitted(f"{target_ip} is not a valid IP address.")

    if not any(addr in net for net in ALLOWED_DEMO_RANGES):
        raise ExecutionNotPermitted(
            f"{target_ip} is outside the allowed demo scope "
            f"(RFC 5737 TEST-NET ranges only: 192.0.2.0/24, 198.51.100.0/24, "
            f"203.0.113.0/24). Refusing to act on real, routable addresses."
        )


# ==========================================================
# Execution engine - built on top of the safety boundary above.
# Nothing here runs an OS-level command without first passing
# check_safe_to_execute().
# ==========================================================

RULE_PREFIX = "IDS_DEMO_"

EXECUTION_LOG_PATH = Path(__file__).resolve().parent / "results" / "prevention_execution_log.jsonl"

# Which action types route through the real block/unblock primitive,
# and how long they persist before auto-expiring.
#
# block_ip / isolate_host: persistent until manually revoked (revoke_action())
#   - these correspond to the more severe verdicts (DDoS/Brute Force/PortScan/
#     SSH-Patator/FTP-Patator for block_ip; Bot for isolate_host) and warrant
#     staying blocked until a human reviews and lifts it.
# drop_connection / rate_limit: auto-expire after a fixed duration.
#   - NOTE, stated plainly: rate_limit is implemented here as a temporary
#     full block, not true bandwidth throttling. Real QoS-based rate
#     limiting on Windows requires netsh QoS policy objects, which is a
#     materially larger, separate piece of work and out of scope for this
#     demo. This is a documented, deliberate simplification, not a hidden
#     gap - the report should state it exactly this way.
ACTION_DURATIONS = {
    "block_ip": None,
    "isolate_host": None,
    "drop_connection": 60,
    "rate_limit": 120,
}


def _is_admin() -> bool:
    if ctypes is None:
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _log_execution(event: dict) -> None:
    EXECUTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
    with open(EXECUTION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _rule_name(action: str, target_ip: str) -> str:
    return f"{RULE_PREFIX}{action}_{target_ip.replace('.', '-')}"


def _add_block_rule(rule_name: str, target_ip: str) -> None:
    for direction in ("in", "out"):
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "add", "rule",
             f"name={rule_name}_{direction}", f"dir={direction}",
             "action=block", f"remoteip={target_ip}"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"netsh failed (dir={direction}): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )


def _remove_block_rule(rule_name: str) -> None:
    for direction in ("in", "out"):
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule",
             f"name={rule_name}_{direction}"],
            capture_output=True, text=True,
        )
        # Non-fatal if already gone - deletion is best-effort cleanup.


# Rules this process believes are in force: rule_name -> {"token", "timer"}.
# One attacker IP is usually flagged in many consecutive windows; without this
# every window would add the same firewall rule again. The token ties each
# expiry timer to the rule it was started for, so a stale timer can never
# remove a newer rule for the same target.
_active_rules = {}
_rules_lock = threading.RLock()


def _start_expiry(rule_name: str, action: str, target_ip: str, seconds: float) -> None:
    """Register a temporary rule and start its expiry timer. Caller holds _rules_lock."""
    token = object()
    timer = threading.Timer(max(0.0, seconds), _expire_rule, args=(rule_name, action, target_ip, token))
    timer.daemon = True
    _active_rules[rule_name] = {"token": token, "timer": timer}
    timer.start()


def _expire_rule(rule_name: str, action: str, target_ip: str, token: object) -> None:
    """Timer callback: remove a temporary rule and record that it expired on schedule."""
    with _rules_lock:
        entry = _active_rules.get(rule_name)
        if entry is None or entry["token"] is not token:
            return  # revoked meanwhile, or replaced by a newer rule - not this timer's to remove
        del _active_rules[rule_name]
        _remove_block_rule(rule_name)
        _log_execution({"action": action, "target_ip": target_ip, "rule_name": rule_name, "expired": True})


def execute_action(action: str, target_ip: str, predicted_class: str, confidence: float) -> dict:
    """
    Attempts to REALLY execute a prevention action, subject to the
    safety boundary in check_safe_to_execute(). Every call - whether
    it succeeds, is refused by the safety boundary, or fails at the
    OS level - is logged distinctly from the recommendation log, to
    EXECUTION_LOG_PATH, so "recommended" and "actually executed" are
    never conflated.

    If the same rule (same action, same target) is already in force,
    nothing is added again: the result has "executed": False and
    "already_active": True.

    Never raises - always returns a dict describing what actually
    happened, so it's safe to call from the backend without wrapping
    every call site in a try/except.
    """
    base_event = {
        "action": action, "target_ip": target_ip,
        "predicted_class": predicted_class, "confidence": confidence,
    }

    if action not in ACTION_DURATIONS:
        outcome = {"executed": False, "reason": f"Unknown action type: {action}"}
        _log_execution({**base_event, **outcome})
        return outcome

    try:
        check_safe_to_execute(target_ip)
    except ExecutionNotPermitted as e:
        outcome = {"executed": False, "reason": str(e)}
        _log_execution({**base_event, **outcome})
        return outcome

    if not _is_admin():
        outcome = {
            "executed": False,
            "reason": "Not running with administrator privileges - netsh "
                      "firewall rules require elevation.",
        }
        _log_execution({**base_event, **outcome})
        return outcome

    rule_name = _rule_name(action, target_ip)
    duration = ACTION_DURATIONS[action]

    # Held across check, add and log so two requests cannot both add the
    # rule, and an expiry timer cannot log "expired" before "executed".
    with _rules_lock:
        if rule_name in _active_rules:
            outcome = {"executed": False, "already_active": True, "rule_name": rule_name,
                       "reason": "This rule is already in force for this target - not added again."}
            # Logged under "active_rule", not "rule_name": only records that
            # change a rule's state carry rule_name (see sweep_expired_rules).
            _log_execution({**base_event, "executed": False, "already_active": True,
                            "active_rule": rule_name, "reason": outcome["reason"]})
            return outcome

        try:
            _add_block_rule(rule_name, target_ip)
        except RuntimeError as e:
            outcome = {"executed": False, "reason": f"OS-level execution failed: {e}"}
            _log_execution({**base_event, **outcome})
            return outcome

        outcome = {"executed": True, "rule_name": rule_name, "auto_expires_in_seconds": duration}
        _log_execution({**base_event, **outcome})
        if duration is None:
            _active_rules[rule_name] = {"token": object(), "timer": None}
        else:
            _start_expiry(rule_name, action, target_ip, duration)

    return outcome


def revoke_action(action: str, target_ip: str) -> dict:
    """
    Manually reverse an action, e.g. a persistent block_ip after human
    review. Works with the kill switch OFF - undoing must stay possible
    after real execution is switched off again - but only for targets
    inside the TEST-NET demo scope (check_in_scope).

    Never raises - returns {"revoked": True, "rule_name": ...} or
    {"revoked": False, "reason": ...}. Every attempt is logged.
    """
    base_event = {"action": action, "target_ip": target_ip}

    if action not in ACTION_DURATIONS:
        outcome = {"revoked": False, "reason": f"Unknown action type: {action}"}
        _log_execution({**base_event, **outcome})
        return outcome

    try:
        check_in_scope(target_ip)
    except ExecutionNotPermitted as e:
        outcome = {"revoked": False, "reason": str(e)}
        _log_execution({**base_event, **outcome})
        return outcome

    if not _is_admin():
        outcome = {"revoked": False,
                   "reason": "Not running with administrator privileges - removing "
                             "firewall rules requires elevation."}
        _log_execution({**base_event, **outcome})
        return outcome

    rule_name = _rule_name(action, target_ip)
    with _rules_lock:
        entry = _active_rules.pop(rule_name, None)
        if entry and entry["timer"] is not None:
            entry["timer"].cancel()
        _remove_block_rule(rule_name)
        outcome = {"revoked": True, "rule_name": rule_name}
        _log_execution({**base_event, **outcome})
    return outcome


def sweep_expired_rules() -> list:
    """
    Startup recovery from the execution log, for everything an in-process
    threading.Timer cannot survive (a crash or restart of the backend):

    - a temporary rule already past its expiry is removed (logged "swept");
    - a temporary rule not yet due gets a new timer for its remaining time;
    - every rule still in force is remembered, so execute_action() does
      not add it a second time after the restart.

    Call this once at backend startup, before serving any predictions.
    Safe to call any number of times - already-clean rules are simply
    skipped. Returns the list of rule_names it actually removed.
    """
    if not EXECUTION_LOG_PATH.exists():
        return []

    latest_state = {}  # rule_name -> most recent state-changing log record for it
    with open(EXECUTION_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            rule_name = record.get("rule_name")
            # Only records that change a rule's state count: added, expired,
            # revoked or swept. Refusals and "already active" skips do not.
            if rule_name and any(record.get(k) for k in ("executed", "revoked", "expired", "swept")):
                latest_state[rule_name] = record

    now = datetime.now(timezone.utc)
    swept = []

    for rule_name, record in latest_state.items():
        if record.get("revoked") or record.get("swept") or record.get("expired"):
            continue  # already cleaned up
        if not record.get("executed"):
            continue  # was never actually created
        duration = record.get("auto_expires_in_seconds")

        with _rules_lock:
            if duration is None:
                # Persistent rule still in force - only revoke_action() removes it.
                _active_rules.setdefault(rule_name, {"token": object(), "timer": None})
                continue

            created_at = datetime.fromisoformat(record["timestamp"])
            remaining = created_at.timestamp() + duration - now.timestamp()
            if remaining <= 0:
                entry = _active_rules.pop(rule_name, None)
                if entry and entry["timer"] is not None:
                    entry["timer"].cancel()
                _remove_block_rule(rule_name)
                _log_execution({
                    "action": record.get("action"), "target_ip": record.get("target_ip"),
                    "rule_name": rule_name, "swept": True,
                    "reason": "Expiry timer never fired (likely a process restart) - "
                              "cleaned up by startup sweep instead.",
                })
                swept.append(rule_name)
            elif rule_name not in _active_rules:
                _start_expiry(rule_name, record.get("action"), record.get("target_ip"), remaining)

    return swept
