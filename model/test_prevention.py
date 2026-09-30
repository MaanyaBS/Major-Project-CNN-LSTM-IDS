"""
Tests for the prevention layer: the policy (class_action_mapping.py) and
the real-execution engine (prevention_executor.py).

Run:  python model/test_prevention.py

These tests never touch the real firewall: the OS-level functions are
replaced with recorders, and any real netsh call that slipped through
would raise and fail the test.
"""

import contextlib
import json
import math
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import class_action_mapping as cam  # noqa: E402
import prevention_executor as pe  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ACTIONS = {"no_action", "block_ip", "isolate_host", "rate_limit", "drop_connection",
           "terminate_session", "sanitize_input"}
SEVERITIES = {"low", "medium", "high", "critical"}
DATA_STARVED = {"Web Attack - Sql Injection", "Heartbleed", "Infiltration"}


class _NoRealNetsh:
    @staticmethod
    def run(*args, **kwargs):
        raise AssertionError(f"real OS command attempted in a test: {args}")


@contextlib.contextmanager
def sandbox(enabled=True, admin=True, add_error=None, durations=None):
    """Patch the executor so nothing reaches the OS; record what would have happened."""
    calls = {"added": [], "removed": []}
    saved = {k: getattr(pe, k) for k in ("PREVENTION_EXECUTION_ENABLED", "_is_admin", "_add_block_rule",
                                         "_remove_block_rule", "subprocess", "EXECUTION_LOG_PATH",
                                         "ACTION_DURATIONS")}

    def fake_add(rule_name, target_ip):
        if add_error:
            raise RuntimeError(add_error)
        calls["added"].append((rule_name, target_ip))

    with tempfile.TemporaryDirectory() as tmp:
        pe.PREVENTION_EXECUTION_ENABLED = enabled
        pe._is_admin = lambda: admin
        pe._add_block_rule = fake_add
        pe._remove_block_rule = lambda rule_name: calls["removed"].append(rule_name)
        pe.subprocess = _NoRealNetsh
        pe.EXECUTION_LOG_PATH = Path(tmp) / "log.jsonl"
        pe.ACTION_DURATIONS = dict(saved["ACTION_DURATIONS"], **(durations or {}))
        try:
            yield calls
        finally:
            for k, v in saved.items():
                setattr(pe, k, v)


