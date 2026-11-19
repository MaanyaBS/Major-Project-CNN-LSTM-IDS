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

Fig. 6.6 shows the same panel after the analyst revoked the rule: no rule is in force, while the detection log keeps the history of the earlier detections.

::figure docs/report_assets/screenshots/shot_6_5_after_revoke_no_rules.png | 6.6 | After revocation: no firewall rules in force | 5.0


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

### 6.2.2 Test Cases

Tables 6.2 to 6.4 list every automated test case. Each test sets up its own situation, runs the code under test and checks the outcome; all of them pass.

::table 6.2 | Test cases of the prevention policy and execution engine
| ID | Test case (expected behaviour) | Result |
|:---|:---|:---|
| TP-01 | Every class of both models has a policy entry | Pass |
| TP-02 | Every policy entry has a valid action, severity and threshold | Pass |
| TP-03 | The F1 scores in the policy match the committed results files | Pass |
| TP-04 | Benign traffic never triggers an action | Pass |
| TP-05 | A confidence equal to the threshold acts (inclusive boundary) | Pass |
| TP-06 | Classes locked to review never act automatically | Pass |
| TP-07 | Less reliable classes need more confidence | Pass |
| TP-08 | MU-IoT thresholds follow the CICIDS2017 calibration curve | Pass |
| TP-09 | MU-IoT automatic actions rest only on held-out evidence | Pass |
| TP-10 | The two datasets' policies are kept apart (shared class names) | Pass |
| TP-11 | An unknown dataset is an error, not a silent default | Pass |
| TP-12 | An unknown class goes to review | Pass |
| TP-13 | With the kill switch off, every action is refused | Pass |
| TP-14 | Real and malformed targets are refused even when enabled and administrator | Pass |
| TP-15 | Without administrator rights, actions are refused | Pass |
| TP-16 | An unknown action type is refused | Pass |
| TP-17 | An operating-system failure is reported, not raised | Pass |
| TP-18 | Documentation (TEST-NET) addresses are executed | Pass |
| TP-19 | Every attempt is logged exactly once | Pass |
| TP-20 | A temporary rule expires and its expiry is logged | Pass |
| TP-21 | A revoked rule is not swept again | Pass |
| TP-22 | The startup sweep removes only stale temporary rules, and is idempotent | Pass |
| TP-23 | A target flagged repeatedly gets one rule | Pass |
| TP-24 | One rule per device across different actions | Pass |
| TP-25 | The list of active rules shows exactly what is in force | Pass |
| TP-26 | The demo target list accepts only single private LAN addresses | Pass |
| TP-27 | A LAN device can be blocked only when listed | Pass |
| TP-28 | A rule can be applied again after revoke or expiry | Pass |
| TP-29 | A stale timer never removes a newer rule | Pass |
| TP-30 | A timer that already fired cannot remove a newer rule | Pass |
| TP-31 | Revoking cancels the expiry timer | Pass |
| TP-32 | Revoke works with the kill switch off, but only in scope | Pass |
| TP-33 | Revoke needs administrator rights | Pass |
| TP-34 | After a restart, active rules and pending expiries are restored | Pass |
| TP-35 | Refusals and skipped attempts do not hide a stale rule from the sweep | Pass |

