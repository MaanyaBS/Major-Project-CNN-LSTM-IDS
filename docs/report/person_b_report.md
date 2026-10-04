# Ruthwik Sai Ganesh — Model, Evaluation, Explainability Analysis and Prevention

Report sections for the model side of the project. Every number below comes
from a committed results file; Section 10 lists them and the commands that
regenerate them.

---

## 1. Role and Scope

I designed, trained and evaluated the CNN-LSTM models on CICIDS2017 and
MU-IoT, built the fair baselines they are compared against, analysed the
MU-IoT model's errors with SHAP, measured inference speed, and designed the
prevention layer: a per-class policy and a safety-bounded execution engine,
with automated tests. Data preparation (Maanya B S) and the dashboard and
backend (Varshini D N) are described in their own sections.

---

## 2. Model Architecture

The same hybrid architecture is used for both datasets: convolution layers
learn local patterns across neighbouring flows, and an LSTM summarises how
they develop across the window.

| Layer | CICIDS2017 model | MU-IoT model |
|---|---|---|
| Input | 10 flows × 20 features | 20 flows × 38 features |
| Conv1D, 64 filters, kernel 3, ReLU, no padding → BatchNorm → MaxPool(2) | yes | yes |
| Conv1D, 128 filters, kernel 3, ReLU, same padding → BatchNorm → MaxPool(2) | yes | yes |
| LSTM, 64 units | yes | yes |
| Dense, 64, ReLU | yes | yes |
| Dense softmax | 15 classes | 7 classes |
| Parameters | 83,919 | 86,855 |
| Precision | float32 | mixed float16 (output float32) |

Both use Adam and sparse categorical cross-entropy, and neither uses
dropout. The deployed CICIDS2017 model was checked layer by layer against
`model/cnn_lstm_architecture.py` and `model/train_cnn_lstm.py`: with its
weights loaded, both definitions give identical predictions.

---

## 3. Data Splits and Leakage Control

The evaluation design matters more than the architecture: a careless split
measures memory, not detection.

### 3.1 CICIDS2017

CICIDS2017 was captured over five working days, and neighbouring flows are
often near-identical, so a random split places near-copies on both sides.
`model/rebuild_chronological_split.py` splits chronologically within each
(capture day, class) group: the first 80% of rows train, the rest test. A
pure day-level split was rejected because it dropped 8 of 15 classes from
the test set. Ten-flow windows never span two capture days, and the scaler
is fitted on training rows only. The test set has 530,951 windows.

### 3.2 MU-IoT

- **No timestamps.** The flow timestamps FPT and LPT were removed: each
  recording holds one class and its own time range, so timestamps would
  reveal the label.
- **Windows respect the data.** 20-row windows never cross a recording
  block, a split, or a gap in the original row ids
  (`model/train_cnn_lstm_mu_iot.py`, 8 tests in `test_mu_iot_windows.py`).
- **Two test tracks.** *test_within* is later traffic from recordings used
  in training. *test_heldout* is four whole recordings never seen in
  training: an hping3 UDP flood (DDoS), a vulnerability scan (Scan), an MQTT
  dictionary attack (Password_Hacking) and an XSS attack (Injection).
- **Unseen-only re-score.** Headline numbers count only test windows whose
  exact 20-row sequence never appears in training, so memorised duplicates
  cannot inflate them.

---

## 4. Training

**CICIDS2017.** Benign traffic is 83% of the test set, so three
class-weighting schemes were trained with the same architecture and scored
on the same test set (`model/results/cnn_lstm_versions_comparison.txt`):

| Version | Class weights | Test accuracy | Macro F1 |
|---|---|---|---|
| v1 | balanced, capped at 50 | 0.8831 | 0.4276 |
| **v2 (deployed)** | **square root of balanced, no cap** | **0.9842** | **0.5857** |
| v3 | 3× boost on the three weakest classes | 0.9470 | 0.4811 |

v1's capped weights pushed benign traffic into rare classes, and v3's
targeted boost made the overall result worse. v2 trained with a 10%
stratified validation split, batch 512 and early stopping on validation
loss (patience 5). Its lowest validation loss came in the first epoch
(0.153, validation accuracy 0.954); training stopped after epoch 6 and
restored the epoch-1 weights (`cnn_lstm_v2_training_curves.png`).
`model/train_cnn_lstm.py` reproduces these settings by default
(`--class-weights sqrt`), from the original training cell
(`notebooks/v2_training_cells.txt`); a GPU retrain gives a close, not
bit-identical, model. v3's training code was not preserved.