def log_records():
    if not pe.EXECUTION_LOG_PATH.exists():
        return []
    return [json.loads(l) for l in pe.EXECUTION_LOG_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_log(records):
    with open(pe.EXECUTION_LOG_PATH, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def ago(seconds):
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


# ----------------------------------------------------------------------
# Policy
# ----------------------------------------------------------------------

def test_policy_covers_exactly_the_model_classes():
    with open(REPO / "model" / "artifacts" / "label_mapping_v2.json") as f:
        model_classes = set(json.load(f))
    assert set(cam.CLASS_ACTION_MAP) == model_classes, \
        f"policy/model class mismatch: {set(cam.CLASS_ACTION_MAP) ^ model_classes}"


def test_every_policy_entry_is_complete_and_valid():
    for name, p in cam.CLASS_ACTION_MAP.items():
        assert p["action"] in ACTIONS, f"{name}: unknown action {p['action']}"
        assert p["severity"] in SEVERITIES, f"{name}: unknown severity {p['severity']}"
        t = p["threshold"]
        assert math.isinf(t) or 0 < t <= 1, f"{name}: threshold {t} out of range"


def test_benign_never_triggers_an_action():
    for conf in (0.0, 0.5, 0.999, 1.0):
        assert cam.get_action("BENIGN", conf)["status"] == "no_action_needed"


def test_threshold_boundary_is_inclusive():
    for name, p in cam.CLASS_ACTION_MAP.items():
        t = p["threshold"]
        if name == "BENIGN" or math.isinf(t):
            continue
        assert cam.get_action(name, t)["status"] == "auto_action", f"{name} at its threshold"
        assert cam.get_action(name, t - 1e-6)["status"] == "held_for_review", f"{name} just below"


def test_data_starved_classes_never_auto_act():
    for name in DATA_STARVED:
        p = cam.CLASS_ACTION_MAP[name]
        assert math.isinf(p["threshold"]) and p.get("never_auto_fire"), f"{name} not hard-locked"
        assert cam.get_action(name, 1.0)["status"] == "held_for_review"


def test_less_reliable_classes_need_more_confidence():
    finite = [(p["f1_score"], p["threshold"], n) for n, p in cam.CLASS_ACTION_MAP.items()
              if n != "BENIGN" and not math.isinf(p["threshold"])]
    finite.sort(key=lambda x: -x[0])
    for (f_hi, t_hi, n_hi), (f_lo, t_lo, n_lo) in zip(finite, finite[1:]):
        assert t_lo >= t_hi, f"{n_lo} (F1 {f_lo}) has a lower threshold than {n_hi} (F1 {f_hi})"


def test_unknown_class_goes_to_review():
    r = cam.get_action("Not A Real Class", 1.0)
    assert r == {"action": "alert_only", "severity": "medium", "status": "held_for_review"}


# ----------------------------------------------------------------------
# Execution engine: refusals
# ----------------------------------------------------------------------

def test_kill_switch_off_refuses_everything():
    with sandbox(enabled=False) as calls:
        r = pe.execute_action("block_ip", "192.0.2.10", "DDoS", 0.99)
        assert r["executed"] is False and "disabled" in r["reason"]
        assert not calls["added"]


def test_real_and_malformed_targets_refused_even_when_enabled_and_admin():
    targets = [
        "8.8.8.8", "192.168.1.1", "10.0.0.5", "172.16.0.1",  # real, routable/private
        "127.0.0.1", "0.0.0.0", "255.255.255.255",            # deny-list
        "192.0.3.1", "198.51.101.1",                         # just outside the test ranges
        "::1", "::ffff:192.0.2.10",                           # IPv6 / mapped
        "192.0.2.0/24",                                       # a whole range
        "192.0.2.10,8.8.8.8", "192.0.2.1-192.0.2.255",        # netsh list / range syntax
        "any", "localsubnet", " 192.0.2.10", "192.0.2.010",   # keywords, padding, leading zero
        "", "not-an-ip", None, 3221225994,                   # empty, garbage, wrong types
    ]
    with sandbox() as calls:
        for t in targets:
            r = pe.execute_action("block_ip", t, "DDoS", 0.99)
            assert r["executed"] is False, f"{t!r} was not refused"
        assert not calls["added"], f"a refused target reached the firewall: {calls['added']}"


def test_not_admin_refuses():
    with sandbox(admin=False) as calls:
        r = pe.execute_action("block_ip", "192.0.2.10", "DDoS", 0.99)
        assert r["executed"] is False and "administrator" in r["reason"]
        assert not calls["added"]


def test_unknown_action_refused():
    with sandbox() as calls:
        r = pe.execute_action("wipe_disk", "192.0.2.10", "DDoS", 0.99)
        assert r["executed"] is False and "Unknown action" in r["reason"]
        assert not calls["added"]


def test_os_failure_is_reported_not_raised():
    with sandbox(add_error="access denied") as calls:
        r = pe.execute_action("block_ip", "192.0.2.10", "DDoS", 0.99)
        assert r["executed"] is False and "OS-level execution failed" in r["reason"]


# ----------------------------------------------------------------------
# Execution engine: allowed actions, logging, expiry, sweep
# ----------------------------------------------------------------------

def test_test_net_targets_execute():
    with sandbox() as calls:
        for ip in ("192.0.2.10", "198.51.100.1", "203.0.113.250"):
            r = pe.execute_action("block_ip", ip, "DDoS", 0.99)
            assert r["executed"] is True and r["rule_name"] == pe._rule_name("block_ip", ip)
        assert len(calls["added"]) == 3


def test_every_attempt_is_logged_once():
    with sandbox():
        pe.execute_action("block_ip", "192.0.2.10", "DDoS", 0.99)   # executed
        pe.execute_action("block_ip", "8.8.8.8", "DDoS", 0.99)      # refused
        pe.execute_action("wipe_disk", "192.0.2.10", "DDoS", 0.99)  # refused
        pe.revoke_action("block_ip", "192.0.2.10")                  # revoked
        recs = log_records()
        assert len(recs) == 4
        assert [r.get("executed") for r in recs[:3]] == [True, False, False]
        assert recs[3]["revoked"] is True and recs[3]["rule_name"] == pe._rule_name("block_ip", "192.0.2.10")


def test_temporary_rule_expires_and_is_logged_so_sweep_leaves_it():
    with sandbox(durations={"drop_connection": 0.05}) as calls:
        r = pe.execute_action("drop_connection", "192.0.2.20", "DoS slowloris", 0.99)
        deadline = time.time() + 3
        while r["rule_name"] not in calls["removed"] and time.time() < deadline:
            time.sleep(0.02)
        assert r["rule_name"] in calls["removed"], "timer did not remove the rule"
        time.sleep(0.05)
        assert any(rec.get("expired") for rec in log_records()), "expiry was not logged"
        assert pe.sweep_expired_rules() == [], "sweep re-cleaned a rule that already expired"


def test_revoked_rule_is_not_swept_again():
    with sandbox():
        rule = pe._rule_name("drop_connection", "192.0.2.7")
        write_log([{"timestamp": ago(3600), "action": "drop_connection", "target_ip": "192.0.2.7",
                    "rule_name": rule, "executed": True, "auto_expires_in_seconds": 60}])
        pe.revoke_action("drop_connection", "192.0.2.7")
        assert pe.sweep_expired_rules() == [], "sweep re-cleaned a revoked rule"


def test_sweep_cleans_only_stale_temporary_rules_and_is_idempotent():
    with sandbox() as calls:
        stale = pe._rule_name("rate_limit", "192.0.2.1")
        write_log([
            {"timestamp": ago(3600), "rule_name": stale, "executed": True, "auto_expires_in_seconds": 120},
            {"timestamp": ago(3600), "rule_name": pe._rule_name("block_ip", "192.0.2.2"),
             "executed": True, "auto_expires_in_seconds": None},                                  # persistent
            {"timestamp": ago(5), "rule_name": pe._rule_name("rate_limit", "192.0.2.3"),
             "executed": True, "auto_expires_in_seconds": 120},                                   # not due yet
            {"timestamp": ago(3600), "rule_name": pe._rule_name("rate_limit", "192.0.2.4"),
             "executed": False},                                                                  # never created
        ])
        assert pe.sweep_expired_rules() == [stale]
        assert calls["removed"] == [stale]
        assert pe.sweep_expired_rules() == [], "second sweep was not a no-op"


if __name__ == "__main__":
    tests = [fn for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
