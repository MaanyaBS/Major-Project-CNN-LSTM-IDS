# 6 | Implementation, Testing and Results

This chapter describes how the system was implemented (Section 6.1) and tested (Section 6.2), reports all results (Section 6.3), discusses them (Section 6.4) and states the limitations of the work (Section 6.5). Every number in this chapter comes from a results file in the project repository; the files are named where the results are reported.

## 6.1 Implementation

### 6.1.1 Code Organisation

The project is kept in one Git repository shared by the three team members, with one branch per member and pull requests to merge finished work into the main branch. Data scripts are in `src/`, the model, evaluation, prevention and extractor code in `model/` (trained artifacts in `model/artifacts/`, every reported result in `model/results/`), the backend in `backend/` and the dashboard in `frontend/`. Two interface documents fix the contract between the members' work: the model interface states the order of the 20 features, the scaling, the window length and the label mapping, and the prevention interface states which actions exist and which checks the engine performs, so the model and the engine could change internally without breaking the dashboard.

### 6.1.2 Dashboard

The dashboard has a home page, an analysis console and an about page. The analysis console offers batch analysis and a live feed. In batch analysis (Fig. 6.1) the analyst uploads a flow CSV or a Wireshark capture and receives a batch verdict (attack rate, top threat, number of classes seen), network statistics (windows, normal and attack windows, actions recommended, actions actually executed and windows held for review), the class distribution, and a list of windows, each of which can be explained with SHAP. The header shows the loaded model with its test accuracy and weighted F1, whether the SHAP explainer is ready, and whether firewall execution is armed.

::figure docs/report_assets/screenshots/shot_6_2_batch_analysis.png | 6.1 | Batch analysis of an uploaded flow file in the dashboard | 4.6

The live feed either replays a file window by window or captures live traffic from a selected interface (Fig. 6.2). It shows the number of packets, flows and windows processed, the latest detection with its confidence and prevention status, a stream of the confidence of recent threat predictions, a detection log, and the Blocked devices panel. When real firewall execution is armed, a banner states which addresses may be acted on.

::figure docs/report_assets/screenshots/shot_6_1_live_capture.png | 6.2 | Live interface capture in the dashboard during the final demonstration | 5.2

### 6.1.3 Prevention in Operation

Figs. 6.3 to 6.5 show the prevention layer at work on live traffic. In Fig. 6.3, from the live run described in Section 6.3.7, window 6 was classified PortScan with a confidence of 0.997 and the scanning tablet was blocked; the following PortScan windows from the same device are reported as "already blocked, dropped" instead of creating new rules, and once the scan ended, the tablet's traffic returned to BENIGN.

::figure docs/report_assets/live_run_dashboard.png | 6.3 | Live run: a port scan detected and blocked, then reported as already blocked | 4.3

Fig. 6.4 shows how the policy treats a class it does not trust. While the tablet repeatedly reloaded a page served by the laptop, the model classified several windows as Bot; Bot is locked to human review, so these windows were held for review (eye icon) and never executed, while the PortScan windows in the same log were acted on.

::figure docs/report_assets/screenshots/shot_6_3_detection_log_held_for_review.png | 6.4 | Detection log: Bot predictions held for review, PortScan acted on | 5.6

Fig. 6.5 shows the Blocked devices panel with the rule in force, its action (block IP, persistent until revoked), its firewall rule name and the revoke control; revoking the rule empties the panel and restores access.

::figure docs/report_assets/screenshots/shot_6_4_blocked_devices_rule.png | 6.5 | Blocked devices panel with one rule in force and the revoke control | 5.6


## 6.2 Testing

### 6.2.1 Automated Tests

Every component that can act on the network was tested automatically, without touching the real firewall, and then checked end to end on the real firewall. Table 6.1 lists the test suites.