**MU-IoT.** Each epoch draws a fresh sample of up to 300,000 training
windows per class, with square-root-balanced class weights capped at 10.
Batch 512, mixed precision on a Colab T4, checkpoints written every epoch
so a disconnect loses at most one epoch. Early stopping on validation loss
(patience 5) stopped at epoch 12 and kept epoch 7.

---

## 5. Results

### 5.1 CICIDS2017

To judge the CNN-LSTM fairly, a random forest (100 trees, seed 42) was
trained on single flows with the same 20 features, on exactly the same
chronological split (built by the same code), and scored on the last flow of
each CNN-LSTM test window: identical examples and labels.

| Model, 530,951 identical examples | Accuracy | Weighted F1 | Macro F1 |
|---|---|---|---|
| CNN-LSTM (10-flow windows) | 0.9842 | 0.9864 | 0.5857 |
| Random forest (single flows) | 0.9911 | 0.9908 | 0.7803 |

| Class | Test windows | CNN-LSTM F1 | Random forest F1 |
|---|---|---|---|
| BENIGN | 439,987 | 0.991 | 0.997 |
| DoS Hulk | 35,038 | **0.990** | 0.953 |
| DDoS | 25,595 | 0.990 | 0.998 |
| PortScan | 23,378 | 0.971 | 0.967 |
| DoS GoldenEye | 2,058 | 0.816 | 0.988 |
| FTP-Patator | 1,219 | 0.773 | 0.994 |
| DoS slowloris | 1,083 | 0.725 | 0.842 |
| DoS Slowhttptest | 1,046 | 0.886 | 0.900 |
| SSH-Patator | 739 | 0.656 | 0.945 |
| Bot | 381 | 0.056 | 0.031 |
| Web Attack - Brute Force | 288 | 0.125 | 0.688 |
| Web Attack - XSS | 131 | 0.006 | 0.336 |
| Web Attack - Sql Injection | 5 | 0.000 | 0.286 |
| Heartbleed | 3 | 0.800 | 1.000 |
| Infiltration | 0 | — | — |

- **On CICIDS2017 the single-flow random forest is the better model.** The
  CNN-LSTM is clearly ahead only on DoS Hulk.
- **Bot is a feature or data limit:** both models fail.
- **The web attacks are a CNN-LSTM limit:** with the same features the
  forest reaches F1 0.69 on brute force, so the signal exists in single
  flows and the CNN-LSTM's windows or training lose it. Why has not been
  tested.
- Heartbleed (3 windows) and SQL injection (5) are too small to measure;
  Infiltration has no test windows, because all its test rows fall in the
  first 9 rows of a day.
- An earlier random-split baseline gave the forest 0.834 macro F1; on the
  chronological split it is 0.786 (all test rows).

### 5.2 MU-IoT

The same random forest, trained on all 2,171,995 single training rows and
scored on the last row of each CNN-LSTM test window. In the same run, the
CNN-LSTM reproduced its committed scores and the unseen-only counts matched
the committed re-score exactly.

| Unseen-only windows | CNN-LSTM | Random forest |
|---|---|---|
| test_within: accuracy / macro F1 (528,967 windows) | **0.964 / 0.936** | 0.904 / 0.816 |
| test_heldout: accuracy / macro F1 (686,566 windows) | **0.680 / 0.676** | 0.407 / 0.404 |
| Normal traffic flagged as attack (within) | **9.3%** | 17.2% |
| Held-out attacks called normal | **0.09%** | 2.5% |

| Held-out recording | CNN-LSTM accuracy | Random forest accuracy |
|---|---|---|
| MQTT dictionary attack (Password_Hacking) | **0.998** | 0.361 |
| XSS (Injection) | **0.882** | 0.839 |
| Vulnerability scan (Scan) | 0.446 | **0.495** |
| hping3 UDP flood (DDoS) | **0.321** | 0.000 |

All windows; within-track per-class F1, CNN-LSTM vs forest: DDoS 0.980 vs
0.928, Injection 0.978 vs 0.958, MiTM 0.963 vs 0.862, Password_Hacking
0.990 vs 0.955, Scan 0.994 vs 0.949, Spyware 0.747 vs 0.259, normal 0.909
vs 0.789.

- **On MU-IoT the CNN-LSTM is clearly better,** most of all on recordings
  it never saw.
