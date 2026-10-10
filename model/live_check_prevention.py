"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Prevention Engine - Live Firewall Check (run as administrator)
Author  : Maanya B S, Ruthwik Sai Ganesh , Varshini D N
==========================================================
End-to-end check of prevention_executor.py against the REAL Windows
Firewall. model/test_prevention.py replaces the firewall with recorders;
this script confirms the same behaviour with real netsh rules:

    1. block_ip adds exactly one inbound and one outbound rule
    2. the same target flagged again adds nothing ("already_active")
    3. real addresses are refused and never reach the firewall
    4. a temporary rule (drop_connection) is removed by its timer
    5. revoke works with the kill switch OFF, and only inside TEST-NET
    6. after a simulated restart, the startup sweep remembers rules still
       in force and restarts the timer of a temporary rule
    7. with the kill switch OFF nothing is added

Safety: only RFC 5737 TEST-NET addresses are used (the engine refuses
anything else), only rules named IDS_DEMO_* for this script's own targets
are touched, and every one of them is removed at the end, pass or fail.
The engine's real log (model/results/prevention_execution_log.jsonl) is
not used: this run logs to a temporary file.

Timers are shortened for the check (drop_connection 8 s, rate_limit 12 s
instead of 60 s and 120 s); the mechanism is the same.

Usage, in an ADMINISTRATOR PowerShell at the repository root:

    .\\venv\\Scripts\\python.exe model\\live_check_prevention.py

Writes model/results/prevention_live_check.txt.
--simulate runs the same steps against an in-memory firewall (no admin,
no netsh) to check the script itself.
"""

import argparse
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(MODEL_DIR))
import prevention_executor as pe  # noqa: E402

BLOCK_IP = "192.0.2.66"       # persistent block, then revoked
TEMP_IP = "198.51.100.20"     # drop_connection, expires on its own
RESTART_BLOCK_IP = "203.0.113.7"
RESTART_TEMP_IP = "203.0.113.8"
REAL_IPS = ("8.8.8.8", "192.168.1.1")
SHORT_DURATIONS = {"drop_connection": 8, "rate_limit": 12}

ALL_RULES = [pe._rule_name(a, ip) for a, ip in (
    ("block_ip", BLOCK_IP), ("drop_connection", TEMP_IP),
    ("block_ip", RESTART_BLOCK_IP), ("rate_limit", RESTART_TEMP_IP),
    *(("block_ip", ip) for ip in REAL_IPS))]


class RealFirewall:
    name = "Windows Firewall (netsh advfirewall)"

    @staticmethod
    def count(rule_name):
        """How many firewall rules carry exactly this name (in + out counted separately)."""
        total = 0
        for direction in ("in", "out"):
            full = f"{rule_name}_{direction}"
            out = subprocess.run(["netsh", "advfirewall", "firewall", "show", "rule", f"name={full}"],
                                 capture_output=True, text=True)
            total += sum(1 for line in out.stdout.splitlines() if line.strip().endswith(full))
        return total


class SimulatedFirewall:
    """In-memory stand-in with netsh's behaviour: adding a name twice gives two rules."""
    name = "simulated firewall (--simulate)"

    def __init__(self):
        self.rules = []
        pe._add_block_rule = lambda rule_name, ip: self.rules.extend([f"{rule_name}_in", f"{rule_name}_out"])
        pe._remove_block_rule = lambda rule_name: self.rules.__setitem__(
            slice(None), [r for r in self.rules if r not in (f"{rule_name}_in", f"{rule_name}_out")])
        pe._is_admin = lambda: True

    def count(self, rule_name):
        return sum(r in (f"{rule_name}_in", f"{rule_name}_out") for r in self.rules)


class Report:
    def __init__(self):
        self.lines, self.failed = [], 0

    def check(self, label, ok, detail=""):
        self.failed += not ok
        line = f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail else "")
        self.lines.append(line)
        print(line, flush=True)

    def note(self, text):
        self.lines.append(text)
        print(text, flush=True)