::table 6.3 | Test cases of the packet-to-flow extractor and the live engine
| ID | Test case (expected behaviour) | Result |
|:---|:---|:---|
| TF-01 | Reproduces a CICIDS2017 row with two padded ACK packets | Pass |
| TF-02 | First packet counted twice; sample standard deviation | Pass |
| TF-03 | Direction and backward statistics are correct | Pass |
| TF-04 | Fwd IAT Std is a sample standard deviation in microseconds | Pass |
| TF-05 | Times are whole microseconds at real dates | Pass |
| TF-06 | A FIN ends the flow; later packets start a new one | Pass |
| TF-07 | An RST ends the flow only when enabled | Pass |
| TF-08 | A flow that starts with a FIN keeps its reply (TCP appendix) | Pass |
| TF-09 | A FIN ends the flow under both settings | Pass |
| TF-10 | Reading a file never ends flows on idle time | Pass |
| TF-11 | The flow timeout is measured from the flow's start | Pass |
| TF-12 | The live tick ends flows only past the flow timeout | Pass |
| TF-13 | Flows are returned in the order they ended | Pass |
| TF-14 | UDP flows are handled | Pass |
| TF-15 | Packet lengths include Ethernet padding | Pass |
| TF-16 | The fast byte reader matches Scapy's decoding (IPv4) | Pass |
| TF-17 | The fast byte reader matches Scapy's decoding (IPv6) | Pass |
| TF-18 | Other link types and IPv6 authentication headers are parsed | Pass |
| TF-19 | IPv4 and IPv6 flows from one capture | Pass |
| TF-20 | Writing and reading a capture file gives the same flows | Pass |
| TL-01 | A scan is detected and the scanner is blocked | Pass |
| TL-02 | Benign traffic is not acted on | Pass |
| TL-03 | This laptop and the gateway are never targets | Pass |
| TL-04 | A device that only broadcasts is never a target | Pass |
| TL-05 | Nothing is predicted before ten flows have ended | Pass |
| TL-06 | The flow timeout ends quiet flows on the tick | Pass |
| TL-07 | A backlog is timed by its own packets | Pass |
| TL-08 | A full queue drops and counts packets | Pass |
| TL-09 | IPv6 is analysed unless switched off | Pass |
| TL-10 | Polling pages through results and reports what it skipped | Pass |
| TL-11 | A replay through the threads detects, blocks and stops | Pass |
| TL-12 | A failing prediction does not stop the capture | Pass |
| TL-13 | Interfaces are listed where Npcap is installed | Pass |
| TL-14 | Starting is refused before the model is loaded | Pass |

::table 6.4 | Test cases of target selection, MU-IoT windows and the extractor validator
| ID | Test case (expected behaviour) | Result |
|:---|:---|:---|
| TS-01 | The most frequent valid source is chosen | Pass |
| TS-02 | Never this laptop or the gateway | Pass |
| TS-03 | Multicast, link-local and broadcast traffic is ignored | Pass |
| TS-04 | Public, IPv6 and malformed addresses are not candidates | Pass |
| TS-05 | Documentation addresses are not treated as LAN devices | Pass |
| TS-06 | A tie goes to the most recent source | Pass |
| TS-07 | Only devices that address this machine count | Pass |
| TS-08 | No candidate gives no target, never a random address | Pass |
| TM-01 | Windows never cross a block, a split or a gap | Pass |
| TM-02 | The number of windows per block is correct | Pass |
| TM-03 | A window's label is its last row; mixed windows are reported | Pass |
| TM-04 | A gap in row identifiers breaks windows unless disabled | Pass |
| TM-05 | Timestamp features are rejected | Pass |
| TM-06 | A clean data package passes validation | Pass |
| TM-07 | Per-class sampling caps large classes, keeps small ones, is deterministic | Pass |
| TM-08 | Class weights favour rare classes and respect the cap | Pass |
| TV-01 | End to end on a synthetic capture day | Pass |
| TV-02 | Agreement at the printed precision of the official CSV | Pass |
| TV-03 | Timestamps without AM or PM are read correctly | Pass |

### 6.2.3 End-to-End Check on the Real Firewall

The end-to-end check runs the engine against the real Windows Firewall with documentation addresses only, with the timers of temporary actions shortened to 8 and 12 seconds (Table 6.5, `model/results/prevention_live_check.txt`).

::table 6.5 | End-to-end check on the Windows Firewall (22 of 22 checks passed)
| Step | What is checked | Result |
|:---|:---|:---|
| 1 | block_ip adds one inbound and one outbound rule | Pass (2 rules) |
| 2 | The same attacker flagged five more times: all "already active", still 2 rules | Pass |
| 3 | Real addresses (8.8.8.8, 192.168.1.1) are refused and no rule exists for them | Pass |
| 4 | A temporary rule (drop_connection) is added and removed by its timer | Pass |
| 5 | Revoke with the kill switch off removes both rules; a real address is refused | Pass |
| 6 | After a simulated restart, the persistent block is remembered and the pending timer still removes its rule | Pass |
| 7 | Clean-up: no test rules are left in the firewall | Pass |

### 6.2.4 Defects Found by Testing

Testing found defects that would otherwise have reached the live demonstration, all of which were fixed:

- revocations were logged without the name of the rule, and timer expiries were not logged at all;
- non-text targets were not explicitly refused;
- integrated with the backend, the engine added the same rule once for every flagged window, and refused to revoke whenever the kill switch was off;
- in the live run, a device that only broadcast discovery messages was chosen as a target, which led to the rule that a target must have sent traffic to the protected host (Section 6.3.7).

