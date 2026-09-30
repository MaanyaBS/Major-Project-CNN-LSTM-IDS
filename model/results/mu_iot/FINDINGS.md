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

## False alarms

The 9.3% false-alarm rate is a genuine model error, not a data artefact (98.6%
of normal test windows are unseen in training). Most of it is normal traffic
confused with Spyware (keylogger): quiet, low-volume exfiltration resembles
ordinary background traffic. Spyware recall is 0.764. Next step: SHAP analysis
of these confusions.

## Data-quality notes (for the report)

- `Botnet_Slowloris.csv` (MU_SESSION_005) and `Slowloris.csv` (MU_SESSION_022)
  are the same capture with different timestamps: ~60% of 022's sampled rows
  are identical to 005's (control: 0%). The two copies are aligned, so they
  do not leak between train and test (0.7%), but one recording is counted
  twice. This is a property of the MU-IoT dataset itself.
- MU_SESSION_002 (DNS amplification DDoS) is tiny (618 test windows) and
  scores 0% — too little data to learn.
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
