# MU-IoT CNN-LSTM — Results and Findings

Model: CNN-LSTM (same architecture as the CICIDS2017 model), 20-row windows,
38 flow features (FPT/LPT timestamps excluded), 7 classes. Trained in Colab on
the `handoff_v3` package (3.94M rows). Early stopping chose epoch 7 of 12.
Script: `model/train_cnn_lstm_mu_iot.py`.

## Headline numbers (report these)

Scored only on test windows whose exact 20-row sequence never appears in
training, so memorised duplicates can't inflate them
(`mu_iot_unseen_only_rescore.txt`).

| Track | What it measures | Accuracy | Macro F1 |
|---|---|---|---|
| test_within | later traffic from recordings seen in training | 0.964 | 0.936 |
| test_heldout | four recordings never seen in training | 0.680 | 0.676 |

- Normal traffic flagged as attack (false-alarm rate): **9.3%**.
- Attacks classified as normal, on unseen recordings: **0.08%**. The model
  almost never misses an attack; its held-out errors are about naming the
  attack type.

## Why the held-out score is lower

Held-out accuracy depends on whether that *kind* of attack was in training:

| Held-out recording | Attack | Similar attack in training? | Recall |
|---|---|---|---|
| MU_SESSION_013 | Dictionary attack (MQTT) | yes — dictionary attacks on 5 other protocols | 0.998 |
| MU_SESSION_026 | XSS injection | yes — another XSS recording | 0.882 |
| MU_SESSION_021 | Vulnerability scan | no — training has only recon scans | 0.441 |
| MU_SESSION_031 | hping3 UDP flood | no — training UDP floods use other tools | 0.406 |

Unseen variants get mapped to the nearest familiar class: vulnerability scans
look like brute force (Password_Hacking), and hping3 floods hit random ports,
which looks like a port scan.

## Single flow records are ambiguous; sequences are not

With timestamps removed, identical flow records repeat heavily — and often
under different labels. Share of test items that appear in training with a
*different* label:

| Class | Single rows | 20-row windows |
|---|---|---|
| Scan (test_within) | 71.8% | 0.0% |
| normal (test_within) | 44.8% | 0.5% |
| Spyware (test_within) | 40.9% | 0.1% |
| DDoS (test_heldout) | 89.8% | 21.0% |

A single flow often cannot identify the attack; a sequence of 20 almost always
can. This is direct evidence for the sequence-based (CNN-LSTM) design.

## Baseline: single-row random forest vs the CNN-LSTM

The same random forest as the CICIDS2017 baseline (100 trees, seed 42),
trained on all 2,171,995 training rows and scored on the last row of each
CNN-LSTM test window: identical examples and labels
(`mu_iot_random_forest_results.txt`, `model/baseline_mu_iot_rf.py`). The
CNN-LSTM reproduced its committed scores in the same run, and the unseen-only
counts matched the committed re-score exactly.

| Unseen-only windows | Random forest | CNN-LSTM |
|---|---|---|
| test_within accuracy / macro F1 | 0.904 / 0.816 | 0.964 / 0.936 |
| test_heldout accuracy / macro F1 | 0.407 / 0.404 | 0.680 / 0.676 |
| Normal flagged as attack (within) | 17.2% | 9.3% |
| Attacks called normal (held-out) | 2.5% | 0.09% |

- **Here the sequence model earns its place**, unlike on CICIDS2017, where a
  single-flow random forest beats it (`../chronological_random_forest_results.txt`).
  This matches the ambiguity finding above: MU-IoT single rows repeat under
  different labels, so a single-row model cannot separate them.
- The gap is largest where it matters: on unseen recordings (macro F1 0.68 vs
  0.40), on normal traffic (half the false alarms), and on Spyware (F1 0.75
  vs 0.26).
- Per held-out recording, the forest is better only on the vulnerability scan
  (0.50 vs 0.45 accuracy); it gets almost none of the hping3 flood right
  (0.0002 vs 0.32) and only 36% of the dictionary attack (CNN-LSTM 99.8%).

## False alarms

The 9.3% false-alarm rate is a genuine model error, not a data artefact (98.6%
of normal test windows are unseen in training). Most of it is normal traffic
confused with Spyware (keylogger): quiet, low-volume exfiltration resembles
ordinary background traffic. Spyware recall is 0.764. The SHAP section below
shows why.

## What the prevention policy would do

Every test window run through `get_action(..., dataset="mu_iot")` and compared
with its true label (`prevention_policy_mu_iot.txt`). Measured only; the
thresholds were not tuned on these results.

| Track | Normal windows auto-blocked | Attacks handled automatically | Attacks sent to review | Attacks missed |
|---|---|---|---|---|
| test_within | 1.60% (1,352 of 84,729) | 94.06% | 4.44% | 1.50% |
| test_heldout | no normal traffic | 94.43% | 5.48% | 0.08% |

