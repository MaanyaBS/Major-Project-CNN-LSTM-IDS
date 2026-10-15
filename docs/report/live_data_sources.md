# Live Data Sources and Evaluation

## 1. Objective

This evaluation checks whether the ThreatLens Batch Analysis interface can accept flow-feature CSVs produced from packet captures, run the hybrid CNN-LSTM model, display predicted classes, and provide SHAP explanations. Prevention actions remain simulated; no real network blocking was attempted.

## 2. Data Sources and Capture Procedure

### Public botnet capture

- Converted file: `botnet_neris.flows.csv`
- Likely source: CTU-13 / Stratosphere Laboratory, inferred from the filename and IP addresses. The original PCAP was not available in this evaluation to independently confirm provenance.
- Dataset reference: https://www.stratosphereips.org/datasets-ctu13
- Licence/redistribution terms: must be confirmed against the applicable dataset terms before redistributing the capture or derived data.

### Locally generated traffic

The following captures were created locally using Wireshark on the testing computer and converted with `model/flow_features.py`:

- DNS traffic: `dns_fresh.pcapng` → `dns_fresh.flows.csv`
- TCP traffic: `tcp_fresh.pcapng` → `tcp_fresh.flows.csv`
- TCP window-scale test: `tcp_fresh.pcapng` → `tcp_window_scale.flows.csv`
- Download activity: `normal_download.pcapng` → `normal_download_new.flows.csv`
- Web browsing: `normal_web_browsing.flows.csv`
- YouTube activity: `normal_youtube.flows.csv`

The local PCAPNG files are personal test captures and must not be committed to the repository. The `tcp_window_scale.flows.csv` file was regenerated from the same `tcp_fresh.pcapng` capture, so it is not an independent capture.

## 3. Batch Analysis Results

Counts below are the dashboard results recorded during testing. CSV rows and analyzed sequences are different quantities because the application groups flow records into model windows.

| Capture file | Source | CSV rows | Sequences analyzed | Predicted normal | Predicted attacks | Attack rate | Actions recommended | Held for review | Actions executed | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `botnet_neris.flows.csv` | Public capture; likely CTU-13, not independently confirmed | 23,692 | 2,000 | 1,536 | 464 | 23.2% | 357 | 107 | 0 | Truncated at 2,000 sequences |
| `tcp_fresh.flows.csv` | Local TCP capture | 59 | 5 | 5 | 0 | 0.0% | 0 | 0 | 0 | All five windows predicted BENIGN |
| `tcp_window_scale.flows.csv` | Same local TCP capture as above | 59 | 5 | 5 | 0 | 0.0% | 0 | 0 | 0 | Regenerated from `tcp_fresh.pcapng`; not independent |
| `dns_fresh.flows.csv` | Local DNS capture | 59 | 5 | 5 | 0 | 0.0% | 0 | 0 | 0 | All five windows predicted BENIGN |
| `normal_download_new.flows.csv` | Local download activity | 9 | 3 | 3 | 0 | 0.0% | 0 | 0 | 0 | Small sample; interpret cautiously |
| `normal_web_browsing.flows.csv` | Local web-browsing activity | 423 | 423 | 362 | 61 | 14.4% | 43 | 18 | 0 | Predicted attacks included FTP-Patator and Web Attack classes |
| `normal_youtube.flows.csv` | Local YouTube activity | 33 | 33 | 30 | 3 | 9.1% | 3 | 0 | 0 | All three attack predictions were FTP-Patator |

The sequence counts and dashboard metrics above are recorded test observations. They are not a substitute for independently labelled ground truth.

## 4. Explanation Validation

SHAP explanations loaded successfully for the tested windows, and the dashboard reported an additivity check for the TCP test:

- Base value: 0.4552
- Sum of displayed contribution: 0.3970
- Model output: 0.8522
- Additivity error: approximately 1.5 × 10^-8

This indicates that the displayed feature contributions reconstructed the reported model score for that example, within numerical tolerance. It does not establish overall model accuracy.

## 5. Rejected Small Samples

The earlier files `dns_sample.flows.csv` and `tcp_sample.flows.csv` were rejected by Batch Analysis with the message: “Need at least 10 valid rows after cleaning.” The earlier `normal_download.flows.csv` was also too small for the intended evaluation. Fresh captures and the regenerated download sample were used for subsequent tests.

## 6. Findings and Limitations

1. The public botnet CSV produced attack predictions, but the application processed only the first 2,000 sequences. Results therefore describe the processed subset, not the complete file.
2. The dashboard predicted all five windows in the fresh TCP and DNS tests as BENIGN.
3. The download sample contained only three analyzed sequences and is too small to support broad conclusions.
4. Some windows in the locally generated web-browsing and YouTube tests were predicted as attacks. These may be false positives if the underlying traffic was benign, but this cannot be confirmed without independent labels and flow-level verification.
5. The botnet capture provenance and applicable redistribution licence have not been independently verified.
6. A zero count for executed actions means no real prevention action was attempted. Recommendations and review counts are policy-engine outputs, not evidence that traffic was blocked.
7. This evaluation tests data conversion, dashboard integration, predictions, and explanations. It is not a controlled benchmark of detection accuracy, recall, false-positive rate, or performance on zero-day attacks.
8. Locally captured PCAPNG files may contain private network metadata and must remain outside version control.

## 7. Reproducibility

The flow conversion was performed using the project's `model/flow_features.py` script. The resulting CSVs were uploaded through the ThreatLens Batch Analysis interface. The dashboard's reported sequence counts, class predictions, action counts, truncation status, and SHAP output were recorded manually.

For a formal accuracy evaluation, use independently labelled captures, document the label-to-flow mapping, and report a confusion matrix and class-wise precision, recall, and F1 score.