::table 6.1 | Automated tests
| Suite | Tests | What it covers |
|:---|---:|:---|
| model/test_prevention.py | 35 | Both policies, review locks, one rule per device, allow-list of listed devices, revoke, restart recovery, every refusal path |
| model/live_check_prevention.py | 22 checks | End to end on the real Windows Firewall, with TEST-NET addresses only |
| model/test_flow_features.py | 20 | Feature definitions, CICFlowMeter-V3 quirks, IPv4 and IPv6 parsing, flow termination |
| backend/test_live_capture.py | 14 | Live engine threads, queue limits, prediction timing, polling, replay, without network, model or firewall |
| model/test_target_selection.py | 8 | Eligible sources, exclusion of this host, the gateway and broadcasting devices |
| model/test_mu_iot_windows.py | 8 | MU-IoT windows never cross a block, a split or a gap in row identifiers |
| model/test_validate_against_cicids.py | 3 | One-to-one flow matching, time-zone search, timestamps without AM/PM |
| backend api, stream and smoke tests | - | Dashboard endpoints and replay (reported as passing by the dashboard developer) |

The prevention tests include adversarial targets, such as an address list written in netsh syntax (`192.0.2.10,8.8.8.8`), address ranges, IPv6 addresses and non-text input, all of which must be refused. The end-to-end check adds real rules once per target with no duplicates, has real public addresses refused, lets temporary rules expire on their timers, revokes with the kill switch off and recovers after a simulated restart; it passed 22 of 22 checks (`model/results/prevention_live_check.txt`) and removes every rule it created.

**Mutation check.** To make sure that the tests would notice a broken safety check, the prevention engine and policy were broken deliberately in 19 different ways (for example: kill switch removed, allow-list removed, a locked class unlocked, duplicate rules allowed, a stale timer allowed to remove a newer rule, the dataset argument ignored, benign traffic made actionable). For each breakage the test suite was run, and it failed every time: 19 of 19 breakages were caught.

### 6.2.2 Defects Found by Testing

Testing found defects that would otherwise have reached the live demonstration, all of which were fixed:

- revocations were logged without the name of the rule, and timer expiries were not logged at all;
- non-text targets were not explicitly refused;
- integrated with the backend, the engine added the same rule once for every flagged window, and refused to revoke whenever the kill switch was off;
- in the live run, a device that only broadcast discovery messages was chosen as a target, which led to the rule that a target must have sent traffic to the protected host (Section 6.3.7).

## 6.3 Results

### 6.3.1 Detection on CICIDS2017

Table 6.2 compares the CNN-LSTM with the random-forest baseline on the 530,951 identical test examples (`model/results/cnn_lstm_v2_full_test_results.txt`, `model/results/chronological_random_forest_results.txt`).

::table 6.2 | CICIDS2017: CNN-LSTM and random forest on identical test examples
| Model | Accuracy | Weighted F1 | Macro F1 |
|:---|---:|---:|---:|
| CNN-LSTM (10-flow windows) | 0.9842 | 0.9864 | 0.5857 |
| Random forest (single flows) | 0.9911 | 0.9908 | 0.7803 |

Both models reach high accuracy and weighted F1, because benign traffic and the large attack classes dominate the test set. The macro F1, which weights every class equally, shows the difference: on CICIDS2017 the single-flow random forest is the better model. Table 6.3 gives the per-class scores.

::table 6.3 | CICIDS2017: F1 score per class
| Class | Test windows | CNN-LSTM F1 | Random forest F1 |
|:---|---:|---:|---:|
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
| Infiltration | 0 | - | - |

- The CNN-LSTM is clearly ahead only on DoS Hulk, and close to the forest on DDoS and PortScan, the attacks that produce long runs of similar flows.
- **Bot is a data or feature limit:** both models fail on it.
- **The web attacks are a limit of the CNN-LSTM:** with the same features, the forest reaches an F1 of 0.69 on web brute force, so the signal exists in single flows and the windowed model loses it. Why has not been tested.
- Heartbleed (3 windows) and SQL injection (5) are too small to measure, and Infiltration has no test windows at all, because all its test rows fall within the first nine rows of a day and no complete window ends on them. These are the classes locked to human review for lack of evidence.

The confusion matrix (Fig. 6.6) shows where the errors go. Almost all errors of the weak classes are confusions with benign traffic: 91% of Bot windows, 75% of web brute-force windows and 95% of XSS windows are classified benign, and a quarter of slowloris and a fifth of SSH-Patator windows likewise. Confusions between attack classes are rare.

::figure model/results/cnn_lstm_v2_confusion_matrix.png | 6.6 | Row-normalised confusion matrix of the CNN-LSTM on the CICIDS2017 test set | 5.2