## 6.3 Results

### 6.3.1 Detection on CICIDS2017

Table 6.6 compares the CNN-LSTM with the random-forest baseline on the 530,951 identical test examples (`model/results/cnn_lstm_v2_full_test_results.txt`, `model/results/chronological_random_forest_results.txt`).

::table 6.6 | CICIDS2017: CNN-LSTM and random forest on identical test examples
| Model | Accuracy | Weighted F1 | Macro F1 |
|:---|---:|---:|---:|
| CNN-LSTM (10-flow windows) | 0.9842 | 0.9864 | 0.5857 |
| Random forest (single flows) | 0.9911 | 0.9908 | 0.7803 |

Both models reach high accuracy and weighted F1, because benign traffic and the large attack classes dominate the test set. The macro F1, which weights every class equally, shows the difference: on CICIDS2017 the single-flow random forest is the better model. Table 6.7 gives the per-class scores.

::table 6.7 | CICIDS2017: F1 score per class
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

The confusion matrix (Fig. 6.7) shows where the errors go. Almost all errors of the weak classes are confusions with benign traffic: 91% of Bot windows, 75% of web brute-force windows and 95% of XSS windows are classified benign, and a quarter of slowloris and a fifth of SSH-Patator windows likewise. Confusions between attack classes are rare.

::figure model/results/cnn_lstm_v2_confusion_matrix.png | 6.7 | Row-normalised confusion matrix of the CNN-LSTM on the CICIDS2017 test set | 5.2

Fig. 6.8 shows the training curves of the deployed model. The validation loss was lowest after the first epoch and did not improve afterwards, so early stopping ended training after the sixth epoch and restored the first-epoch weights. Because the validation windows were a random 10% of the training windows, and neighbouring windows share nine of their ten flows, the validation set overlaps the training set and gives a weak stopping signal; the test score, which comes from the separate chronological test set, is not affected.

::figure model/results/cnn_lstm_v2_training_curves.png | 6.8 | Training and validation curves of the deployed CICIDS2017 model | 5.6

Table 6.8 lists the values behind the curves, transcribed from the training log.

::table 6.8 | Training history of the deployed CICIDS2017 model
| Epoch | Training loss | Training accuracy | Validation loss | Validation accuracy |
|---:|---:|---:|---:|---:|
| 1 (kept) | 0.1798 | 0.9435 | 0.1525 | 0.9539 |
| 2 | 0.1072 | 0.9513 | 0.3387 | 0.8386 |
| 3 | 0.0844 | 0.9654 | 0.2021 | 0.9313 |
| 4 | 0.0704 | 0.9739 | 0.2457 | 0.9346 |
| 5 | 0.0642 | 0.9764 | 0.2792 | 0.9123 |
| 6 | 0.0612 | 0.9767 | 0.1588 | 0.9559 |

### 6.3.2 Detection on MU-IoT

Table 6.9 compares the two models on the MU-IoT test windows whose exact sequence never appears in training (`model/results/mu_iot/`).

::table 6.9 | MU-IoT: CNN-LSTM and random forest on unseen test windows
| Measure | CNN-LSTM | Random forest |
|:---|---:|---:|
| Within recordings: accuracy / macro F1 (528,967 windows) | **0.964 / 0.936** | 0.904 / 0.816 |
| Held-out recordings: accuracy / macro F1 (686,566 windows) | **0.680 / 0.676** | 0.407 / 0.404 |
| Normal traffic flagged as attack (within) | **9.3%** | 17.2% |
| Held-out attacks classified as normal | **0.09%** | 2.5% |

On MU-IoT the CNN-LSTM is clearly better than the forest, most of all on the recordings it never saw. Within recordings its per-class F1 scores are higher for every class: DDoS 0.980 against 0.928, Injection 0.978 against 0.958, MiTM 0.963 against 0.862, Password_Hacking 0.990 against 0.955, Scan 0.994 against 0.949, Spyware 0.747 against 0.259 and normal 0.909 against 0.789. Table 6.10 shows the accuracy on each held-out recording.

::table 6.10 | MU-IoT: accuracy on each held-out recording
| Held-out recording | Class | CNN-LSTM | Random forest |
|:---|:---|---:|---:|
| MQTT dictionary attack | Password_Hacking | **0.998** | 0.361 |
| XSS attack | Injection | **0.882** | 0.839 |
| Vulnerability scan | Scan | 0.446 | **0.495** |
| hping3 UDP flood | DDoS | **0.321** | 0.000 |

