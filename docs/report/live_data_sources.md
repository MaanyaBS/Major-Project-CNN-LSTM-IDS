# Public PCAP Evaluation and Live Data Sources

## 1. Objective

This document records the evaluation of publicly available packet captures using the project's packet-to-flow feature extraction pipeline and ThreatLens dashboard.

The objectives are to:

- Test whether the flow extraction pipeline can process public PCAP and PCAPNG files.
- Convert packet captures into flow-level features compatible with the project's model input format.
- Evaluate ThreatLens Batch Analysis on both candidate normal traffic and attack-labelled traffic.
- Review predicted attack classes, confidence scores, severity, recommended prevention policies, and SHAP explanations.
- Identify potential false alarms, compatibility issues, and limitations when applying the trained model to traffic from sources other than its training dataset.

The results in this report describe observed model outputs. They do not establish real-world detection accuracy unless independent ground-truth labels and a proper evaluation are available.

## 2. Evaluation Methodology

The evaluation followed this workflow:

1. Obtain candidate PCAP or PCAPNG files from public dataset sources.
2. Keep the original captures outside the project repository.
3. Run the project's `model/flow_features.py` feature extractor on each suitable capture.
4. Save the derived flow CSV files in a local working directory.
5. Upload the derived CSV files to the ThreatLens Batch Analysis interface.
6. Record the number of extracted flows, generated model windows, processed sequences, predicted classes, attack-prediction ratio, and prevention recommendations.
7. Inspect selected predictions and their SHAP explanations.
8. Record any truncation, insufficient sample size, source-label uncertainty, or other limitations.

The feature extractor groups flows into model windows. In the evaluations below, the reported window counts are based on the generated CSV files and the project's current processing configuration.

The dashboard's predicted attack ratio is the proportion of processed windows classified as attacks. It must not be interpreted as recall, precision, accuracy, or a verified attack detection rate.

## 3. Public Data Sources

### 3.1 CTU-13 Botnet Dataset

- Dataset information: https://www.stratosphereips.org/datasets-ctu13
- Capture 42 PCAP: https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-42/botnet-capture-20110810-neris.pcap
- Capture 43 PCAP: https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-43/botnet-capture-20110811-neris.pcap

Two captures associated with the Neris botnet family were processed. Since both captures represent the same broad malware family, they should not be counted as two independent attack-family evaluations.

### 3.2 Wireshark Wi-Fi Capture

A local Wireshark capture, `Wifi_wireshark.pcapng`, was processed as a small candidate traffic sample.

- Original local file: `D:\PublicPCAPs\Wifi_wireshark.pcapng`
- File format: PCAPNG
- Source attribution and independent ground-truth labels: not confirmed in this evaluation.

This sample is useful for checking whether the pipeline accepts a PCAPNG file, but its predicted labels cannot be treated as confirmed attacks or confirmed false positives without validating the capture's provenance and contents.

### 3.3 SHIELD-i46 Dataset

- Public repository: https://github.com/i46-projects/SHIELD-i46

The following files were selected from the downloaded dataset:

- `normal-3_LAN.pcap`
- `5G_DDOS.pcap`

The dataset also contained other captures, but not all were suitable for this evaluation. Some files were extremely small and produced no model windows. Several files were only 2 bytes and appeared to be incomplete placeholders; these were excluded. An incomplete `.crdownload` file was also excluded.

The original PCAP files and extracted dataset directory remained in the local working directory rather than being added to the Git repository.

**Licence note:** The applicable licence and redistribution permissions for the individual capture files have not yet been independently verified. The original captures should not be redistributed through the project repository until those permissions are confirmed.

## 4. Evaluation Results

### 4.1 CTU-13 Neris Capture 42

**Original capture:** `botnet-capture-20110810-neris.pcap`

**Local paths**

- Original PCAP: `D:\PublicPCAPs\botnet-capture-20110810-neris.pcap`
- Derived CSV: `D:\PublicPCAPs\botnet_neris_verified.flows.csv`

**Extraction results**

| Metric | Result |
|---|---:|
| Original PCAP size | 58,266,506 bytes |
| Extracted flows | 23,692 |
| Generated model windows | 2,369 |
| Derived CSV size | 4,455,144 bytes |
| Windows processed by dashboard | 2,000 |
| Dashboard processing truncated | Yes |