Fig. 6.7 shows the training curves of the deployed model. The validation loss was lowest after the first epoch and did not improve afterwards, so early stopping ended training after the sixth epoch and restored the first-epoch weights. Because the validation windows were a random 10% of the training windows, and neighbouring windows share nine of their ten flows, the validation set overlaps the training set and gives a weak stopping signal; the test score, which comes from the separate chronological test set, is not affected.

::figure model/results/cnn_lstm_v2_training_curves.png | 6.7 | Training and validation curves of the deployed CICIDS2017 model | 5.6

### 6.3.2 Detection on MU-IoT

Table 6.4 compares the two models on the MU-IoT test windows whose exact sequence never appears in training (`model/results/mu_iot/`).

::table 6.4 | MU-IoT: CNN-LSTM and random forest on unseen test windows
| Measure | CNN-LSTM | Random forest |
|:---|---:|---:|
| Within recordings: accuracy / macro F1 (528,967 windows) | **0.964 / 0.936** | 0.904 / 0.816 |
| Held-out recordings: accuracy / macro F1 (686,566 windows) | **0.680 / 0.676** | 0.407 / 0.404 |
| Normal traffic flagged as attack (within) | **9.3%** | 17.2% |
| Held-out attacks classified as normal | **0.09%** | 2.5% |

On MU-IoT the CNN-LSTM is clearly better than the forest, most of all on the recordings it never saw. Within recordings its per-class F1 scores are higher for every class: DDoS 0.980 against 0.928, Injection 0.978 against 0.958, MiTM 0.963 against 0.862, Password_Hacking 0.990 against 0.955, Scan 0.994 against 0.949, Spyware 0.747 against 0.259 and normal 0.909 against 0.789. Table 6.5 shows the accuracy on each held-out recording.

::table 6.5 | MU-IoT: accuracy on each held-out recording
| Held-out recording | Class | CNN-LSTM | Random forest |
|:---|:---|---:|---:|
| MQTT dictionary attack | Password_Hacking | **0.998** | 0.361 |
| XSS attack | Injection | **0.882** | 0.839 |
| Vulnerability scan | Scan | 0.446 | **0.495** |
| hping3 UDP flood | DDoS | **0.321** | 0.000 |

The CNN-LSTM almost never misses an attack on unseen recordings (0.09% called normal); its errors concern the name of the attack. Unfamiliar tools are mapped to the nearest familiar class: the hping3 flood, for example, is called Scan in 68% of its windows. Because every automatic MU-IoT action blocks the source address, a misnamed attack is still blocked. The main weakness is false alarms on normal traffic (9.3%), most of them predicted as Spyware.

**Why sequences help on MU-IoT.** With timestamps removed, identical MU-IoT flow records often appear with different labels: 71.8% of single Scan test records also appear in the training data with another label, against 0.0% of twenty-row Scan windows. A model that sees one record at a time cannot separate such records, whatever its quality; a model that sees the sequence can. On CICIDS2017, by contrast, single flows are distinctive enough for a random forest to do better. The evidence therefore supports the CNN-LSTM where traffic is ambiguous at the level of single flows, as in the IoT data, not as a universal improvement.

### 6.3.3 Explainability

**Choice of explainer for the dashboard.** Table 6.6 summarises the measurements on which the dashboard's explainer was chosen.

::table 6.6 | Measured comparison of SHAP explainers on the deployed model
| Property | Gradient explainer | Kernel SHAP (deployed) |
|:---|:---|:---|
| Additivity error (base value plus attributions against model output) | about 0.13 | about 10⁻⁹ (largest measured 7.2 x 10⁻⁹) |
| Same input, repeated runs | Different results | Identical (fixed seed) |
| Time per window | 1 to 16 s | about 1.5 s (1,000 samples) |
| Agreement with a converged reference | - | r = 0.98 with grouped features (r = 0.34 with 200 ungrouped inputs) |

Two configuration details mattered. Grouping each feature's ten time steps into one value reduced the problem from 200 to 20 attributions, which the sampling budget can estimate reliably; and the explainer's default regularisation, which silently keeps only ten of the inputs, was switched off. The explanation is computed on demand for the selected window only, so its cost of about 1.5 seconds does not slow down the analysis.

**Causes of the MU-IoT errors.** Table 6.7 summarises the SHAP error analysis (`model/results/mu_iot/mu_iot_shap_report.txt`). In every group the mean SHAP sum matched the mean output to within 0.04.

