# 3 | Objective and Methodology

## 3.1 Objective

The aim of the project is a hybrid CNN-LSTM intrusion detection and prevention system that is evaluated honestly, explains its decisions, acts only where it is reliable, and works on live traffic. The specific objectives are:

1. **Detection.** Train a hybrid CNN-LSTM model that classifies windows of consecutive network flows into benign traffic and fourteen attack classes of CICIDS2017, and a second model of the same architecture for the seven classes of the Indian MU-IoT dataset.
2. **Leakage-controlled evaluation.** Split the data so that near-identical neighbouring flows cannot appear on both sides of the split; compare the CNN-LSTM with a random-forest baseline trained and scored on identical examples; report macro F1 and per-class scores alongside accuracy; and test generalisation on whole MU-IoT recordings never used in training.
3. **Explainability.** Explain every prediction in the dashboard with SHAP, choosing and configuring the explainer by measurement, and use SHAP offline to find the causes of the model's main errors.
4. **Prevention.** Map each class to a countermeasure through a policy whose automatic-action thresholds follow each class's measured F1 score, lock unreliable classes to human review, and execute approved actions as Windows Firewall rules behind independent safety checks that make every action reversible.
5. **Live operation.** Convert live traffic and Wireshark captures into the exact features the model was trained on, validate this conversion against the original CICIDS2017 packet capture, and detect and block a real attack on a real network in real time.
6. **Presentation.** Provide a web dashboard that shows predictions, confidence, explanations, prevention decisions and blocked devices, with a control to revoke any block.

## 3.2 Methodology

### 3.2.1 Overview

The work was divided among the three team members by area: data preparation and live traffic captures (Maanya B S); model development, evaluation, error analysis, prevention and the live capture engine (Ruthwik Sai Ganesh); and the explainability service, backend and dashboard (Varshini D N). The methodology has an offline part, in which the datasets are prepared and the models are trained and evaluated, and an online part, in which traffic is captured, converted into flows, classified, explained and acted upon (Fig. 3.1).

::figure docs/report_assets/figures/fig_3_1_block_diagram.png | 3.1 | Proposed block diagram: offline development and online operation | 5.8

The remainder of this section follows the order of Fig. 3.1: datasets and preprocessing (Sections 3.2.2 and 3.2.3), the evaluation design (Section 3.2.4), the model and its training (Section 3.2.5), explainability (Section 3.2.6), the prevention policy (Section 3.2.7), live capture and flow extraction (Section 3.2.8), the dashboard (Section 3.2.9) and the evaluation metrics (Section 3.2.10).

### 3.2.2 Datasets

**CICIDS2017.** The dataset [@K9] is published as eight CSV files, one or two per capture day, with about 79 columns per flow. Each file was loaded, column names were standardised, rows with missing or infinite values and exact duplicate rows were removed, ten columns that were constant across the data were dropped, the label was encoded as an integer, and the files were combined with a `source_day` column that records which capture file each row came from. Table 3.1 lists the effect of cleaning on each file. The cleaned dataset has 2,655,060 rows and 70 columns.

::table 3.1 | Cleaning of the CICIDS2017 capture files
| Capture file | Original rows | Missing values | Duplicates removed | Cleaned rows |
|:---|---:|---:|---:|---:|
| Monday-WorkingHours | 529,918 | 874 | 14,278 | 515,203 |
| Tuesday-WorkingHours | 445,909 | 528 | 13,859 | 431,786 |
| Wednesday-WorkingHours | 692,703 | 2,594 | 66,975 | 624,431 |
| Thursday-Morning-WebAttacks | 170,366 | 270 | 3,719 | 166,512 |
| Thursday-Afternoon-Infiltration | 288,602 | 414 | 23,225 | 265,170 |
| Friday-Morning | 191,033 | 244 | 4,456 | 186,455 |
| Friday-Afternoon-PortScan | 286,467 | 742 | 44,734 | 241,362 |
| Friday-Afternoon-DDoS | 225,745 | 68 | 1,570 | 224,141 |
| **Total** | **2,830,743** | **5,734** | **172,816** | **2,655,060** |

The missing-value column counts values, not rows: every row removed for missing data had two missing values, so 2,867 rows were removed for this reason in total (for example, 874 values in 437 rows of the Monday file).