The CNN-LSTM almost never misses an attack on unseen recordings (0.09% called normal); its errors concern the name of the attack. Unfamiliar tools are mapped to the nearest familiar class: the hping3 flood, for example, is called Scan in 68% of its windows. Because every automatic MU-IoT action blocks the source address, a misnamed attack is still blocked. The main weakness is false alarms on normal traffic (9.3%), most of them predicted as Spyware.

Tables 6.11 and 6.12 give the full per-class scores on all test windows of the two tracks (including repeated windows, so the figures differ slightly from the unseen-only scores of Table 6.9), and Table 6.13 shows where the held-out windows went.

::table 6.11 | MU-IoT within recordings: per-class results on all 586,631 test windows
| Class | Precision | Recall | F1 | Windows |
|:---|---:|---:|---:|---:|
| DDoS | 0.99 | 0.97 | 0.98 | 149,566 |
| Injection | 0.96 | 1.00 | 0.98 | 35,340 |
| MiTM | 0.94 | 0.98 | 0.96 | 3,954 |
| Password_Hacking | 0.98 | 1.00 | 0.99 | 148,851 |
| Scan | 1.00 | 0.99 | 0.99 | 143,875 |
| Spyware | 0.73 | 0.76 | 0.75 | 20,316 |
| normal | 0.91 | 0.91 | 0.91 | 84,729 |
| Accuracy / macro F1 | | | 0.9672 / 0.9372 | 586,631 |

::table 6.12 | MU-IoT held-out recordings: per-class results on all 731,358 test windows
| Class | Precision | Recall | F1 | Windows |
|:---|---:|---:|---:|---:|
| DDoS (hping3 flood) | 0.73 | 0.32 | 0.45 | 199,620 |
| Injection (XSS) | 0.96 | 0.88 | 0.92 | 132,498 |
| Password_Hacking (MQTT dictionary) | 0.67 | 1.00 | 0.80 | 199,620 |
| Scan (vulnerability scan) | 0.40 | 0.45 | 0.42 | 199,620 |
| Accuracy / macro F1 | | | 0.6416 / 0.6469 | 731,358 |

::table 6.13 | Confusion matrix of the held-out recordings (rows: true class; columns: predicted class)
| True \ predicted | DDoS | Injection | MiTM | Password Hacking | Scan | Spyware | normal |
|:---|---:|---:|---:|---:|---:|---:|---:|
| DDoS | 64,056 | 5 | 0 | 149 | 135,327 | 9 | 74 |
| Injection | 18 | 116,907 | 7 | 15,128 | 28 | 9 | 401 |
| Password_Hacking | 11 | 1 | 0 | 199,255 | 353 | 0 | 0 |
| Scan | 23,327 | 5,282 | 66 | 81,731 | 89,049 | 33 | 132 |

The matrix makes the pattern of the errors visible: almost no held-out attack window is called normal (607 of 731,358), but the hping3 flood is mostly called Scan and the vulnerability scan is spread over Password_Hacking, DDoS and Scan. The model recognises that these recordings are attacks; it does not know the new tools well enough to name them. Table 6.14 shows how the MU-IoT model was trained: the validation loss was lowest after epoch 7, and early stopping ended training five epochs later.

::table 6.14 | Training history of the MU-IoT model
| Epoch | Training loss | Validation loss | Validation accuracy | Validation macro F1 |
|---:|---:|---:|---:|---:|
| 1 | 0.1350 | 0.1353 | 0.9409 | 0.9441 |
| 2 | 0.0712 | 0.2272 | 0.9020 | 0.9093 |
| 3 | 0.0580 | 0.1197 | 0.9536 | 0.9555 |
| 4 | 0.0510 | 0.1273 | 0.9514 | 0.9547 |
| 5 | 0.0460 | 0.1313 | 0.9529 | 0.9563 |
| 6 | 0.0427 | 0.1221 | 0.9601 | 0.9631 |
| 7 (kept) | 0.0392 | 0.1182 | 0.9625 | 0.9647 |
| 8 | 0.0373 | 0.1577 | 0.9544 | 0.9578 |
| 9 | 0.0349 | 0.1437 | 0.9580 | 0.9610 |
| 10 | 0.0336 | 0.1346 | 0.9599 | 0.9627 |
| 11 | 0.0322 | 0.1347 | 0.9628 | 0.9657 |
| 12 | 0.0309 | 0.1389 | 0.9614 | 0.9645 |