def wait_until(condition, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition():
            return True
        time.sleep(0.5)
    return condition()


def simulate_restart():
    """What a backend restart does to the engine: timers die, in-memory state is lost."""
    with pe._rules_lock:
        for entry in pe._active_rules.values():
            if entry["timer"] is not None:
                entry["timer"].cancel()
        pe._active_rules.clear()


def run(fw, r):
    pe.ACTION_DURATIONS.update(SHORT_DURATIONS)

    r.note("\n1. block_ip adds one inbound and one outbound rule")
    pe.PREVENTION_EXECUTION_ENABLED = True
    out = pe.execute_action("block_ip", BLOCK_IP, "PortScan", 0.99)
    block_rule = pe._rule_name("block_ip", BLOCK_IP)
    r.check("execute_action reports executed", out.get("executed") is True, out.get("reason", ""))
    r.check("firewall holds exactly 2 rules (in + out)", fw.count(block_rule) == 2, f"found {fw.count(block_rule)}")

    r.note("\n2. the same attacker flagged again")
    repeats = [pe.execute_action("block_ip", BLOCK_IP, "PortScan", 0.99) for _ in range(5)]
    r.check("5 repeats all return already_active", all(o.get("already_active") for o in repeats))
    r.check("still exactly 2 rules (no duplicates)", fw.count(block_rule) == 2, f"found {fw.count(block_rule)}")

    r.note("\n3. real addresses are refused")
    for ip in REAL_IPS:
        o = pe.execute_action("block_ip", ip, "DDoS", 0.99)
        r.check(f"{ip} refused", o.get("executed") is False and "outside the allowed demo scope" in o.get("reason", ""),
                o.get("reason", "")[:70])
        r.check(f"no rule exists for {ip}", fw.count(pe._rule_name("block_ip", ip)) == 0)

    r.note(f"\n4. temporary rule removed by its timer (drop_connection, {SHORT_DURATIONS['drop_connection']} s)")
    temp_rule = pe._rule_name("drop_connection", TEMP_IP)
    o = pe.execute_action("drop_connection", TEMP_IP, "DoS slowloris", 0.99)
    r.check("added", o.get("executed") is True and fw.count(temp_rule) == 2, f"found {fw.count(temp_rule)}")
    gone = wait_until(lambda: fw.count(temp_rule) == 0, SHORT_DURATIONS["drop_connection"] + 10)
    r.check("removed on schedule", gone, f"found {fw.count(temp_rule)} after the timer")

    r.note("\n5. revoke with the kill switch OFF")
    pe.PREVENTION_EXECUTION_ENABLED = False
    o = pe.revoke_action("block_ip", BLOCK_IP)
    r.check("revoke reports revoked", o.get("revoked") is True, o.get("reason", ""))
    r.check("both rules removed", fw.count(block_rule) == 0, f"found {fw.count(block_rule)}")
    o = pe.revoke_action("block_ip", "8.8.8.8")
    r.check("revoke of a real address refused", o.get("revoked") is False, o.get("reason", "")[:70])

    r.note(f"\n6. restart recovery (rate_limit {SHORT_DURATIONS['rate_limit']} s + a persistent block)")
    pe.PREVENTION_EXECUTION_ENABLED = True
    rb_rule = pe._rule_name("block_ip", RESTART_BLOCK_IP)
    rt_rule = pe._rule_name("rate_limit", RESTART_TEMP_IP)
    pe.execute_action("block_ip", RESTART_BLOCK_IP, "DDoS", 0.99)
    pe.execute_action("rate_limit", RESTART_TEMP_IP, "DoS Hulk", 0.99)
    r.check("both added", fw.count(rb_rule) == 2 and fw.count(rt_rule) == 2)
    simulate_restart()
    swept = pe.sweep_expired_rules()
    r.check("startup sweep removes nothing still due", swept == [], str(swept))
    o = pe.execute_action("block_ip", RESTART_BLOCK_IP, "DDoS", 0.99)
    r.check("after restart, the persistent block is remembered (already_active)", o.get("already_active") is True)
    r.check("still exactly 2 rules", fw.count(rb_rule) == 2, f"found {fw.count(rb_rule)}")
    gone = wait_until(lambda: fw.count(rt_rule) == 0, SHORT_DURATIONS["rate_limit"] + 10)
    r.check("the restarted timer removed the rate_limit rule", gone, f"found {fw.count(rt_rule)}")
    o = pe.revoke_action("block_ip", RESTART_BLOCK_IP)
    r.check("persistent block revoked", o.get("revoked") is True and fw.count(rb_rule) == 0)

    r.note("\n7. kill switch OFF: nothing is added")
    pe.PREVENTION_EXECUTION_ENABLED = False
    o = pe.execute_action("block_ip", BLOCK_IP, "PortScan", 0.99)
    r.check("refused as disabled", o.get("executed") is False and "disabled" in o.get("reason", ""))
    r.check("no rule exists", fw.count(block_rule) == 0)


def main():
    parser = argparse.ArgumentParser(description="Live check of the prevention engine against the Windows Firewall")
    parser.add_argument("--simulate", action="store_true", help="in-memory firewall, no admin needed")
    parser.add_argument("--output", default=str(MODEL_DIR / "results" / "prevention_live_check.txt"))
    args = parser.parse_args()

    if args.simulate:
        fw = SimulatedFirewall()
    else:
        if platform.system() != "Windows":
            sys.exit("This check needs Windows (netsh advfirewall).")
        if not pe._is_admin():
            sys.exit("Not running as administrator. Open PowerShell with 'Run as administrator' and run this again.")
        fw = RealFirewall()
        leftovers = [n for n in ALL_RULES if fw.count(n)]
        if leftovers:
            sys.exit(f"Rules from an earlier run still exist: {leftovers}. Remove them first, e.g. "
                     f"netsh advfirewall firewall delete rule name={leftovers[0]}_in")

    pe.EXECUTION_LOG_PATH = Path(tempfile.mkdtemp()) / "live_check_log.jsonl"
    r = Report()
    r.note(f"Firewall : {fw.name}")
    r.note(f"Started  : {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    try:
        run(fw, r)
    except Exception as e:
        r.check("script finished without an error", False, repr(e))
    finally:
        pe.PREVENTION_EXECUTION_ENABLED = False
        simulate_restart()
        for name in ALL_RULES:
            pe._remove_block_rule(name)
        remaining = [n for n in ALL_RULES if fw.count(n)]
        r.note("")
        r.check("cleanup: no test rules left in the firewall", not remaining, str(remaining))

    total = sum(1 for line in r.lines if line.startswith(("PASS", "FAIL")))
    r.note(f"\n{total - r.failed}/{total} checks passed")

    header = [
        "=" * 70, "PREVENTION ENGINE - LIVE FIREWALL CHECK", "=" * 70,
        f"System   : {platform.platform()}",
        f"Python   : {platform.python_version()}",
        "Timers shortened for the check: " + ", ".join(f"{k} {v} s" for k, v in SHORT_DURATIONS.items()),
        "Targets  : TEST-NET only (" + ", ".join([BLOCK_IP, TEMP_IP, RESTART_BLOCK_IP, RESTART_TEMP_IP]) + ")",
        "",
    ]
    if not args.simulate:
        Path(args.output).write_text("\n".join(header + r.lines) + "\n", encoding="utf-8")
        print(f"\nWrote {args.output}")
    sys.exit(1 if r.failed else 0)


if __name__ == "__main__":
    main()