The dashboard processed 2,000 windows and did not process the remaining 369 generated windows in this run.

**Dashboard predictions**

| Metric | Result |
|---|---:|
| Windows predicted normal | 1,536 |
| Windows predicted as attacks | 464 |
| Predicted attack ratio | 23.2% |
| Distinct predicted classes observed | 12 |
| Prevention actions recommended | 357 |
| Held for analyst review | 107 |
| Prevention actions executed | 0 |

Predicted classes included `BENIGN`, `DDoS`, `FTP-Patator`, `Bot`, `DoS slowloris`, `Web Attack XSS`, `Web Attack Brute Force`, `DoS GoldenEye`, `Infiltration`, `DoSSlowhttptest`, `PortScan`, and `SSH-Patator`.

These are model predictions, not independently verified labels for every window.

**Selected prediction and explanation**

One inspected window, window 41, was classified as `FTP-Patator` with a confidence score of approximately 86.8%. The dashboard displayed a high-severity result and recommended the `block_ip` policy.

The prevention system was operating in recommendation-only mode. No actual blocking was performed.

The recorded SHAP additivity check was:

- Base value: approximately 0.0377
- Sum of feature contributions: approximately 0.8301
- Model output: approximately 0.8677
- Additivity error: approximately 2.1e-10

Leading positive contributors in the inspected explanation included:

- Packet Length Std
- Bwd Packet Length Std
- Avg Fwd Segment Size
- Destination Port
- Packet Length Mean
- Fwd Packet Length Max

**Interpretation**

The capture successfully passed through flow extraction and dashboard analysis. The dashboard produced varied predictions and an inspectable explanation for a selected high-confidence attack prediction.

However, the run was truncated, and independent window-level ground truth was not used to calculate classification metrics. The results therefore demonstrate pipeline operation and model behaviour, not a verified 23.2% attack prevalence or a measured detection rate.

### 4.2 CTU-13 Neris Capture 43

**Original capture:** `botnet-capture-20110811-neris.pcap`

**Local paths**

- Original PCAP: `D:\PublicPCAPs\botnet-capture-20110811-neris.pcap`
- Derived CSV: `D:\PublicPCAPs\neris_20110811.flows.csv`

**Extraction results**

| Metric | Result |
|---|---:|
| Original PCAP size | 36,261,479 bytes |
| Extracted flows | 30,657 |
| Generated model windows | 3,065 |
| Derived CSV size | 5,446,223 bytes |
| Windows processed by dashboard | 2,000 |
| Dashboard processing truncated | Yes |

**Dashboard predictions**

| Metric | Result |
|---|---:|
| Windows predicted normal | 1,921 |
| Windows predicted as attacks | 79 |
| Predicted attack ratio | 4.0% |
| Distinct predicted classes observed | 13 |
| Prevention actions recommended | 17 |
| Held for analyst review | 62 |
| Prevention actions executed | 0 |

The dashboard's top threat category was `FTP-Patator`.

One inspected prediction, window 29, was classified as `FTP-Patator` with approximately 77.16% confidence. The displayed policy was `block_ip`, with high severity. The event was treated as a recommendation rather than an executed prevention action.

**SHAP explanation**

The recorded additivity check was:

- Base value: approximately 0.0377
- Sum of feature contributions: approximately 0.7339
- Model output: approximately 0.7716
- Additivity error: approximately 2.1e-10

Leading contributors in the inspected explanation included Average Packet Size, Packet Length Std, Destination Port, Bwd Packet Length Std, Avg Bwd Segment Size, and Flow IAT Max.

**Interpretation**

Capture 43 also passed through the flow extraction and dashboard pipeline. Its predicted attack ratio was lower than that of Capture 42, despite both captures being associated with the Neris botnet family.

This difference demonstrates that predictions can vary between captures from the same broad source or family. It does not establish that Capture 43 contained fewer attacks than Capture 42, because a ground-truth comparison was not completed.

Both CTU-13 runs were truncated to 2,000 windows. They should therefore be described as partial dashboard evaluations.

### 4.3 Wireshark Wi-Fi PCAPNG Capture

**Original capture:** `Wifi_wireshark.pcapng`

**Derived CSV:** `D:\PublicPCAPs\wifi_test.flows.csv`