- It almost never misses an attack; its held-out errors are about naming
  the attack. Unfamiliar tools are mapped to the nearest familiar class: the
  hping3 flood is called Scan in 68% of its windows.
- The main weakness is false alarms on normal traffic (9.3%), mostly
  predicted as Spyware.

### 5.3 When Sequences Help

With timestamps removed, identical MU-IoT flow records often appear under
different labels: 71.8% of single Scan test records also appear in training
with another label, against 0.0% of 20-row Scan windows. A single-row model
cannot separate such records; a sequence model can. On CICIDS2017, single
flows are distinctive enough that a random forest does better. The evidence
therefore supports the CNN-LSTM where traffic is ambiguous at the level of
single flows, as in the IoT data, not as a universal improvement.

---

## 6. Explainability Analysis (MU-IoT)

The dashboard shows SHAP explanations per prediction (Varshini's section).
I used SHAP to explain the MU-IoT model's three main error patterns
(`model/explain_mu_iot.py`).

- **Method.** Expected gradients, the estimator behind
  `shap.GradientExplainer`, computed in large batches; 500 samples per
  window; a background of 350 real training windows (50 per class); up to
  200 windows per group.
- **Validation.** Against `shap.GradientExplainer` on the same windows the
  feature profiles correlate at r = 0.990. In every group the mean SHAP sum
  matches the mean output gap to within 0.04 (additivity).
- **Comparison.** Each error group's mean SHAP profile is compared with
  correctly classified groups by cosine similarity.

| Error | Similar to the predicted class's real detections | Similar to the true class's detections | Cause |
|---|---|---|---|
| normal → Spyware | 0.87 | 0.29 | Systematic resemblance |
| hping3 flood → Scan | 0.59 | −0.64 | Real resemblance to scans |
| vulnerability scan → Password_Hacking | 0.20 | −0.05 | Extrapolation |

- **normal → Spyware.** The same five features push both the false alarms
  and real Spyware toward Spyware (DNS_RCUL, TCPWS_Mode, FAMax, DNSQTL, FD),
  and the false alarms are confident (mean probability 0.76). No threshold
  separates them, which is why Spyware is locked to human review.
- **hping3 flood → Scan.** Its packet sizes (about 64) and near-zero FAMean
  match scans (60), not the training floods (74, FAMean 0.017): a gap in
  training coverage.
- **vulnerability scan → Password_Hacking.** One feature dominates:
  TCPWS_Mean, with a median around 25,000 against about 3,900 and 3,500 in
  the two classes. The model is extrapolating beyond its training range.

---

## 7. Prevention Layer

### 7.1 Policy

`model/class_action_mapping.py` maps each class to an action, a severity and
a confidence threshold. Thresholds rise as a class's F1 falls (DDoS acts at
0.55 on CICIDS2017; SSH-Patator at 0.78). The MU-IoT policy reads its
thresholds off the same F1 → threshold curve, using held-out-recording F1
only (Injection 0.63, Password_Hacking 0.71, DDoS and Scan 0.84). Classes
are locked to human review when their evidence is too weak:

- CICIDS2017: Sql Injection, Heartbleed and Infiltration (too few test
  examples); Bot, Brute Force and XSS (F1 below 0.15).
- MU-IoT: MiTM and Spyware (no held-out recording).

`get_action(cls, conf, dataset=...)` keeps the two policies apart (both
datasets have a `DDoS` class) and rejects an unknown dataset.

### 7.2 Execution Engine

`model/prevention_executor.py` turns an approved action into Windows Firewall
rules through `netsh`, behind independent checks:

1. a global kill switch, off by default;
2. an allow-list of RFC 5737 TEST-NET ranges, so no real address can be
   touched;
3. a deny-list (loopback, broadcast, unspecified) and an administrator check.

Each rule is added once per target, however many windows flag it (500
windows from one IP give 1 rule). Temporary actions expire on a timer; on
startup, a sweep removes rules a crash left behind, restarts timers that are
not yet due and remembers rules still in force. Revoking works with the kill
switch off, so an action can always be undone, but only for TEST-NET targets.
Every attempt is logged. Rate limiting is approximated by a
temporary block; input sanitisation for XSS stays recommendation-only.

### 7.3 Verification

- **31 automated tests** (`model/test_prevention.py`) cover both policies,
  one rule per target, revoking, restart recovery and every refusal path, including adversarial targets such as
  `192.0.2.10,8.8.8.8` (netsh list syntax), CIDR ranges, IPv6 and
  non-string input. They never call the real firewall.