::table 6.7 | Causes of the main MU-IoT errors found with SHAP
| Error | Similarity to the predicted class's detections | Similarity to the true class's detections | Cause |
|:---|---:|---:|:---|
| normal classified as Spyware | 0.87 | 0.29 | Systematic resemblance |
| hping3 flood classified as Scan | 0.59 | -0.64 | Real resemblance to scans |
| Vulnerability scan classified as Password_Hacking | 0.20 | -0.05 | Extrapolation beyond the training range |

- **normal classified as Spyware.** The same features (DNS_RCUL, TCPWS_Mode, FAMax, DNSQTL and FD) push both the false alarms and the real Spyware detections towards Spyware (Fig. 6.8), and the false alarms are confident, with a mean probability of 0.76. No confidence threshold can separate them from real detections, which is why Spyware is locked to human review.
- **hping3 flood classified as Scan.** The flood's packet sizes (about 64) and its near-zero FAMean feature match those of scans (packet size about 60), not those of the floods in the training data (packet size about 74, FAMean 0.017). The model is right that the traffic resembles a scan; the training data simply contain no flood of this kind.
- **Vulnerability scan classified as Password_Hacking.** One feature dominates: the mean TCP window size, with a median of about 25,000 in this recording against about 3,900 and 3,500 in the two classes. The model is extrapolating far beyond the values it was trained on.

::figure model/results/mu_iot/mu_iot_shap_spyware.png | 6.8 | Mean SHAP values of normal traffic flagged as Spyware, real Spyware detections and correctly classified normal traffic | 4.6
### 6.3.4 Prevention Policy

Every test window was passed through the policy and the decision compared with its true label (`model/results/prevention_policy_cicids2017.txt` and its MU-IoT counterpart). Table 6.8 gives the result.

::table 6.8 | Effect of the prevention policy on all test windows
| Dataset | Benign windows actioned automatically | Attack windows handled automatically | Attack windows missed |
|:---|---:|---:|---:|
| CICIDS2017 | 0.33% | 96.6% | 2.4% |
| MU-IoT, within recordings | 1.6% | 94.1% | 1.5% |
| MU-IoT, held-out recordings | no normal traffic | 94.4% | 0.08% |

- **The measurement changed the policy.** Before Bot was locked to review, all 17 automatic Bot actions on the CICIDS2017 test set, at confidences of 0.94 and above, hit benign traffic. High confidence did not make these predictions right.
- On CICIDS2017 the policy handles 96.6% of attack windows automatically while acting on only one benign window in 300.
- On MU-IoT the false-action rate on normal traffic is five times higher (1.6%, mostly Injection), and it is the main remaining risk of the MU-IoT policy.
- The thresholds were derived from test-set F1 scores, and no separate calibration set exists, so these figures describe the policy rather than validate it independently.

### 6.3.5 Validation of the Flow Extractor

The original Friday capture of CICIDS2017, published by the University of New Brunswick, was passed through the project's extractor, and every resulting flow was compared with CICFlowMeter-V3's official row for the same flow (`model/results/extractor_validation.md`). The comparison covered ten minutes inside the PortScan period. Flows were matched one to one by their five-tuple and start time; the official timestamps turned out to be in local time (UTC-3) and written without AM or PM, which the matching had to account for. Table 6.9 summarises the result.

::table 6.9 | Extractor against CICFlowMeter-V3 on the original CICIDS2017 capture
| Measure | Value |
|:---|:---|
| Flows matched one to one with official rows | 5,957 of 7,332 (81%); the rest share a five-tuple within a minute, mostly reused nmap ports |
| All 20 features agree, at the precision printed in the official CSV | 99.8% |
| All 20 features agree strictly (within 10⁻⁴) | 86.3% |
| PortScan flows agreeing on all 20 features | 49 of 49 |
| Agreement if flows also end on RST | 98.9% (so CICFlowMeter-V3 did not end flows on RST) |

The official CSV prints large values with three significant digits (for example 1.02E+07), so strict agreement is lower than agreement at the printed precision; the per-feature agreement at the printed precision is between 99.83% and 100% for every one of the 20 features. The comparison found two real differences, both of which were corrected: times must be whole microseconds (floating-point epoch seconds had turned a 100 μs gap into 99.9 μs), and a FIN that starts a flow must not end it, so the reply joins that flow. The second correction is the TCP appendix artefact described by Engelen et al. [@K26]; correcting it raised strict agreement from 77.5% to 86.3%.