| Metric | Result |
|---|---:|
| Original capture size | 3,178,224 bytes |
| Extracted flows | 77 |
| Generated model windows | 7 |
| Windows processed | 7 |
| Dashboard processing truncated | No |
| Windows predicted normal | 6 |
| Windows predicted as attacks | 1 |
| Predicted attack ratio | 14.3% |
| Distinct predicted classes observed | 2 |
| Prevention actions recommended | 0 |
| Prevention actions executed | 0 |
| Events held for review | 1 |

The dashboard classified the highest-risk inspected window, window 5, as `Web Attack - XSS` with approximately 37.93% confidence.

The displayed class probabilities were approximately:

| Predicted class | Probability |
|---|---:|
| Web Attack - XSS | 37.93% |
| Web Attack Brute Force | 33.43% |
| BENIGN | 26.92% |

The dashboard displayed the `sanitize_input` policy and high severity, but the event was held for analyst review. No prevention action was executed.

**SHAP explanation**

The recorded additivity check was:

- Base value: approximately 0.0401
- Sum of feature contributions: approximately 0.3393
- Model output: approximately 0.3793
- Additivity error: approximately 1.9e-9

Leading contributors in the inspected explanation included Fwd IAT Std, Packet Length Mean, Avg Fwd Segment Size, Fwd Packet Length Mean, Bwd Packet Length Mean, and Fwd Packet Length Max.

**Interpretation**

The small PCAPNG capture was accepted by the pipeline and produced seven model windows. The dashboard flagged one window, but the highest predicted class had only 37.93% confidence, and the alternative class probabilities were also substantial.

Because the capture's provenance and ground-truth labels have not been verified, this result cannot be described as a confirmed XSS attack or a confirmed false positive. The small sample size also limits the conclusions that can be drawn.

### 4.4 SHIELD-i46 Normal LAN Capture

**Original capture:** `normal-3_LAN.pcap`

**Derived CSV:** `D:\PublicPCAPs\shield_normal_lan.flows.csv`

| Metric | Result |
|---|---:|
| Original capture size | 2,246,772 bytes |
| Extracted flows | 1,056 |
| Generated model windows | 105 |
| Windows processed | 105 |
| Dashboard processing truncated | No |
| Windows predicted normal | 104 |
| Windows predicted as attacks | 1 |
| Predicted attack ratio | Approximately 1.0% |
| Distinct predicted classes observed | 2 |
| Prevention actions recommended | 0 |
| Prevention actions executed | 0 |
| Events held for review | 1 |

The dashboard classified window 82 as `Bot` with approximately 61.68% confidence. The `BENIGN` probability was approximately 38.20%, with the remaining listed class probabilities very small.

The dashboard displayed a high-severity result and an `isolate host` policy recommendation. The event was held for analyst review; no prevention action was executed.

**SHAP explanation**

The recorded additivity check was:

- Base value: approximately 0.0323
- Sum of feature contributions: approximately 0.5845
- Model output: approximately 0.6168
- Additivity error: approximately 1.8e-10

Leading contributors included Destination Port, Packet Length Mean, Average Packet Size, Fwd Packet Length Mean, and Avg Fwd Segment Size.

**Interpretation**

The dashboard predicted one attack window out of 105 in this candidate normal-LAN capture. If the source label and contents are confirmed to represent benign traffic, that window would be a candidate false alarm for further investigation.

Until that confirmation is completed, the result should be described as an attack prediction on a capture labelled normal, rather than a definitively measured false positive. The capture's label does not replace independent verification of the exact window-level ground truth.

### 4.5 SHIELD-i46 5G DDoS Capture

**Original capture:** `5G_DDOS.pcap`

**Derived CSV:** `D:\PublicPCAPs\shield_5g_ddos.flows.csv`

| Metric | Result |
|---|---:|
| Original capture size | 6,382,999 bytes |
| Extracted flows | 28,499 |
| Generated model windows | 2,849 |
| Windows processed | 2,000 |
| Dashboard processing truncated | Yes |
| Windows not processed in this run | 849 |
| Windows predicted normal | 116 |
| Windows predicted as attacks | 1,884 |
| Predicted attack ratio | 94.2% |
| Prevention actions recommended | 1,544 |
| Held for analyst review | 340 |
| Prevention actions executed | 0 |

The most prominent predicted threat was `DoS GoldenEye`. Other predictions included `DoS Hulk`, `DDoS`, and `BENIGN`.