- **Mutation check:** the code was broken deliberately in 26 ways (kill
  switch removed, allow-list removed, a locked class unlocked, the dataset
  argument ignored, duplicate rules allowed, a stale timer allowed to remove
  a newer rule, and so on); a test failed every time.
- **End-to-end:** a real rule was created and removed on schedule in an
  elevated terminal.
- Writing the tests found three engine bugs, all fixed: revocations were
  logged without the rule name, timer expiry was not logged, and non-string
  targets were not explicitly refused. Integration with the backend found two
  more, also fixed: the same rule was added once per flagged window, and a
  revoke was refused whenever the kill switch was off.

### 7.4 Measured Effect

Every test window was run through the policy and the decision compared with
its true label (`model/evaluate_prevention_policy.py`):

| | Benign windows auto-actioned | Attacks handled automatically | Attacks missed |
|---|---|---|---|
| CICIDS2017 | 0.33% | 96.6% | 2.4% |
| MU-IoT, within recordings | 1.6% (mostly Injection) | 94.1% | 1.5% |
| MU-IoT, held-out recordings | no normal traffic | 94.4% | 0.08% |

- The measurement changed the policy: before the lock, all 17 automatic Bot
  actions on CICIDS2017 hit benign traffic.
- On MU-IoT, a misnamed attack is still blocked, because every automatic
  MU-IoT action is `block_ip`.
- The MU-IoT false-block rate on normal traffic (1.6%, five times CICIDS2017)
  is the policy's main remaining risk.
- The thresholds come from test-set F1; no separate calibration set exists,
  so these figures describe the policy rather than validate it independently.

---

## 8. Inference Speed

On a Ryzen 3 5300U laptop CPU, plugged in
(`model/results/inference_benchmark.txt`):

| | CICIDS2017 model | MU-IoT model |
|---|---|---|
| One window, `model.predict_on_batch` | 1.48 ms | 1.60 ms |
| One window, `model.predict` | 67 ms | 66 ms |
| Batches of 2048 windows | ~70,700 windows/s | ~21,900 windows/s |

`model.predict` adds about 65 ms of fixed overhead per call. The backend's
live replay currently calls it once per window; switching to
`predict_on_batch` makes that path about 40 times faster with identical
predictions. The MU-IoT model runs in mixed precision as trained; a float32
copy was 1.6× faster in batches but disagreed on 13 of 16,384 windows, so
the evaluated model was kept.

---

## 9. Limitations

- On CICIDS2017 a single-flow random forest outperforms the CNN-LSTM; the
  CNN-LSTM loses web-attack signal that single flows carry.
- Generalisation to unseen attack tools is weak (held-out macro F1 0.68).
- Normal traffic in MU-IoT comes from one recording, as does Spyware, so
  their scores are optimistic.
- Prevention runs only against TEST-NET addresses; thresholds are calibrated
  on test-set F1.
- The live feed replays recorded traffic; nothing is captured from a network.
- The deployed CICIDS2017 model kept its first-epoch weights; longer or
  slower training has not been explored.

---

## 10. Reproducing the Results

| Result | File | Command |
|---|---|---|
| CICIDS2017 evaluation | `model/results/cnn_lstm_v2_full_test_results.txt` | `python model/evaluate_model.py` |
| CICIDS2017 baseline | `model/results/chronological_random_forest_results.txt` | `python model/baseline_chronological_rf.py --source … --label-mapping … --sequences-dir …` (Colab) |
| MU-IoT training and evaluation | `model/results/mu_iot/` | `python model/train_cnn_lstm_mu_iot.py --data-dir … --out-dir … --resume` (Colab) |
| MU-IoT baseline | `model/results/mu_iot/mu_iot_random_forest_results.txt` | `python model/baseline_mu_iot_rf.py --data-dir …` (Colab) |
| SHAP analysis | `model/results/mu_iot/mu_iot_shap_report.txt` | `python model/explain_mu_iot.py --data-dir …` (Colab) |
| Policy outcomes | `model/results/prevention_policy_*.txt` | `python model/evaluate_prevention_policy.py --dataset cicids2017` (MU-IoT in Colab) |
| Speed | `model/results/inference_benchmark.txt` | `python model/benchmark_inference.py` |
| Tests | — | `python model/test_prevention.py`, `python model/test_mu_iot_windows.py` |