**Why sequences help on MU-IoT.** With timestamps removed, identical MU-IoT flow records often appear with different labels: 71.8% of single Scan test records also appear in the training data with another label, against 0.0% of twenty-row Scan windows. A model that sees one record at a time cannot separate such records, whatever its quality; a model that sees the sequence can. On CICIDS2017, by contrast, single flows are distinctive enough for a random forest to do better. The evidence therefore supports the CNN-LSTM where traffic is ambiguous at the level of single flows, as in the IoT data, not as a universal improvement.

### 6.3.3 Explainability

**Choice of explainer for the dashboard.** Table 6.15 summarises the measurements on which the dashboard's explainer was chosen.

::table 6.15 | Measured comparison of SHAP explainers on the deployed model
| Property | Gradient explainer | Kernel SHAP (deployed) |
|:---|:---|:---|
| Additivity error (base value plus attributions against model output) | about 0.13 | about 10⁻⁹ (largest measured 7.2 x 10⁻⁹) |
| Same input, repeated runs | Different results | Identical (fixed seed) |
| Time per window | 1 to 16 s | about 1.5 s (1,000 samples) |
| Agreement with a converged reference | - | r = 0.98 with grouped features (r = 0.34 with 200 ungrouped inputs) |

Two configuration details mattered. Grouping each feature's ten time steps into one value reduced the problem from 200 to 20 attributions, which the sampling budget can estimate reliably; and the explainer's default regularisation, which silently keeps only ten of the inputs, was switched off. The explanation is computed on demand for the selected window only, so its cost of about 1.5 seconds does not slow down the analysis.

**Causes of the MU-IoT errors.** Table 6.16 summarises the SHAP error analysis (`model/results/mu_iot/mu_iot_shap_report.txt`). In every group the mean SHAP sum matched the mean output to within 0.04.

::table 6.16 | Causes of the main MU-IoT errors found with SHAP
| Error | Similarity to the predicted class's detections | Similarity to the true class's detections | Cause |
|:---|---:|---:|:---|
| normal classified as Spyware | 0.87 | 0.29 | Systematic resemblance |
| hping3 flood classified as Scan | 0.59 | -0.64 | Real resemblance to scans |
| Vulnerability scan classified as Password_Hacking | 0.20 | -0.05 | Extrapolation beyond the training range |

- **normal classified as Spyware.** The same features (DNS_RCUL, TCPWS_Mode, FAMax, DNSQTL and FD) push both the false alarms and the real Spyware detections towards Spyware (Fig. 6.9), and the false alarms are confident, with a mean probability of 0.76. No confidence threshold can separate them from real detections, which is why Spyware is locked to human review.
- **hping3 flood classified as Scan.** The flood's packet sizes (about 64) and its near-zero FAMean feature match those of scans (packet size about 60), not those of the floods in the training data (packet size about 74, FAMean 0.017). The model is right that the traffic resembles a scan; the training data simply contain no flood of this kind.
- **Vulnerability scan classified as Password_Hacking.** One feature dominates: the mean TCP window size, with a median of about 25,000 in this recording against about 3,900 and 3,500 in the two classes. The model is extrapolating far beyond the values it was trained on.

::figure model/results/mu_iot/mu_iot_shap_spyware.png | 6.9 | Mean SHAP values of normal traffic flagged as Spyware, real Spyware detections and correctly classified normal traffic | 4.6

Figs. 6.10 and 6.11 show the profiles of the other two errors. For the hping3 flood, the features that push it towards Scan are the same ones that real scan detections rely on, while they push against the floods the model was trained on. For the vulnerability scan, one feature, the mean TCP window size, dominates all others by a wide margin, which is the signature of a model extrapolating far outside its training range.

::figure model/results/mu_iot/mu_iot_shap_hping3.png | 6.10 | Mean SHAP values of the hping3 flood windows classified as Scan, compared with real scan and flood detections | 4.8

::figure model/results/mu_iot/mu_iot_shap_vulnscan.png | 6.11 | Mean SHAP values of the vulnerability scan windows classified as Password_Hacking, compared with real Password_Hacking and Scan detections | 4.8
### 6.3.4 Prevention Policy