**MU-IoT.** The MU-IoT dataset [@K30] was recorded on an IoT testbed at Manipur University. The copy used in this project consists of 40 raw CSV files, about 12.4 GB, with 124 columns. A session-mapping step grouped the 40 files into 32 capture sessions (one recording of one activity), and the session identifier was kept with every row. Cleaning processed the files in chunks and produced 24,171,263 rows with 118 columns: eight completely empty columns and seven constant columns were removed, and the `label` and `type` columns were removed from the features because they encode the target. HTTP and RTSP request methods were encoded as small integers (for example GET as 0 and POST as 1, with -1 for missing), and the source and destination IP addresses were replaced by six numeric indicators each (private, loopback, multicast and link-local flags, and the first and last octets), so that the model cannot learn the testbed's specific addresses.

The published description of the dataset [@K30] reports a larger record count and 121 flow features; the files used here are the copy available to the team, reduced as described above and in Section 3.2.3. *[To confirm with the data team: how the 40-file copy relates to the full published dataset.]*

Data preparation also found that two of the raw files (`Botnet_Slowloris.csv` and `Slowloris.csv`) are identical, so they cannot be treated as independent recordings.

### 3.2.3 Preprocessing and Feature Selection

**CICIDS2017 features.** Twenty features were selected by random-forest importance. A random forest with 100 trees was trained on a random sample of 100,000 rows of the encoded dataset, the features were ranked by their importance, and the top 20 were kept (Table 3.2). All twenty are statistics of packet lengths, inter-arrival times and the destination port; none of them identifies a particular host.

::table 3.2 | The 20 CICIDS2017 features selected by random-forest importance
| Rank | Feature | Importance | Rank | Feature | Importance |
|---:|:---|---:|---:|:---|---:|
| 1 | Bwd Packet Length Mean | 0.0568 | 11 | Subflow Fwd Bytes | 0.0366 |
| 2 | Packet Length Variance | 0.0549 | 12 | Avg Bwd Segment Size | 0.0335 |
| 3 | Packet Length Std | 0.0490 | 13 | Fwd IAT Std | 0.0304 |
| 4 | Average Packet Size | 0.0454 | 14 | Fwd Packet Length Mean | 0.0239 |
| 5 | Total Length of Bwd Packets | 0.0424 | 15 | Subflow Bwd Bytes | 0.0217 |
| 6 | Bwd Packet Length Std | 0.0416 | 16 | Flow IAT Max | 0.0215 |
| 7 | Bwd Packet Length Max | 0.0410 | 17 | Avg Fwd Segment Size | 0.0213 |
| 8 | Total Length of Fwd Packets | 0.0406 | 18 | Fwd Packet Length Max | 0.0199 |
| 9 | Packet Length Mean | 0.0390 | 19 | Destination Port | 0.0180 |
| 10 | Max Packet Length | 0.0390 | 20 | Subflow Fwd Packets | 0.0149 |

The ranking was computed on a sample of the whole dataset, before the chronological split described below, so a small part of the sample consists of rows that later became test rows. This is a mild selection leak; its effect is probably small, because the ranking used only 100,000 of 2,655,060 rows, but it was not measured, and it is listed among the limitations (Section 6.5).

**MU-IoT features.** The MU-IoT features were selected from the 48 top-ranked features of the dataset's reference paper [@K30]. Features with poor coverage or constant values were removed, leaving 40, and two timing features, FPT and LPT (the times of a flow's first and last packet), were then removed because every recording covers one class and its own period of time, so absolute timestamps would reveal the label. The final set has 38 features (listed in Appendix B).

**Scaling.** Features are standardised with a `StandardScaler` fitted on the training rows only, so that no information from the validation or test data reaches the model through the scaling parameters:

::equation scaler | 3.1

where x is a raw value of feature j, and μ and σ are that feature's mean and standard deviation over the training rows.

**Windows.** The CNN-LSTM does not classify one flow but a window of consecutive flows. For CICIDS2017 a window holds the ten most recent flows, each described by its 20 standardised features, and is labelled with the class of its last flow:

::equation window | 3.2

The window slides by one flow, so every flow (after the first nine of a capture day) ends exactly one window. A window never spans two capture days. MU-IoT uses windows of 20 rows with 38 features, which never cross a recording block, a split boundary or a gap in the original row identifiers.

### 3.2.4 Evaluation Design

The evaluation design matters more than the architecture: a careless split measures memory, not detection [@K28].

