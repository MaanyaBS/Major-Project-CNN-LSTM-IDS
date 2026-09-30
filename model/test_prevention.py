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
import re
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import class_action_mapping as cam  # noqa: E402
import prevention_executor as pe  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ACTIONS = {"no_action", "block_ip", "isolate_host", "rate_limit", "drop_connection",
           "terminate_session", "sanitize_input"}
SEVERITIES = {"low", "medium", "high", "critical"}
LABEL_MAPPINGS = {"cicids2017": REPO / "model" / "artifacts" / "label_mapping_v2.json",
                  "mu_iot": REPO / "model" / "artifacts" / "mu_iot" / "label_mapping.json"}
BENIGN_NAME = {"cicids2017": "BENIGN", "mu_iot": "normal"}
REVIEW_ONLY = {"cicids2017": {"Web Attack - Sql Injection", "Heartbleed", "Infiltration"},  # too few test rows
               "mu_iot": {"MiTM", "Spyware"}}                                            # no held-out evidence


def acting_entries(dataset):
    """(name, policy) for attack classes that can auto-act (finite threshold)."""
    return [(n, p) for n, p in cam.POLICIES[dataset].items()
            if p["action"] != "no_action" and not math.isinf(p["threshold"])]


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
    assert set(cam.POLICIES) == set(LABEL_MAPPINGS)
    for dataset, path in LABEL_MAPPINGS.items():
        with open(path) as f:
            model_classes = set(json.load(f))
        policy = set(cam.POLICIES[dataset])
        assert policy == model_classes, f"{dataset}: policy/model class mismatch: {policy ^ model_classes}"


def test_every_policy_entry_is_complete_and_valid():
    for dataset, policy in cam.POLICIES.items():
        for name, p in policy.items():
            assert p["action"] in ACTIONS, f"{dataset}/{name}: unknown action {p['action']}"
            assert p["severity"] in SEVERITIES, f"{dataset}/{name}: unknown severity {p['severity']}"
            t = p["threshold"]
            assert math.isinf(t) or 0 < t <= 1, f"{dataset}/{name}: threshold {t} out of range"


def test_policy_f1_matches_committed_results():
    metrics = json.loads((REPO / "model" / "results" / "mu_iot" / "mu_iot_metrics.json").read_text())
    for name, p in cam.MU_IOT_CLASS_ACTION_MAP.items():
        measured = round(metrics[p["f1_source"]]["per_class"][name]["f1"], 4)
        assert p["f1_score"] == measured, f"mu_iot/{name}: policy F1 {p['f1_score']} vs results {measured}"
    # The committed CICIDS2017 report prints F1 to 2 decimals.
    report = (REPO / "model" / "results" / "cnn_lstm_v2_full_test_results.txt").read_text(encoding="utf-8")
    for name, p in cam.CLASS_ACTION_MAP.items():
        if "f1_score" not in p:
            continue
        m = re.search(rf"^\s*{re.escape(name)}\s+[\d.]+\s+[\d.]+\s+([\d.]+)\s+\d+\s*$", report, re.M)
        assert m, f"cicids2017/{name}: not found in the results report"
        assert float(m.group(1)) == round(p["f1_score"], 2), f"cicids2017/{name}: policy F1 {p['f1_score']} vs report {m.group(1)}"


def test_benign_never_triggers_an_action():
    for dataset, benign in BENIGN_NAME.items():
        for conf in (0.0, 0.5, 0.999, 1.0):
            assert cam.get_action(benign, conf, dataset)["status"] == "no_action_needed", f"{dataset}/{benign}"


def test_threshold_boundary_is_inclusive():
    for dataset in cam.POLICIES:
        for name, p in acting_entries(dataset):
            t = p["threshold"]
            assert cam.get_action(name, t, dataset)["status"] == "auto_action", f"{dataset}/{name} at its threshold"
            assert cam.get_action(name, t - 1e-6, dataset)["status"] == "held_for_review", f"{dataset}/{name} just below"


def test_review_only_classes_never_auto_act():
    for dataset, names in REVIEW_ONLY.items():
        locked = {n for n, p in cam.POLICIES[dataset].items() if math.isinf(p["threshold"])}
        assert locked == names, f"{dataset}: hard-locked {sorted(locked)}, expected {sorted(names)}"
        for name in names:
            assert cam.POLICIES[dataset][name].get("never_auto_fire"), f"{dataset}/{name} not flagged"
            assert cam.get_action(name, 1.0, dataset)["status"] == "held_for_review", f"{dataset}/{name}"


def test_less_reliable_classes_need_more_confidence():
    # One F1 -> threshold rule across both datasets.
    finite = [(p["f1_score"], p["threshold"], f"{d}/{n}") for d in cam.POLICIES for n, p in acting_entries(d)]
    finite.sort(key=lambda x: -x[0])
    for (f_hi, t_hi, n_hi), (f_lo, t_lo, n_lo) in zip(finite, finite[1:]):
        assert t_lo >= t_hi, f"{n_lo} (F1 {f_lo}) has a lower threshold than {n_hi} (F1 {f_hi})"


def test_mu_iot_thresholds_follow_the_cicids_curve():
    f1s, ths = zip(*sorted((p["f1_score"], p["threshold"]) for _, p in acting_entries("cicids2017")))
    for name, p in acting_entries("mu_iot"):
        expected = round(float(np.interp(p["f1_score"], f1s, ths)), 2)
        assert p["threshold"] == expected, f"mu_iot/{name}: threshold {p['threshold']}, curve gives {expected}"


def test_mu_iot_auto_actions_rest_on_held_out_evidence():
    for name, p in acting_entries("mu_iot"):
        assert p["f1_source"] == "test_heldout", f"mu_iot/{name} can auto-act on {p['f1_source']} evidence"
        assert p["action"] in pe.ACTION_DURATIONS, f"mu_iot/{name}: {p['action']} is not really executable"


def test_datasets_are_kept_apart():
    # "DDoS" exists in both: each dataset must use its own threshold (0.55 vs 0.84).
    assert cam.get_action("DDoS", 0.60)["status"] == "auto_action"
    assert cam.get_action("DDoS", 0.60, dataset="mu_iot")["status"] == "held_for_review"
    assert cam.get_action("Scan", 0.99, dataset="mu_iot")["status"] == "auto_action"
    assert cam.get_action("Scan", 0.99)["action"] == "alert_only"                       # unknown to CICIDS2017
    assert cam.get_action("PortScan", 0.99, dataset="mu_iot")["action"] == "alert_only"  # unknown to MU-IoT


def test_unknown_dataset_is_an_error():
    for bad in ("mu-iot", "MU_IOT", "cicids", "", None):
        try:
            cam.get_action("DDoS", 0.99, dataset=bad)
        except ValueError:
            continue
        raise AssertionError(f"dataset={bad!r} was accepted")


def test_unknown_class_goes_to_review():
    for dataset in cam.POLICIES:
        r = cam.get_action("Not A Real Class", 1.0, dataset)
        assert r == {"action": "alert_only", "severity": "medium", "status": "held_for_review"}, dataset


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