Every test window was passed through the policy and the decision compared with its true label (`model/results/prevention_policy_cicids2017.txt` and its MU-IoT counterpart). Table 6.17 gives the result.

::table 6.17 | Effect of the prevention policy on all test windows
| Dataset | Benign windows actioned automatically | Attack windows handled automatically | Attack windows missed |
|:---|---:|---:|---:|
| CICIDS2017 | 0.33% | 96.6% | 2.4% |
| MU-IoT, within recordings | 1.6% | 94.1% | 1.5% |
| MU-IoT, held-out recordings | no normal traffic | 94.4% | 0.08% |

- **The measurement changed the policy.** Before Bot was locked to review, all 17 automatic Bot actions on the CICIDS2017 test set, at confidences of 0.94 and above, hit benign traffic. High confidence did not make these predictions right.
- On CICIDS2017 the policy handles 96.6% of attack windows automatically while acting on only one benign window in 300.
- On MU-IoT the false-action rate on normal traffic is five times higher (1.6%, mostly Injection), and it is the main remaining risk of the MU-IoT policy.
- The thresholds were derived from test-set F1 scores, and no separate calibration set exists, so these figures describe the policy rather than validate it independently.

Table 6.18 breaks the CICIDS2017 result down by true class. Every reliable flood and scan class is handled automatically in more than 94% of its windows; slowloris and SSH-Patator are missed in about a quarter of their windows because the model calls them benign; and the classes locked to review are, as intended, never acted on automatically.

::table 6.18 | Policy decisions per true class on the CICIDS2017 test set
| True class | Windows | Automatic | Review | No action |
|:---|---:|---:|---:|---:|
| BENIGN | 439,987 | 0.33% | 0.93% | 98.75% |
| Bot | 381 | 1.31% | 8.14% | 90.55% |
| DDoS | 25,595 | 98.37% | 1.09% | 0.54% |
| DoS GoldenEye | 2,058 | 94.85% | 2.24% | 2.92% |
| DoS Hulk | 35,038 | 98.87% | 0.48% | 0.65% |
| DoS Slowhttptest | 1,046 | 98.37% | 1.63% | 0.00% |
| DoS slowloris | 1,083 | 69.62% | 4.71% | 25.67% |
| FTP-Patator | 1,219 | 96.72% | 2.38% | 0.90% |
| Heartbleed | 3 | 0.00% | 100.00% | 0.00% |
| PortScan | 23,378 | 96.57% | 0.73% | 2.70% |
| SSH-Patator | 739 | 73.34% | 4.33% | 22.33% |
| Web Attack - Brute Force | 288 | 0.00% | 25.35% | 74.65% |
| Web Attack - Sql Injection | 5 | 0.00% | 0.00% | 100.00% |
| Web Attack - XSS | 131 | 0.00% | 4.58% | 95.42% |

(The few Bot windows acted on automatically were predicted as another attack class, not as Bot.) Table 6.19 looks at the same decisions from the side of the action: of 89,293 automatic actions, 97.98% acted on the predicted attack, 0.41% on a different attack (the attacker was still acted on, possibly with another action type), and 1.61% on benign traffic. PortScan and DoS GoldenEye produce most of the actions on benign traffic.

::table 6.19 | Automatic actions on the CICIDS2017 test set by predicted class
| Predicted class | Action | Threshold | Automatic | Correct | Other attack | Benign |
|:---|:---|---:|---:|---:|---:|---:|
| DDoS | block_ip | 0.55 | 25,083 | 25,015 | 24 | 44 |
| DoS GoldenEye | rate_limit | 0.70 | 2,495 | 1,948 | 62 | 485 |
| DoS Hulk | rate_limit | 0.55 | 34,767 | 34,594 | 136 | 37 |
| DoS Slowhttptest | drop_connection | 0.65 | 1,145 | 1,018 | 117 | 10 |
| DoS slowloris | drop_connection | 0.75 | 711 | 656 | 15 | 40 |
| FTP-Patator | block_ip | 0.72 | 1,387 | 1,163 | 11 | 213 |
| PortScan | block_ip | 0.60 | 23,092 | 22,553 | 5 | 534 |
| SSH-Patator | block_ip | 0.78 | 613 | 542 | 0 | 71 |

Table 6.20 gives the same breakdown for the MU-IoT recordings seen in training. MiTM and Spyware, locked to review, are sent to an analyst instead of being acted on, and 7.61% of normal windows reach review as false alerts that an analyst would dismiss.

