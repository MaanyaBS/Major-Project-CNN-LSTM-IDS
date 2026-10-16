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
REVIEW_ONLY = {"cicids2017": {"Web Attack - Sql Injection", "Heartbleed", "Infiltration",  # too few test rows
                              "Bot", "Web Attack - Brute Force", "Web Attack - XSS"},    # F1 below 0.15
               "mu_iot": {"MiTM", "Spyware"}}                                            # no held-out evidence


def acting_entries(dataset):
    """(name, policy) for attack classes that can auto-act."""
    return [(n, p) for n, p in cam.POLICIES[dataset].items()
            if p["action"] != "no_action" and not p.get("never_auto_fire")]


def curve_entries(dataset):
    """(name, policy) for attack classes with a finite threshold: the F1 -> threshold calibration points."""
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
                                         "ACTION_DURATIONS", "_active_rules")}

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
        pe._active_rules = {}
        saved_env = os.environ.pop(pe.DEMO_TARGETS_ENV, None)   # the tester's own setting must not leak in
        try:
            yield calls
        finally:
            for entry in pe._active_rules.values():  # no timer may outlive the sandbox
                if entry["timer"] is not None:
                    entry["timer"].cancel()
            for k, v in saved.items():
                setattr(pe, k, v)
            os.environ.pop(pe.DEMO_TARGETS_ENV, None)
            if saved_env is not None:
                os.environ[pe.DEMO_TARGETS_ENV] = saved_env


@contextlib.contextmanager
def demo_env(value):
    """Temporarily set (or clear, with None) the demo-target environment variable."""
    old = os.environ.pop(pe.DEMO_TARGETS_ENV, None)
    if value is not None:
        os.environ[pe.DEMO_TARGETS_ENV] = value
    try:
        yield
    finally:
        os.environ.pop(pe.DEMO_TARGETS_ENV, None)
        if old is not None:
            os.environ[pe.DEMO_TARGETS_ENV] = old


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
        locked = {n for n, p in cam.POLICIES[dataset].items() if p.get("never_auto_fire")}
        assert locked == names, f"{dataset}: locked {sorted(locked)}, expected {sorted(names)}"
        unflagged_inf = {n for n, p in cam.POLICIES[dataset].items()
                         if math.isinf(p["threshold"]) and not p.get("never_auto_fire")}
        assert not unflagged_inf, f"{dataset}: infinite threshold without the flag: {sorted(unflagged_inf)}"
        for name in names:
            assert cam.get_action(name, 1.0, dataset)["status"] == "held_for_review", f"{dataset}/{name}"


def test_less_reliable_classes_need_more_confidence():
    # One F1 -> threshold rule across both datasets.
    finite = [(p["f1_score"], p["threshold"], f"{d}/{n}") for d in cam.POLICIES for n, p in curve_entries(d)]
    finite.sort(key=lambda x: -x[0])
    for (f_hi, t_hi, n_hi), (f_lo, t_lo, n_lo) in zip(finite, finite[1:]):
        assert t_lo >= t_hi, f"{n_lo} (F1 {f_lo}) has a lower threshold than {n_hi} (F1 {f_hi})"


def test_mu_iot_thresholds_follow_the_cicids_curve():
    f1s, ths = zip(*sorted((p["f1_score"], p["threshold"]) for _, p in curve_entries("cicids2017")))
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


# ----------------------------------------------------------------------
# Execution engine: one rule per target, revoke, restart recovery
# ----------------------------------------------------------------------

def wait_until(condition, timeout=3.0):
    deadline = time.time() + timeout
    while not condition() and time.time() < deadline:
        time.sleep(0.02)
    return condition()


def test_same_target_flagged_repeatedly_adds_one_rule():
    with sandbox() as calls:
        results = [pe.execute_action("block_ip", "192.0.2.10", "DDoS", 0.99) for _ in range(50)]
        assert len(calls["added"]) == 1, f"rule added {len(calls['added'])} times"
        assert results[0]["executed"] is True
        assert all(r["executed"] is False and r["already_active"] for r in results[1:])
        assert sum(1 for r in log_records() if r.get("executed")) == 1
        # A different target is a different rule; a different action on a
        # device that is already blocked is not (one rule per device).
        pe.execute_action("block_ip", "192.0.2.11", "DDoS", 0.99)
        again = pe.execute_action("rate_limit", "192.0.2.10", "DoS Hulk", 0.99)
        assert again["already_active"] and again["rule_name"] == pe._rule_name("block_ip", "192.0.2.10")
        assert len(calls["added"]) == 2