One inspected window, window 6, was classified as `DoS Hulk` with approximately 51.99% confidence, while the `BENIGN` probability was approximately 39.49%. The displayed policy was `rate limit`, with high severity. The dashboard did not execute the action.

**SHAP explanation**

The recorded additivity check was:

- Base value: approximately 0.0412
- Sum of feature contributions: approximately 0.4787
- Model output: approximately 0.5199
- Additivity error: approximately 9.3e-10

Leading contributors included Destination Port, Fwd Packet Length Max, Fwd Packet Length Mean, Avg Fwd Segment Size, and Average Packet Size.

**Interpretation**

The model predicted attacks for 94.2% of the 2,000 processed windows from the DDoS-labelled capture. This is consistent with the capture being selected as an attack-traffic test case, but it is not a measured recall or accuracy score.

The dashboard did not process 849 generated windows in this run. A complete evaluation would require processing all windows and comparing the predictions against independently verified labels.

## 5. Summary of Results

| Capture | Generated windows | Processed windows | Predicted attack ratio | Truncated? |
|---|---:|---:|---:|---|
| CTU-13 Neris Capture 42 | 2,369 | 2,000 | 23.2% | Yes |
| CTU-13 Neris Capture 43 | 3,065 | 2,000 | 4.0% | Yes |
| Wireshark Wi-Fi PCAPNG | 7 | 7 | 14.3% | No |
| SHIELD-i46 Normal LAN | 105 | 105 | 1.0% | No |
| SHIELD-i46 5G DDoS | 2,849 | 2,000 | 94.2% | Yes |

The evaluation confirms that the current feature extraction and dashboard pipeline processed several public or candidate public captures, including PCAP and PCAPNG formats. The runs also produced class predictions, severity levels, prevention recommendations, and inspectable SHAP explanations.

The predicted attack ratios are descriptive dashboard outputs. They must not be compared directly as model accuracy metrics because the captures differ in source, traffic composition, sample size, and processing completeness.
## 6. Earlier Locally Captured Traffic Tests

In addition to the public and candidate-public captures described above, locally generated traffic was captured with Wireshark and processed using `model/flow_features.py`. These tests were used to check compatibility between the flow extractor, ThreatLens Batch Analysis, and the prediction pipeline.

The historical results below are retained as dashboard observations. Their original flow CSV files were not available during the latest audit, so the recorded row counts and prediction counts could not be independently reproduced.

| Capture CSV | Historical row count | Historical BENIGN predictions | Historical attack predictions | Reported attack ratio |
|---|---:|---:|---:|---:|
| `tcp_window_scale.flows.csv` | 59 | 5 | 0 | 0.0% |
| `dns_fresh.flows.csv` | 59 | 5 | 0 | 0.0% |
| `normal_download_new.flows.csv` | 9 | 3 | 0 | 0.0% |
| `normal_web_browsing.flows.csv` | 423 | 362 | 61 | 14.4% |
| `normal_youtube.flows.csv` | 33 | 30 | 3 | 9.1% |

**Sequence-count clarification:** The current inference implementation uses windows of 10 consecutive flows with a stride of one flow. A capture containing *N* valid flows produces *N − 9* prediction windows when *N* ≥ 10. Thus, 423 flows would produce 414 windows, and 33 flows would produce 24 windows. The historical prediction totals of 423 and 33 do not match those expected window counts if the reported row counts represent flows. Because the original historical flow CSVs are unavailable for independent verification, those historical prediction totals are retained only as unverified dashboard observations and must not be interpreted as validated sequence counts.

### 6.1 Normal Browsing Capture — October 15, 2026

The processed capture `normal_browsing_10min_v2.flows.csv` was generated from the local capture file `captures/normal_browsing_10min_v2.pcapng`.

| Measurement | Observed result |
|---|---:|
| Valid flow records | 3,010 |
| Rows excluded for invalid feature values | 0 |
| Window length | 10 flows |
| Window stride | 1 flow |
| Prediction windows | 3,001 |
| Observed flow-time span | 617.41 seconds |
| Mean maximum-class confidence | 0.776876 |
| Median maximum-class confidence | 0.758773 |

Predicted class counts:

| Predicted class | Windows |
|---|---:|
| BENIGN | 2,431 |
| FTP-Patator | 544 |
| Web Attack - Sql Injection | 24 |
| DoS slowloris | 1 |
| Web Attack - XSS | 1 |

