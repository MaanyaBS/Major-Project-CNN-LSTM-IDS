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


def execute_action(action: str, target_ip: str, predicted_class: str, confidence: float) -> dict:
    """
    Attempts to REALLY execute a prevention action, subject to the
    safety boundary in check_safe_to_execute(). Every call - whether
    it succeeds, is refused by the safety boundary, or fails at the
    OS level - is logged distinctly from the recommendation log, to
    EXECUTION_LOG_PATH, so "recommended" and "actually executed" are
    never conflated.

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

    try:
        _add_block_rule(rule_name, target_ip)
    except RuntimeError as e:
        outcome = {"executed": False, "reason": f"OS-level execution failed: {e}"}
        _log_execution({**base_event, **outcome})
        return outcome

    outcome = {"executed": True, "rule_name": rule_name, "auto_expires_in_seconds": duration}
    _log_execution({**base_event, **outcome})

    if duration is not None:
        timer = threading.Timer(duration, _remove_block_rule, args=(rule_name,))
        timer.daemon = True
        timer.start()

    return outcome


def revoke_action(action: str, target_ip: str) -> None:
    """Manually reverse a persistent (non-expiring) action, e.g. after human review."""
    rule_name = _rule_name(action, target_ip)
    _remove_block_rule(rule_name)
    _log_execution({"action": action, "target_ip": target_ip, "revoked": True})