**Chronological split for CICIDS2017.** CICIDS2017 rows have no reliable timestamp in the cleaned data, but the row order within each capture file preserves the order of capture. The data were therefore split chronologically within each group of (capture day, class): the first 80% of the rows of each group train the model, and the remaining 20% test it. A pure day-level split, holding out whole capture days, was considered and rejected, because each attack appears on only one day and such a split removed eight of the fifteen classes from the test set. The resulting test set has 530,951 windows, 83% of them benign.

**Tracks for MU-IoT.** Four complete capture sessions were held out from training and validation: an hping3 UDP flood (DDoS), a vulnerability scan (Scan), an MQTT dictionary attack (Password_Hacking) and an XSS attack (Injection). The remaining sessions were split chronologically within each session into about 70% training, 15% validation and 15% testing. This gives two test tracks (Table 3.3): *within*, later traffic of recordings seen in training, and *held-out*, recordings never seen, which measures generalisation to new attack tools.

::table 3.3 | MU-IoT rows per class and split
| Class | Train | Validation | Test (within) | Test (held-out) |
|:---|---:|---:|---:|---:|
| DDoS | 496,750 | 99,261 | 149,984 | 200,000 |
| Injection | 165,355 | 35,433 | 35,435 | 132,764 |
| MiTM | 18,623 | 3,991 | 3,992 | 0 |
| Password_Hacking | 500,000 | 100,000 | 149,174 | 200,000 |
| Scan | 500,000 | 100,000 | 144,179 | 200,000 |
| Spyware | 95,071 | 20,373 | 20,373 | 0 |
| normal | 396,196 | 84,899 | 84,900 | 0 |
| **Total** | **2,171,995** | **443,957** | **588,037** | **732,764** |

MiTM, Spyware and normal traffic have no held-out recording, so their scores come from the within track only. The final MU-IoT feature matrix has 3,936,753 rows and 38 features.

**Unseen-only scoring.** With timestamps removed, many MU-IoT windows are exact repeats of windows in the training data. Headline MU-IoT scores therefore count only test windows whose exact 20-row sequence never appears in training, so that memorised duplicates cannot inflate them.

**Baseline on identical examples.** A random forest [@K29] with 100 trees is trained on single flows with the same features and the same split, built by the same code, and scored on the last flow of each CNN-LSTM test window. Both models are thus judged on identical examples with identical labels, and any difference between them is due to the model, not the data.

### 3.2.5 Model Development

**Architecture.** The model, described in detail in Section 4.5.3, consists of two one-dimensional convolution blocks that learn local patterns across neighbouring flows, an LSTM layer that summarises how these patterns develop across the window, a dense layer and a softmax output. The same architecture is used for both datasets; only the input shape and the number of output classes differ.

**Class imbalance.** Benign traffic is 83% of the CICIDS2017 test set and some attack classes have only a few hundred examples, so the training loss weights each class (Section 4.5.3). Three weighting schemes were trained with the same architecture and scored on the same test set (Table 3.4). Capped balanced weights pushed benign traffic into rare classes, and a targeted boost of the three weakest classes made the overall result worse; the square root of the balanced weights gave the best result and is the deployed model (v2).

::table 3.4 | Class-weighting schemes compared on the CICIDS2017 test set
| Version | Class weights | Test accuracy | Macro F1 |
|:---|:---|---:|---:|
| v1 | Balanced, capped at 50 | 0.8831 | 0.4276 |
| **v2 (deployed)** | **Square root of balanced, no cap** | **0.9842** | **0.5857** |
| v3 | Three-times boost on the three weakest classes | 0.9470 | 0.4811 |

**Training procedure.** Both models use the Adam optimiser, sparse categorical cross-entropy, a batch size of 512 and early stopping on the validation loss with a patience of five epochs, restoring the best weights. The CICIDS2017 model used a stratified 10% validation split; its lowest validation loss came in the first epoch (0.153, validation accuracy 0.954), so training stopped after the sixth epoch and the first-epoch weights were kept. The MU-IoT model was trained in mixed precision on a Colab T4 GPU; every epoch draws a fresh sample of up to 300,000 training windows per class, with square-root-balanced class weights capped at 10, and checkpoints are written every epoch so that a disconnected session loses at most one epoch. Early stopping ended training at epoch 12 and kept the weights of epoch 7.

### 3.2.6 Explainability Method

Two SHAP estimators are used, each chosen for its purpose.