**Limitations:** this capture has no ground-truth labels. These figures describe model outputs, not accuracy, precision, recall, or a measured false-positive rate. The observed flow-time span does not by itself establish uninterrupted packet capture. The capture's network environment and exact capture start/end times should be recorded only if supported by capture metadata or contemporaneous notes. Local packet captures and derived flow CSVs must be reviewed for sensitive information before sharing or committing them.
## 7. SHAP and Prevention Behaviour

SHAP explanations were inspected for selected windows from the five captures. The recorded additivity errors were very small, ranging from approximately 1.8e-10 to 1.9e-9 in the selected checks.

This indicates that the recorded SHAP contributions approximately reconstruct the inspected model outputs. It does not, by itself, prove that the underlying prediction is correct or that each feature has a causal relationship with an attack.

The inspected explanations repeatedly included features such as Destination Port, packet-length statistics, segment sizes, and inter-arrival-time statistics. These features may influence the model's predictions, but their importance can vary with the traffic window and predicted class.

Across the recorded runs, prevention policies included `block_ip`, `sanitize_input`, `isolate host`, and `rate limit`. These were dashboard recommendations only. The evaluation did not establish that any real network host was blocked, isolated, or rate-limited.

## 8. Limitations and Follow-up Work

### 8.1 Ground-truth validation

The dashboard's predicted class is not the same as the capture's verified label. In particular, an attack prediction on a candidate normal capture is not sufficient evidence of a false positive unless the source label and relevant traffic window are verified.

Future evaluation should use independently validated labels and report a confusion matrix, precision, recall, F1-score, and false-positive rate wherever the necessary ground truth is available.

### 8.2 Truncated evaluations

The CTU-13 Capture 42, CTU-13 Capture 43, and SHIELD-i46 5G DDoS runs processed 2,000 windows each and were truncated. Results describe only the processed subset.

The remaining generated windows should be evaluated before making conclusions about an entire capture.

### 8.3 Small samples

The Wi-Fi PCAPNG capture generated only seven model windows. Such a small sample is useful for checking basic pipeline compatibility but is insufficient for drawing reliable conclusions about model performance.

### 8.4 Dataset and feature compatibility

Public captures can differ substantially from the dataset used to train the model. Differences in protocols, traffic distributions, feature availability, flow duration, and capture conditions may cause out-of-distribution predictions.

The current results should therefore be treated as an integration and exploratory generalisation check, not as proof that the model will achieve the same performance on arbitrary live networks.

### 8.5 SHAP interpretation

SHAP additivity verifies the numerical consistency of the explanation with the inspected model output. It does not establish prediction correctness, causal attribution, or operational safety.

### 8.6 Dataset licence and provenance

Before redistributing any derived artifacts, document the source, relevant licence terms, and redistribution permissions. The licence for the individual CTU-13 and SHIELD-i46 capture files has not yet been independently confirmed as part of this evaluation.

The Wireshark Wi-Fi capture's provenance and ground-truth status also remain unconfirmed.

### 8.7 Recommended next steps

1. Confirm source labels and licensing terms for every capture used in the report.
2. Evaluate the remaining 849 windows from the SHIELD-i46 5G DDoS run and the unprocessed windows from the CTU-13 runs.
3. Inspect additional windows from the candidate normal capture to understand the `Bot` prediction.
4. Compare model predictions against validated labels wherever available.
5. Record reproducible commands, software versions, and dashboard settings.
6. Continue to use recommendation-only prevention mode during exploratory testing.
7. Avoid claiming a measured false-positive rate, detection rate, or overall accuracy until a proper ground-truth evaluation is complete.

## 9. Repository and Privacy Notes

The original packet captures were kept in the local working directory `D:\PublicPCAPs` and were not intended to be committed to the project repository.

The public-derived flow CSVs created during these experiments were also kept outside the repository during the evaluation. Any decision to commit a small derived artifact should be made separately after checking its size, provenance, licensing conditions, and privacy implications.

Do not commit private network captures, credentials, session tokens, personal information, or traffic collected from networks without appropriate permission.

The report records the observed results and limitations so that the project team can reproduce the evaluation and distinguish pipeline validation from verified model-performance measurement.

**Current evaluation status:** Public-capture pipeline testing completed for the five captures documented above. Full-capture processing, independent ground-truth validation, source-licence confirmation, and formal performance-metric calculation remain outstanding.
