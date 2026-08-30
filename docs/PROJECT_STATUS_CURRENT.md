# Project Status — IDS → IPS, Current State

This supersedes the status sections of the earlier workflow doc, which was written
before the model was trained. If you're an LLM helping Person C and have no other
context on this project, read this file fully before touching any integration code.

---

## 1. What This Project Is, In One Paragraph

A CNN-LSTM intrusion detection system (IDS) on the CICIDS2017 dataset, extended
mid-project into a lightweight intrusion *prevention* system (IPS) at the guide's
request. "Prevention" here means recommended-action + simulated-prevention — a policy
engine that maps model predictions to actions/severity and produces a structured log,
not a real live-blocking system (that was explicitly scoped out as unrealistic for the
timeline). Three people: A (data), B (model — this doc's author), C (dashboard +
explainability).

---

## 2. Current Status Per Person

| Person | Status |
|---|---|
| **A — Data** | Done. Rebuilt the dataset with chronological (day-aware) ordering after discovering the dataset has no Timestamp column — used preserved row order within each of CICIDS2017's real 8 capture-day files as a verified time proxy, tagged with a `source_day` column. |
| **B — Model** | **Done as of tonight.** Real CNN-LSTM trained (three iterations, see Section 4), evaluated, verified byte-identical on reload, committed to the repo as real files (not just Drive). Handoff doc written. Prevention PoC built and run against both RF and CNN-LSTM predictions. |
| **C — Dashboard + Explainability** | Status of the Flask backend specifically unconfirmed as of this doc — last known state was frontend-only (React + Vite, already on GitHub). **This needs to be answered before dashboard integration planning proceeds.** |

---

## 3. The Model — What Exists and Where

All three files below are **committed to the repo**, in `model/artifacts/` — this is the
real, versioned source of truth, not the Drive copies used during training/experimentation:

- `model/artifacts/cnn_lstm_best_v2.keras` — trained model
- `model/artifacts/scaler_v2.pkl` — fitted `StandardScaler`
- `model/artifacts/label_mapping_v2.json` — `{label: int}` canonical class encoding

Full integration contract, including a working `predict()` code example, is in
`model/MODEL_INTERFACE.md` — **read that file in full before wiring anything up.**

**Honest performance:** accuracy 98.4%, weighted F1 0.986, **macro F1 only 0.586**.
Four classes (Bot, Web Attack - Brute Force, Web Attack - XSS, Web Attack - Sql
Injection) have poor-to-zero recall; Infiltration has zero test support. This mirrors
the RF baseline's own weakest classes, so it's treated as a real feature-level
limitation (these attacks are behaviorally/payload-distinguished, not captured by
flow-level statistics), not a training bug. **Do not present accuracy alone as "the"
number anywhere in the dashboard or report.**

---

## 4. Why There Are Three Model Versions (v1/v2/v3) — Skip Unless You Need the History

Only `v2` matters for integration. Context for the report/write-up only:
- v1: uniform heavy class weighting (capped at 50×) — fixed nothing, caused BENIGN to
  flood false-positives into rare classes
- v2: uniform dampened weighting (sqrt of balanced weights) — the actual chosen model.
  Fixed most classes well, but Bot/Brute Force/XSS remained weak
- v3: targeted 3× boost on just those three weak classes — made things *worse* across
  the board (macro F1 dropped), confirming the problem isn't weighting, it's the
  feature set itself

---

## 5. The Prevention (IPS) Layer — Not Mentioned in the Model Handoff Message, Important

This is a separate, already-working system, independent of which detection model is used:

- `model/class_action_mapping.py` — a policy table (`CLASS_ACTION_MAP`) mapping each of
  the 15 classes to a recommended `action`, `severity`, and confidence `threshold`.
  Thresholds are calibrated per-class based on that class's real reliability (currently
  calibrated against RF's F1 scores — **not yet recalibrated for CNN-LSTM's different
  reliability profile, a known open item**). Sql Injection is hard-locked to
  `held_for_review` regardless of confidence (`threshold: float('inf')`) — too few
  samples (~21 total) to trust any confidence score at all.
- `model/prevention_simulation.py` — takes a CSV of `predicted_class, confidence,
  true_class` and produces a log with `action`, `severity`, `status`
  (`auto_action` / `held_for_review` / `no_action_needed`) per row.
- **Two real prediction logs already exist** as reference/example output:
  - RF-based (531,012 rows): 440,246 no_action / 90,142 auto_action / 624 held_for_review
  - CNN-LSTM v2-based (530,951 rows): 436,676 no_action / 89,737 auto_action / 4,538
    held_for_review (higher held_for_review count than RF's run — expected, since
    thresholds are currently RF-calibrated, not CNN-LSTM-calibrated; see open item above)

**Not yet built:** the "replay as live feed" layer — replaying a static prevention log
with a small per-row delay so it looks live for demo purposes. This is dashboard-facing
work and its ownership (B builds the replay mechanism, or C builds it as part of the
dashboard, or it's split) hasn't been decided — **worth resolving directly with B, not
assumed either way.**

---

## 6. Open, Undecided Items (Do Not Silently Resolve These)

1. **Does C's pipeline actually produce the 20 CICFlowMeter-style flow features** the
   model was trained on (packet lengths, IATs, byte counts, etc.)? If not, there's a
   whole feature-extraction step that doesn't exist yet. This is the single biggest
   unknown blocking real integration.
2. ~~Day-boundary / sequence-gap handling in live inference~~ — **resolved**. The
   live-feed replay loads a complete CSV upfront and serves windows from it in order
   (not a genuine continuous live-sensor capture), so a mid-stream connection gap can't
   occur in the system as built. See `MODEL_INTERFACE.md` Section 7. Would need
   revisiting only if a true live-sensor-capture mode is added later.
3. **Prevention policy thresholds are RF-calibrated, not CNN-LSTM-calibrated** — a
   real recalibration pass against CNN-LSTM's actual per-class F1 scores hasn't been
   done. Flagged, not urgent.
4. **Live-feed replay layer ownership** — not built, not assigned.
5. **Flask backend completeness** — unconfirmed as of this document.

---

## 7. Practical Integration Gotchas

- The model/scaler were built with TensorFlow 2.21.0 and scikit-learn 1.9.0. A pickled
  scaler can throw version warnings or fail under a different sklearn version —
  test-load all three artifact files in the actual backend environment early.
- `MODEL_INTERFACE.md`'s code example uses relative paths (`model/artifacts/...`) that
  only resolve if the process's working directory is the repo root — resolve relative
  to the script/project root instead of assuming CWD.
- `predict()` assumes flow rows arrive as dicts keyed by the 20 feature names — confirm
  this matches your actual data format before assuming it works as-is.