**Per-prediction explanations in the dashboard.** The dashboard explains the selected window with Kernel SHAP [@K16], which treats the model as a black box, with 1,000 samples, attributions grouped per feature across the ten time steps (20 values instead of 200), a fixed random seed and a background of real training windows. The explainer and its configuration were chosen by measurement against the gradient-based alternative (Section 6.3.3).

**Error analysis of the MU-IoT model.** The offline analysis uses expected gradients [@K16], with 500 samples per window and a background of 350 real training windows (50 per class). For each type of error, the mean SHAP profile of the wrongly classified windows is compared with the profiles of correctly classified windows of the predicted and of the true class, which shows whether an error is a systematic resemblance, a real similarity between attacks, or an extrapolation beyond the training data.

### 3.2.7 Prevention Policy Design

Each class is mapped to a countermeasure (block the source address, drop its connections for 60 seconds, rate-limit it for 120 seconds, isolate the host, or a recommendation only), a severity and a confidence threshold. The threshold rises as the class's measured F1 score falls, so reliable classes act at lower confidence and unreliable ones need more. Classes whose evidence is too weak are locked to human review whatever the confidence: on CICIDS2017, SQL injection, Heartbleed and Infiltration have too few test examples to measure, and Bot, Web Attack - Brute Force and XSS have an F1 score below 0.15; on MU-IoT, MiTM and Spyware have no held-out recording. Approved actions are executed as Windows Firewall rules by an execution engine with independent safety checks. The policy, the decision rule and the execution engine are described in Section 4.5.6 and Section 4.5.7, and the policy's measured effect in Section 6.3.4.

### 3.2.8 Live Capture and Packet-to-Flow Extraction

The model was trained on flows produced by CICFlowMeter version 3. To apply it to live traffic or to Wireshark captures, packets must be turned into flows with exactly the same definitions, including the tool's quirks, because the model learned the features as the tool computed them. A new extractor was written for this purpose and validated against the original CICIDS2017 capture (Section 6.3.5). Table 3.5 lists the definitions it reproduces.

::table 3.5 | CICFlowMeter-V3 behaviour reproduced by the extractor
| Behaviour | Effect on the features |
|:---|:---|
| First packet counted twice | Packet Length Mean, Std and Variance and Average Packet Size include the flow's first packet twice |
| Sample standard deviation | Standard deviations divide by n - 1 |
| Ethernet padding counted as payload | Frames shorter than Ethernet's 60-byte minimum are padded, as on the wired testbed |
| Whole-microsecond timestamps | Times and inter-arrival times are integers in microseconds |
| Flow ends on FIN | A FIN ends an existing flow; a FIN that starts a new flow does not (the "TCP appendix" [@K26]) |
| 120-second flow timeout | A flow ends 120 seconds after it started |
| Subflows | Subflow values equal the flow totals |

The extractor reads IPv4 and IPv6 packets directly from raw bytes. Live mode differs from CICFlowMeter-V3 in one deliberate way: it also ends a flow on RST. A scan flow (SYN followed by RST) has the same features either way, but ending it at the RST reports the scan within seconds instead of after the 120-second timeout. The live engine is described in Sections 4.4 and 4.5.

### 3.2.9 Dashboard and Backend

A Flask backend loads the model, the scaler and the SHAP explainer and exposes them through a REST API (Appendix A). A React and TypeScript dashboard offers two modes: batch analysis of an uploaded flow CSV file or Wireshark capture, and a live feed that either replays a file or captures from a network interface. For display, the dashboard maps the fifteen CICIDS2017 classes to nine categories that follow CERT-In's grouping of incidents (Appendix B). Every prediction shows its class, confidence, prevention decision and, on request, its SHAP explanation; the dashboard distinguishes an action that was only recommended from one that was actually executed, and lists the blocked devices with a revoke control.

### 3.2.10 Evaluation Metrics

For each class k, precision P and recall R are computed from the true positives (TP), false positives (FP) and false negatives (FN) of that class:

::equation precision | 3.3

The F1 score is their harmonic mean:

::equation f1 | 3.4

Two averages over the K classes are reported. The macro F1 gives every class the same weight and therefore exposes failures on rare classes; the weighted F1 weights each class by its number of examples Nₖ:

::equation macro_weighted | 3.5

Accuracy is the fraction of correctly classified examples:

::equation accuracy | 3.6

Because benign traffic dominates both datasets, accuracy and weighted F1 stay high however the rare attacks fare, so macro F1 and the per-class F1 scores are the main measures of detection quality in this report.