### 6.3.6 Real Traffic and Public Captures

**Public captures.** The data team ran the pipeline on public packet captures that the model was never trained on (Table 6.10, `docs/report/live_data_sources.md`). These captures have no window-level labels, so the predicted attack ratio shows the model's behaviour, not its accuracy. Three runs were cut at the dashboard's limit of 2,000 windows.

::table 6.10 | Predicted attack ratio on public captures
| Capture | Windows (processed) | Predicted attack ratio |
|:---|---:|---:|
| CTU-13 Neris botnet, capture 42 | 2,369 (2,000) | 23.2% |
| CTU-13 Neris botnet, capture 43 | 3,065 (2,000) | 4.0% |
| SHIELD-i46 normal LAN traffic | 105 | about 1.0% |
| SHIELD-i46 5G DDoS traffic | 2,849 (2,000) | 94.2% |
| Small Wi-Fi capture (Wireshark) | 7 | 14.3% |

The DDoS capture is flagged almost entirely and the normal LAN capture almost not at all, which is the expected direction; the botnet captures, recorded in 2011 on a different network, are flagged far less consistently, which matches the model's weakness on the Bot class.

**Own captures.** Three captures of about three minutes each were recorded with a laptop as the protected host and an Android tablet as a second device on a phone hotspot (`model/results/hotspot_live_results.md`). The captures contain personal traffic and are not stored in the repository. Table 6.11 gives the results, together with the data team's ten-minute browsing capture.

::table 6.11 | Results on own packet captures
| Capture | Result |
|:---|:---|
| Port scan from the tablet (nmap -sT, 1,051 probes in 7 s) | 98% of the windows pointing at the tablet classified PortScan; replayed through the live engine, the first detection came 1.6 s after the first SYN, and every automatic action targeted the tablet |
| Laptop browsing (IPv4 and IPv6) | 11.1% of windows not benign; 7.6% recommend an automatic action, none with a target that could be blocked |
| Tablet repeatedly loading a page on the laptop | Windows classified Bot and held for review; no automatic action against the tablet |
| Ten-minute browsing capture (data team), live settings | 29.9% of 4,857 windows not benign, 23.8% FTP-Patator |

Four findings follow from these captures.

- **A scan is recognised only if the victim answers it.** In CICIDS2017 the victim servers replied to every probe. Windows' stealth mode replies to none, and the scan then looks benign to the model. For the demonstration, stealth mode was turned off on the laptop, so that it answers like the 2017 servers did.
- **Repeated polling of one web server reads as Bot,** because CICIDS2017's Ares botnet polls its command server in the same way. All 127 such windows were held for review by the Bot lock: the policy, not the model, kept the tablet from being blocked.
- **Present-day browsing raises recommendation-only false alarms.** IPv6 and QUIC traffic, which did not exist in the 2017 training data in this form, is often classified as an attack (mostly DoS GoldenEye or FTP-Patator). The sources of these windows are the laptop itself and internet servers, never a local device, so nothing was executed. Analysing IPv4 only reduces the rates to 3.6% and 0%, but ignores 98% of the browsing packets. The rate also depends strongly on the traffic, from 11.1% to 29.9% between the two browsing captures.
- **The laptop sees its own traffic plus other devices' broadcasts.** Only a device that talks to the laptop can be a target (Section 4.5.7).

### 6.3.7 Live Run on a Real Network

On 18 October 2026 the whole system ran live on a home Wi-Fi router used daily by 20 to 30 people, with the owner's permission, and with the tablet as the only device listed as a permitted target. Table 6.12 summarises the run.

::table 6.12 | Live run on a shared Wi-Fi network
| Aspect | Result |
|:---|:---|
| Detection | PortScan at a confidence of 0.99, about 2 s after nmap's first probes; 13 consecutive PortScan windows |
| Prevention | Tablet blocked automatically with one rule; 18 further detections answered "already blocked" |
| Effect | The laptop's services (test page, dashboard, remote desktop) became unreachable from the tablet |
| Revocation | Page reachable again after revoking; three full scan, block and revoke cycles |
| Normal use | The tablet's page reloads read as Bot, held for review, never executed |
| Bystander | Another person's device, flagged as DoS Slowhttptest at 0.996 from its SSDP discovery broadcasts, refused 10 times because it was not listed |