def test_one_rule_per_device_across_actions():
    with sandbox(durations={"rate_limit": 30, "drop_connection": 30}) as calls:
        ip = "192.0.2.30"
        assert pe.execute_action("rate_limit", ip, "DoS Hulk", 0.99)["executed"] is True
        # temporary rule in force: another temporary action is covered
        assert pe.execute_action("drop_connection", ip, "DoS slowloris", 0.99)["already_active"]
        # but a persistent block still replaces it
        assert pe.execute_action("block_ip", ip, "PortScan", 0.99)["executed"] is True
        # and then covers everything
        for action in ("rate_limit", "drop_connection", "isolate_host", "block_ip"):
            assert pe.execute_action(action, ip, "X", 0.99)["already_active"], action
        assert len(calls["added"]) == 2


def test_active_rules_lists_what_is_in_force():
    with sandbox(durations={"rate_limit": 30}):
        assert pe.active_rules() == []
        pe.execute_action("block_ip", "192.0.2.40", "PortScan", 0.99)
        pe.execute_action("rate_limit", "192.0.2.41", "DoS Hulk", 0.99)
        rules = {r["target_ip"]: r for r in pe.active_rules()}
        assert set(rules) == {"192.0.2.40", "192.0.2.41"}
        assert rules["192.0.2.40"]["persistent"] is True and rules["192.0.2.40"]["expires_in_seconds"] is None
        assert rules["192.0.2.41"]["persistent"] is False and 0 < rules["192.0.2.41"]["expires_in_seconds"] <= 30
        assert rules["192.0.2.40"]["rule_name"] == pe._rule_name("block_ip", "192.0.2.40")
        pe.revoke_action("block_ip", "192.0.2.40")
        assert [r["target_ip"] for r in pe.active_rules()] == ["192.0.2.41"]


def test_demo_target_list_accepts_only_single_private_lan_addresses():
    accepted, rejected = pe.parse_demo_targets(
        "192.168.43.57, 10.0.0.7;172.20.10.3, 192.168.43.0/24, 192.168.43.1-192.168.43.9, 8.8.8.8, "
        "224.0.0.251, 127.0.0.1, 192.168.43.255, 192.168.43.0, 192.168.043.5, fe80::1, nonsense, 192.168.43.10",
        local_addresses={"192.168.43.10"})
    assert accepted == {"192.168.43.57", "10.0.0.7", "172.20.10.3"}
    reasons = dict(rejected)
    assert "ranges" in reasons["192.168.43.0/24"] and "ranges" in reasons["192.168.43.1-192.168.43.9"]
    assert "RFC 1918" in reasons["8.8.8.8"] and "RFC 1918" in reasons["224.0.0.251"]
    assert "RFC 1918" in reasons["127.0.0.1"]
    assert "broadcast" in reasons["192.168.43.255"] and "broadcast" in reasons["192.168.43.0"]
    assert "own address" in reasons["192.168.43.10"]
    assert "192.168.043.5" in reasons and "fe80::1" in reasons and "nonsense" in reasons


def test_lan_device_blockable_only_when_listed():
    lan = "192.168.43.57"
    with sandbox() as calls:
        with demo_env(None):
            assert pe.execute_action("block_ip", lan, "PortScan", 0.99)["executed"] is False
        with demo_env("192.168.43.99"):
            assert pe.execute_action("block_ip", lan, "PortScan", 0.99)["executed"] is False, "another device listed"
        with demo_env("192.168.43.0/24"):
            assert pe.execute_action("block_ip", lan, "PortScan", 0.99)["executed"] is False, "ranges never count"
        assert not calls["added"]
        with demo_env(lan):
            assert pe.execute_action("block_ip", lan, "PortScan", 0.99)["executed"] is True
            assert pe.execute_action("block_ip", "192.168.43.58", "PortScan", 0.99)["executed"] is False
        assert calls["added"] == [(pe._rule_name("block_ip", lan), lan)]
        # once listed and blocked, it can be lifted again - even after the switch is turned off
        pe.PREVENTION_EXECUTION_ENABLED = False
        with demo_env(lan):
            assert pe.revoke_action("block_ip", lan)["revoked"] is True


def test_rule_can_be_applied_again_after_revoke_or_expiry():
    with sandbox(durations={"drop_connection": 0.05}) as calls:
        pe.execute_action("block_ip", "192.0.2.10", "DDoS", 0.99)
        pe.revoke_action("block_ip", "192.0.2.10")
        assert pe.execute_action("block_ip", "192.0.2.10", "DDoS", 0.99)["executed"] is True

        rule = pe.execute_action("drop_connection", "192.0.2.20", "DoS slowloris", 0.99)["rule_name"]
        assert wait_until(lambda: rule in calls["removed"]), "temporary rule did not expire"
        assert pe.execute_action("drop_connection", "192.0.2.20", "DoS slowloris", 0.99)["executed"] is True
        assert len(calls["added"]) == 4