- **False blocks on normal traffic: 1.60%**, five times the CICIDS2017 rate
  (0.33%). Most come from Injection predictions (885 of 1,352), the class with
  the lowest threshold (0.63). This rests on a single normal recording. It is
  the policy's main remaining risk.
- **Misnamed attacks are still blocked.** On held-out recordings, 35% of
  automatic actions name a different attack than the true one, but every
  automatic MU-IoT action is `block_ip`, so the source is blocked either way.
- Spyware: 76.4% of its windows go to review, 23.6% are called normal.
  MiTM: 98.6% go to review.

## SHAP: why the three main errors happen

`mu_iot_shap_report.txt`, charts `mu_iot_shap_*.png`. Up to 200 windows per
group; expected gradients (the `shap.GradientExplainer` estimator) with 500
samples per window and a background of 350 real training windows.

Checks: agreement with `shap.GradientExplainer` on the same windows, r = 0.990
(feature profiles); each group's mean SHAP sum is within 0.04 of its mean
output gap. Single-window explanations of the hping3 group are noisier
(mean per-window error 0.35), so only its group averages are used.

Each error group is compared with correctly classified windows by the cosine
similarity of their mean SHAP profiles (1 = same features, same direction):

| Error | Similarity to the predicted class's real detections | Similarity to the true class's detections | Cause |
|---|---|---|---|
| normal → Spyware | 0.87 | 0.29 (correct normal) | Systematic resemblance |
| hping3 flood → Scan | 0.59 | −0.64 (training floods) | Real resemblance to scans |
| vulnerability scan → Password_Hacking | 0.20 | −0.05 (scans) | Extrapolation beyond training values |

- **normal → Spyware.** The same five features push both the false alarms and
  real Spyware toward Spyware: DNS_RCUL, TCPWS_Mode, FAMax, DNSQTL and FD. The
  false alarms are confident (mean P(Spyware) 0.756, real Spyware 0.927), so no
  threshold separates them cleanly. This supports keeping Spyware in review.
- **hping3 flood → Scan.** Its packets resemble scans, not the floods in
  training: PLM and FH_M around 64 (scans 60, training floods 74), and FAMean
  near zero like scans (training floods 0.017). The fix is training data
  with more flood tools. For prevention it is harmless: both classes block.
- **vulnerability scan → Password_Hacking.** One feature dominates:
  TCPWS_Mean (+0.36, three times any other). Its median here is about 25,000,
  against 3,900 for Password_Hacking and 3,500 for Scan. The model is
  extrapolating on values it never saw, not recognising password hacking. An
  out-of-range check on inputs could route such windows to review.

SHAP describes what the model relies on, not what causes the traffic to
differ. Feature names are the dataset's abbreviations; TCPWS_* is read as TCP
window size from its name and values (near zero for UDP floods, about 2,000
for TCP scans). Exact definitions are in the MU-IoT paper.

## Data-quality notes (for the report)

- `Botnet_Slowloris.csv` (MU_SESSION_005) and `Slowloris.csv` (MU_SESSION_022)
  are byte-identical files: a full comparison of the raw CSVs matches exactly
  (150,577 rows each; `docs/report/person_a_report.md`, 12.1). One recording
  is therefore counted twice, as two sessions. The two copies were split the
  same way, so they do not leak between train and test (0.7% overlap), and
  their test results are identical (22,530 windows, 0.932 accuracy each).
  This is a property of the MU-IoT dataset itself. (An earlier version of
  this note said "different timestamps"; the raw-file comparison corrects it.)
- MU_SESSION_002 (DNS amplification DDoS) is tiny (4,243 raw rows, 618 test
  windows) and scores 0% — too little data to learn.
- Normal and Spyware each come from a single recording, so their test scores
  come from the same recording as their training data (optimistic).
- FPT/LPT (flow timestamps) were removed as model inputs: each file has its own
  time range and each recording is a single class, so timestamps would reveal
  the answer.

## Files

- `mu_iot_test_within_results.txt`, `mu_iot_test_heldout_results.txt` — full
  reports (per-class, per-recording, confusion matrices), all windows.
- `mu_iot_unseen_only_rescore.txt` — the headline numbers above.
- `mu_iot_metrics.json` — machine-readable metrics.
- `training_history.json` — per-epoch loss and validation scores.
- `prevention_policy_mu_iot.txt` / `.json` — the policy's decisions on every
  test window (`model/evaluate_prevention_policy.py --dataset mu_iot`).
- `mu_iot_shap_report.txt`, `mu_iot_shap_values.json`, `mu_iot_shap_*.png` —
  the SHAP analysis (`model/explain_mu_iot.py`).
- `mu_iot_random_forest_results.txt` / `.json` — the single-row random forest
  baseline on identical examples (`model/baseline_mu_iot_rf.py`).