Most of nmap's 1,000 ports were probed within the second before the block took effect, so nmap still listed them as closed: a block stops an attacker from that moment on, not retroactively. The bystander is the most instructive result of the run. The model was wrong with high confidence, about a device that had nothing to do with the test, on a network used by other people; the allow-list refused every attempt to act. The incident led to the rule that a device becomes a target only if it has sent traffic to the protected host, since discovery broadcasts never do.

The system was demonstrated again at the final project review on a different network, with the same sequence: live capture, port scan, automatic block, already-blocked reports, and revocation (Figs. 6.2, 6.4 and 6.5).

### 6.3.8 Inference Speed

Table 6.13 gives the inference speed measured on the laptop's CPU, plugged in, without a GPU (`model/results/inference_benchmark.txt`).

::table 6.13 | Inference speed on the laptop CPU (AMD Ryzen 3 5300U)
| Measure | CICIDS2017 model | MU-IoT model |
|:---|---:|---:|
| One window, direct call (predict_on_batch) | 1.48 ms | 1.60 ms |
| One window, model.predict | 67 ms | 66 ms |
| Batches of 2,048 windows | about 70,700 windows/s | about 21,900 windows/s |
| Model file size | 1.01 MB | - |

The Keras `predict` method adds about 65 ms of fixed overhead per call. The extractor processes about 68,000 packets per second, and the live engine makes one prediction per second, so neither the model nor the extractor limits the live system; detection latency is set by the flow-ending rules and the one-second prediction interval.

## 6.4 Discussion

- **Sequences are not a universal improvement.** The comparison on identical examples is the central result: a report that evaluated the CNN-LSTM alone, or on CICIDS2017 alone, would have reached the wrong conclusion in one direction or the other. Sequences help where single flow records are ambiguous, as in MU-IoT.
- **Reliability, not accuracy, decides what may be automated.** An accuracy of 98.4% says nothing about whether a Bot prediction may be acted on; a Bot F1 of 0.056 does. The same review lock protected the tablet during the live run.
- **Safety limits are part of the result.** In the live run the model was confidently wrong about another person's device; only the allow-list prevented an automatic block.
- **Benchmark features must be reproduced exactly.** Validating the extractor against the original capture found two differences that no test based on the documentation would have found.
- **A 2017 model meets 2026 traffic.** None of the false alarms on present-day traffic was executed, but they show that the next step is retraining on current traffic, not a larger model.

## 6.5 Limitations

- **Model.** On CICIDS2017 a single-flow random forest outperforms the CNN-LSTM, which loses web-attack signal that single flows carry. Generalisation to unseen attack tools is weak (held-out macro F1 0.68). Normal traffic and Spyware in MU-IoT each come from one recording, so their scores are optimistic.
- **Evaluation.** Feature selection used a sample that includes some later test rows; the CICIDS2017 validation set overlaps the training windows; the CICIDS2017 test set contains later traffic of the same capture sessions, not unseen attacks; the policy thresholds come from test-set F1 without a separate calibration set; and each model was trained once, so the scores carry no error margin.
- **Extractor.** The extractor was validated on one ten-minute slice of one day, and only 49 PortScan flows could be matched one to one, because nmap reuses source ports.
- **Live operation.** One live attack type (a TCP connect scan) was run, on one network, from one device at a time. "Real time" means one prediction per second on the ten most recently ended flows; during a fast scan most windows are never classified, and blocking follows detection by about two seconds, by which time a fast scan has probed most ports.
- **Prevention.** Prevention acts only on documentation addresses and devices listed by hand; rate limiting is a temporary full block; input sanitisation against XSS is a recommendation only.
- **Dataset shift.** The 2017-trained model raises recommendation-only false alarms on present-day IPv6 and QUIC traffic (11% to 30% of browsing windows), reads repeated polling as Bot, and does not recognise scans against a silent, firewalled host.
- **Scope.** The MU-IoT model is evaluated offline and is not served by the dashboard, because live traffic is converted into CICIDS2017 features.
