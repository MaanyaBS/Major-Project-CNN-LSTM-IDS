# Real Prevention Execution — Handoff for Backend Integration (Person C)

This document covers `model/prevention_executor.py` — the piece that turns a
prevention *recommendation* (`class_action_mapping.py`'s `get_action()`) into
a real, executable action, for the classes where the model is confident
enough to trust automatically. Read this before wiring it into `app.py`.

---

## 1. What This Actually Is

Previously, `auto_action` was just a status label — the dashboard would say
"this would be auto-executed" but nothing was ever really executed.
`prevention_executor.py` closes that gap for a real, safely-scoped subset of
actions: it actually adds/removes Windows Firewall rules via `netsh
advfirewall`.

**This is explicitly scoped to a controlled demo environment, not open
execution on arbitrary real traffic.** See Section 2 — this is enforced in
code, not just a policy statement.

---

## 2. The Safety Boundary (enforced before any real action, three layers)

1. **Global kill switch** — `PREVENTION_EXECUTION_ENABLED`, defaults to
   `False`. Real execution is opt-in; nothing executes unless this is
   explicitly flipped on.
2. **Scope allow-list** — the target IP must fall inside one of the RFC 5737
   "TEST-NET" ranges (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) —
   ranges permanently reserved for documentation/testing, guaranteed to never
   route on the real internet. Real execution can never reach a real
   destination, by construction.
3. **Explicit deny-list** — loopback/broadcast/unspecified addresses are
   always refused, defense in depth even if a bug got them past the
   allow-list.

An admin-privilege check also runs before any `netsh` call — if the process
isn't elevated, it fails with a clear, logged reason instead of silently
doing nothing.

---

## 3. Which Actions Are Real, and Which Aren't

| Action | Real? | Persistence |
|---|---|---|
| `block_ip` | Yes | Persistent — stays blocked until `revoke_action()` |
| `isolate_host` | Yes (same underlying mechanism as `block_ip`) | Persistent |
| `drop_connection` | Yes | Auto-expires after 60s |
| `rate_limit` | **Partially** — see note below | Auto-expires after 120s |
| `sanitize_input` (XSS) | **No — stays simulated/log-only, deliberately** | — |

**`rate_limit` honesty note:** this is implemented as a *temporary full
block*, not true bandwidth throttling. Real QoS-based rate limiting on
Windows requires `netsh` QoS policy objects — a materially larger, separate
piece of work, out of scope here. State this explicitly in the report; it's
a deliberate simplification, not a hidden gap.

**`sanitize_input` stays simulated on purpose:** it's an application-layer
concept (escaping request content), which a network-level IDS/IPS
structurally cannot do. Keeping this one recommendation-only is the correct
call, not a shortcut — say so explicitly in the report too.

Three classes (Sql Injection, Heartbleed, Infiltration) are hard-locked to
`held_for_review` in `class_action_mapping.py` regardless of confidence, so
they will never reach `auto_action` and never trigger real execution at all
— that's correct, unrelated to this module.

---

## 4. API

```python
import sys
sys.path.insert(0, "model")  # or however your backend already imports model/
import prevention_executor as pe

# Real execution is off by default - flip it on explicitly (e.g. in your
# backend's config/startup, not hardcoded here)
pe.PREVENTION_EXECUTION_ENABLED = True

# Call this once whenever a prediction resolves to auto_action:
result = pe.execute_action(
    action=prevention["action"],          # e.g. "block_ip", from get_action()
    target_ip=source_ip,                  # from the Section 1.1 CSV schema extension
    predicted_class=predicted_class,
    confidence=confidence,
)
# result = {"executed": True/False, "reason": "..." (if False),
#           "rule_name": "..." (if True), "auto_expires_in_seconds": int|None}

# To manually lift a persistent action (block_ip/isolate_host) after human review:
pe.revoke_action(action="block_ip", target_ip=source_ip)

# Call this ONCE at backend startup, alongside service.load() in initialize():
pe.sweep_expired_rules()
```

**Why the startup sweep matters:** the auto-expiry timer lives inside the
process that called `execute_action()`. If the backend process crashes or
restarts before a temporary rule's timer fires, that rule would otherwise be
orphaned. `sweep_expired_rules()` catches and cleans up exactly that case —
call it once during `initialize()`, before serving any predictions.

`execute_action()` never raises — it always returns a dict, so it's safe to
call directly from a request handler without wrapping every call site in a
`try/except`.

---

## 5. Verified, Not Assumed

- All safety-refusal paths tested: disabled switch, real-world IP, deny-list
  addresses, malformed input, unknown action type — all correctly refused
  and logged with a clear reason.
- Real execution tested end-to-end in an elevated terminal: rule genuinely
  created (confirmed via `netsh advfirewall firewall show rule`), then
  genuinely auto-removed after its duration elapsed, process kept alive
  throughout to properly exercise the timer.
- `sweep_expired_rules()` tested against 4 synthetic scenarios (expired /
  not-yet-expired / persistent / already-revoked) — correct in all four, and
  confirmed idempotent (safe to call repeatedly).

Every attempt — refused, failed, or genuinely executed — is logged to
`model/results/prevention_execution_log.jsonl`, kept separate from the
existing recommendation log so "recommended" and "actually executed" are
never conflated in the data or in the report.

---

## 6. What's Left for Integration (Task 1.4)

1. Extend `/api/predict_csv` and `/api/stream/load` to accept an optional
   Source IP column (Task 1.1 — may already be done on your side).
2. Call `pe.sweep_expired_rules()` once in `initialize()`.
3. In the prediction path, when `prevention["status"] == "auto_action"` and a
   Source IP is available, call `pe.execute_action(...)` and surface the
   result distinctly in the API response / dashboard UI — "recommended:
   block_ip" vs "executed: real firewall rule added" are different claims
   and should look different to the viewer.
4. Decide and expose how `PREVENTION_EXECUTION_ENABLED` gets toggled (env
   var recommended, not a hardcoded `True`) — it should default off in
   normal operation and only be on deliberately for a demo.