::table 6.20 | Policy decisions per true class on the MU-IoT within-recording test set
| True class | Windows | Automatic | Review | No action |
|:---|---:|---:|---:|---:|
| DDoS | 149,566 | 97.16% | 1.15% | 1.69% |
| Injection | 35,340 | 99.95% | 0.04% | 0.01% |
| MiTM | 3,954 | 0.00% | 98.58% | 1.42% |
| Password_Hacking | 148,851 | 99.90% | 0.08% | 0.02% |
| Scan | 143,875 | 99.22% | 0.70% | 0.08% |
| Spyware | 20,316 | 0.01% | 76.37% | 23.62% |
| normal | 84,729 | 1.60% | 7.61% | 90.79% |

### 6.3.5 Validation of the Flow Extractor

The original Friday capture of CICIDS2017, published by the University of New Brunswick, was passed through the project's extractor, and every resulting flow was compared with CICFlowMeter-V3's official row for the same flow (`model/results/extractor_validation.md`). The comparison covered ten minutes inside the PortScan period. Flows were matched one to one by their five-tuple and start time; the official timestamps turned out to be in local time (UTC-3) and written without AM or PM, which the matching had to account for. Table 6.21 summarises the result.

::table 6.21 | Extractor against CICFlowMeter-V3 on the original CICIDS2017 capture
| Measure | Value |
|:---|:---|
| Flows matched one to one with official rows | 5,957 of 7,332 (81%); the rest share a five-tuple within a minute, mostly reused nmap ports |
| All 20 features agree, at the precision printed in the official CSV | 99.8% |
| All 20 features agree strictly (within 10⁻⁴) | 86.3% |
| PortScan flows agreeing on all 20 features | 49 of 49 |
| Agreement if flows also end on RST | 98.9% (so CICFlowMeter-V3 did not end flows on RST) |

The official CSV prints large values with three significant digits (for example 1.02E+07), so strict agreement is lower than agreement at the printed precision; the per-feature agreement at the printed precision is between 99.83% and 100% for every one of the 20 features. The comparison found two real differences, both of which were corrected: times must be whole microseconds (floating-point epoch seconds had turned a 100 μs gap into 99.9 μs), and a FIN that starts a flow must not end it, so the reply joins that flow. The second correction is the TCP appendix artefact described by Engelen et al. [@K26]; correcting it raised strict agreement from 77.5% to 86.3%.

::table 6.22 | Agreement of each feature with CICFlowMeter-V3 (5,957 matched flows)
| Feature | Agreement at printed precision | Strict agreement |
|:---|---:|---:|
| Destination Port | 100.00% | 100.00% |
| Total Length of Fwd Packets | 99.88% | 99.88% |
| Total Length of Bwd Packets | 99.88% | 99.88% |
| Fwd Packet Length Max | 99.98% | 99.98% |
| Fwd Packet Length Mean | 99.95% | 99.95% |
| Bwd Packet Length Max | 99.98% | 99.98% |
| Bwd Packet Length Mean | 99.95% | 99.95% |
| Bwd Packet Length Std | 99.97% | 99.97% |
| Flow IAT Max | 99.95% | 86.54% |
| Fwd IAT Std | 99.83% | 96.93% |
| Max Packet Length | 99.98% | 99.98% |
| Packet Length Mean | 99.88% | 99.88% |
| Packet Length Std | 99.90% | 99.90% |
| Packet Length Variance | 99.90% | 99.90% |
| Average Packet Size | 99.88% | 99.88% |
| Avg Fwd Segment Size | 99.95% | 99.95% |
| Avg Bwd Segment Size | 99.95% | 99.95% |
| Subflow Fwd Packets | 99.88% | 99.88% |
| Subflow Fwd Bytes | 99.88% | 99.88% |
| Subflow Bwd Bytes | 99.88% | 99.88% |

Almost all strict disagreements are in the two time features, Flow IAT Max and Fwd IAT Std, whose values are large numbers of microseconds that the official CSV prints with three significant digits; at the printed precision they agree on more than 99.8% of flows. The size features agree strictly wherever they agree at all, and every one of the 49 matched PortScan flows agrees on all 20 features.

### 6.3.6 Real Traffic and Public Captures