def test_stale_timer_never_removes_a_newer_rule():
    with sandbox(durations={"drop_connection": 0.2}) as calls:
        rule = pe.execute_action("drop_connection", "192.0.2.30", "DoS slowloris", 0.99)["rule_name"]
        pe.revoke_action("drop_connection", "192.0.2.30")            # cancels the 0.2 s timer
        pe.ACTION_DURATIONS["drop_connection"] = 30
        pe.execute_action("drop_connection", "192.0.2.30", "DoS slowloris", 0.99)  # new rule, 30 s
        time.sleep(0.4)
        assert calls["removed"] == [rule], f"new rule removed early: {calls['removed']}"
        assert rule in pe._active_rules


def test_timer_that_already_fired_cannot_remove_a_newer_rule():
    # The race cancel() cannot stop: the old timer has fired and is waiting
    # for the lock while the rule is revoked and added again.
    with sandbox(durations={"drop_connection": 30}) as calls:
        rule = pe.execute_action("drop_connection", "192.0.2.31", "DoS slowloris", 0.99)["rule_name"]
        old_token = pe._active_rules[rule]["token"]
        pe.revoke_action("drop_connection", "192.0.2.31")
        pe.execute_action("drop_connection", "192.0.2.31", "DoS slowloris", 0.99)
        pe._expire_rule(rule, "drop_connection", "192.0.2.31", old_token)   # the late callback
        assert calls["removed"] == [rule] and rule in pe._active_rules


def test_revoke_cancels_the_expiry_timer():
    with sandbox(durations={"drop_connection": 30}):
        rule = pe.execute_action("drop_connection", "192.0.2.32", "DoS slowloris", 0.99)["rule_name"]
        timer = pe._active_rules[rule]["timer"]
        pe.revoke_action("drop_connection", "192.0.2.32")
        assert timer.finished.is_set(), "timer still pending after revoke"


def test_revoke_works_with_switch_off_but_only_in_scope():
    with sandbox() as calls:
        pe.execute_action("block_ip", "192.0.2.10", "DDoS", 0.99)
        pe.PREVENTION_EXECUTION_ENABLED = False                       # e.g. restarted without the env var
        r = pe.revoke_action("block_ip", "192.0.2.10")
        assert r["revoked"] is True and calls["removed"] == [r["rule_name"]]
        for action, target in [("block_ip", "8.8.8.8"), ("block_ip", "192.0.2.10,8.8.8.8"),
                               ("block_ip", None), ("wipe_disk", "192.0.2.10")]:
            r = pe.revoke_action(action, target)
            assert r["revoked"] is False and r["reason"], f"{action} {target!r} was not refused"
        assert len(calls["removed"]) == 1, "a refused revoke reached the firewall"


def test_revoke_needs_admin():
    with sandbox(admin=False) as calls:
        r = pe.revoke_action("block_ip", "192.0.2.10")
        assert r["revoked"] is False and "administrator" in r["reason"]
        assert not calls["removed"]


def test_restart_restores_active_rules_and_pending_expiry():
    with sandbox() as calls:
        persistent = pe._rule_name("block_ip", "192.0.2.40")
        pending = pe._rule_name("drop_connection", "192.0.2.41")
        write_log([
            {"timestamp": ago(3600), "rule_name": persistent, "action": "block_ip",
             "target_ip": "192.0.2.40", "executed": True, "auto_expires_in_seconds": None},
            {"timestamp": ago(1), "rule_name": pending, "action": "drop_connection",
             "target_ip": "192.0.2.41", "executed": True, "auto_expires_in_seconds": 1.3},
        ])
        assert pe.sweep_expired_rules() == []                          # neither is due yet
        assert pe.execute_action("block_ip", "192.0.2.40", "DDoS", 0.99)["already_active"]
        assert not calls["added"], "a rule already in force was added again after restart"
        assert wait_until(lambda: pending in calls["removed"]), "pending expiry was not rescheduled"
        assert any(r.get("expired") and r.get("rule_name") == pending for r in log_records())


def test_refusals_and_skips_do_not_hide_a_stale_rule_from_the_sweep():
    with sandbox() as calls:
        stale = pe._rule_name("rate_limit", "192.0.2.50")
        write_log([{"timestamp": ago(3600), "rule_name": stale, "action": "rate_limit",
                    "target_ip": "192.0.2.50", "executed": True, "auto_expires_in_seconds": 120}])
        pe._is_admin = lambda: False
        pe.revoke_action("rate_limit", "192.0.2.50")                   # refused: not admin
        with open(pe.EXECUTION_LOG_PATH, "a", encoding="utf-8") as f:  # a record naming the rule
            f.write(json.dumps({"timestamp": ago(10), "rule_name": stale,   # without changing it
                                "executed": False, "reason": "refused"}) + "\n")
        assert pe.sweep_expired_rules() == [stale]


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