**Public captures.** The data team ran the pipeline on public packet captures that the model was never trained on (Table 6.23, `docs/report/live_data_sources.md`). These captures have no window-level labels, so the predicted attack ratio shows the model's behaviour, not its accuracy. Three runs were cut at the dashboard's limit of 2,000 windows.

::table 6.23 | Predicted attack ratio on public captures
| Capture | Windows (processed) | Predicted attack ratio |
|:---|---:|---:|
| CTU-13 Neris botnet, capture 42 | 2,369 (2,000) | 23.2% |
| CTU-13 Neris botnet, capture 43 | 3,065 (2,000) | 4.0% |
| SHIELD-i46 normal LAN traffic | 105 | about 1.0% |
| SHIELD-i46 5G DDoS traffic | 2,849 (2,000) | 94.2% |
| Small Wi-Fi capture (Wireshark) | 7 | 14.3% |

The DDoS capture is flagged almost entirely and the normal LAN capture almost not at all, which is the expected direction; the botnet captures, recorded in 2011 on a different network, are flagged far less consistently, which matches the model's weakness on the Bot class.

**Own captures.** Three captures of about three minutes each were recorded with a laptop as the protected host and an Android tablet as a second device on a phone hotspot (`model/results/hotspot_live_results.md`). The captures contain personal traffic and are not stored in the repository. Table 6.24 gives the results, together with the data team's ten-minute browsing capture.

::table 6.24 | Results on own packet captures
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

On 18 October 2026 the whole system ran live on a home Wi-Fi router used daily by 20 to 30 people, with the owner's permission, and with the tablet as the only device listed as a permitted target. Table 6.25 summarises the run.

::table 6.25 | Live run on a shared Wi-Fi network
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

Table 6.26 gives the inference speed measured on the laptop's CPU, plugged in, without a GPU (`model/results/inference_benchmark.txt`).

::table 6.26 | Inference speed on the laptop CPU (AMD Ryzen 3 5300U)
| Measure | CICIDS2017 model | MU-IoT model |
|:---|---:|---:|
| One window, direct call (predict_on_batch) | 1.48 ms | 1.60 ms |
| One window, model.predict | 67 ms | 66 ms |
| Batches of 2,048 windows | about 70,700 windows/s | about 21,900 windows/s |
| Model file size | 1.01 MB | - |

The Keras `predict` method adds about 65 ms of fixed overhead per call. The extractor processes about 68,000 packets per second, and the live engine makes one prediction per second, so neither the model nor the extractor limits the live system; detection latency is set by the flow-ending rules and the one-second prediction interval.

Tables 6.27 and 6.28 give the full measurements. The latency of a single window is dominated by how the model is called, not by the model itself; in batches, the CICIDS2017 model classifies about 70,700 windows per second and the larger MU-IoT model, which works in mixed precision on a CPU without hardware support for it, about 21,900.

::table 6.27 | Latency of one window on the laptop CPU, in milliseconds (CICIDS2017 model, 300 calls)
| Call path | Median | 95th percentile | 99th percentile |
|:---|---:|---:|---:|
| Backend path (scaling and model.predict) | 66.71 | 83.47 | 96.23 |
| of which scaling (pandas and scaler) | 0.86 | 1.17 | 1.43 |
| model.predict | 67.22 | 102.87 | 143.66 |
| model.predict_on_batch | 1.48 | 1.94 | 2.13 |
| Direct call model(x) | 20.52 | 28.95 | 34.54 |

::table 6.28 | Throughput by batch size, windows per second (median of 5 runs of 16,384 windows)
| Batch size | CICIDS2017 model | MU-IoT model |
|---:|---:|---:|
| 1 (backend path, one call per window) | 15 | 15 |
| 32 | 13,490 | 7,248 |
| 256 | 56,860 | 15,512 |
| 2,048 | 70,729 | 21,907 |

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

- **Connections opened before a block.** A Windows Firewall rule stops new connections; a connection the device had opened before the block may continue. A change that also resets such connections when a device is blocked was written and tested with simulated system calls after the final demonstration, and still has to be verified on a real network.
- **Dataset shift.** The 2017-trained model raises recommendation-only false alarms on present-day IPv6 and QUIC traffic (11% to 30% of browsing windows), reads repeated polling as Bot, and does not recognise scans against a silent, firewalled host.
- **Scope.** The MU-IoT model is evaluated offline and is not served by the dashboard, because live traffic is converted into CICIDS2017 features.
