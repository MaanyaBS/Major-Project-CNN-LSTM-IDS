# Live Data Sources and Evaluation

## 1. Objective

This evaluation checks whether the ThreatLens Batch Analysis interface can accept flow-feature CSVs produced from packet captures, run the hybrid CNN-LSTM model, display predicted classes, and provide SHAP explanations. Prevention actions remain simulated; no real network blocking was attempted.

## 2. Data Sources and Capture Procedure

### 2.1 Public Neris Botnet Capture

- Original capture: `botnet-capture-20110810-neris.pcap`
- Converted file: `output/live_captures/botnet_neris_verified.flows.csv`
- Original PCAP size: approximately 55.57 MB.
- Converted CSV size: approximately 4.25 MB.
- Dataset reference: https://www.stratosphereips.org/datasets-ctu13
- Direct PCAP URL: https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-42/botnet-capture-20110810-neris.pcap
- Conversion script: `model/flow_features.py`
- Conversion result: 23,692 flow rows and 2,369 model windows of 10 flows each.
- Dashboard processing: 2,000 sequences were processed; the interface indicated that the input was truncated.
- Redistribution terms: The applicable dataset licence and redistribution conditions have not yet been independently confirmed. The original PCAP is kept outside the repository and must not be committed.
- Evaluation limitation: Dashboard classifications are model predictions and are not independently verified ground-truth labels.

The converted CSV was generated from the available original PCAP using the project's flow-feature extraction script. The dashboard results documented below refer to the verified CSV filename.

### 2.2 Locally Generated Traffic

The following captures were created locally using Wireshark on the testing computer and converted with `model/flow_features.py`:

- DNS traffic: `dns_fresh.pcapng` → `dns_fresh.flows.csv`
- TCP traffic: `tcp_fresh.pcapng` → `tcp_fresh.flows.csv`
- TCP window-scale test: `tcp_fresh.pcapng` → `tcp_window_scale.flows.csv`
- Download activity: `normal_download.pcapng` → `normal_download_new.flows.csv`
- Web browsing: `normal_web_browsing.flows.csv`
- YouTube activity: `normal_youtube.flows.csv`

The local PCAPNG files may contain private network metadata and must not be committed to the repository. The `tcp_window_scale.flows.csv` file was regenerated from the same `tcp_fresh.pcapng` capture, so it is not an independent capture.

## 3. Batch Analysis Results

The following counts are the dashboard observations recorded during testing. CSV rows and analyzed sequences are different quantities because the application groups flow records into model windows. The classifications shown are predictions, not verified labels.

| Capture file | Source | CSV rows | Sequences analyzed | Predicted normal | Predicted attacks | Attack rate | Actions recommended | Held for review | Actions executed | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `botnet_neris_verified.flows.csv` | Public Neris botnet capture | 23,692 | 2,000 | 1,536 | 464 | 23.2% | 357 | 107 | 0 | Converter produced 2,369 windows; dashboard truncated at 2,000 |
| `tcp_fresh.flows.csv` | Local TCP capture | 59 | 5 | 5 | 0 | 0.0% | 0 | 0 | 0 | All five windows predicted BENIGN |
| `tcp_window_scale.flows.csv` | Same local TCP capture | 59 | 5 | 5 | 0 | 0.0% | 0 | 0 | 0 | Regenerated from `tcp_fresh.pcapng`; not independent |
| `dns_fresh.flows.csv` | Local DNS capture | 59 | 5 | 5 | 0 | 0.0% | 0 | 0 | 0 | All five windows predicted BENIGN |
| `normal_download_new.flows.csv` | Local download activity | 9 | 3 | 3 | 0 | 0.0% | 0 | 0 | 0 | Small sample; interpret cautiously |
| `normal_web_browsing.flows.csv` | Local web-browsing activity | 423 | 423 | 362 | 61 | 14.4% | 43 | 18 | 0 | Predicted attacks included FTP-Patator and Web Attack classes |
| `normal_youtube.flows.csv` | Local YouTube activity | 33 | 33 | 30 | 3 | 9.1% | 3 | 0 | 0 | All three attack predictions were FTP-Patator |

The public Neris CSV contained 23,692 flow records, corresponding to 2,369 model windows at 10 flows per window. The dashboard processed only 2,000 sequences, leaving 369 windows outside the recorded analysis. The public-capture metrics therefore describe the processed subset.

The sequence counts and dashboard metrics are recorded test observations. They are not a substitute for independently labelled ground truth.

## 4. Explanation Validation

SHAP explanations loaded successfully for the tested windows. The dashboard reported the following additivity check for a TCP test:

- Base value: 0.4552
- Sum of displayed contributions: 0.3970
- Model output: 0.8522
- Additivity error: approximately 1.5 × 10⁻⁸

The displayed feature contributions reconstructed the reported model score for that example within numerical tolerance. This checks the numerical consistency of the explanation; it does not establish overall model accuracy.

### 4.1 SHAP Check for the Public Neris Capture

For dashboard window #41, which was predicted as FTP-Patator:

- Displayed confidence: approximately 86.8%.
- Model output: approximately 0.8677.
- Base value: approximately 0.0377.
- Sum of feature contributions: approximately 0.8301.
- Reported additivity error: approximately 2.1 × 10⁻¹⁰.
- Leading displayed contributors included Packet Length Std (+0.133), Bwd Packet Length Std (+0.107), Avg Fwd Segment Size (+0.102), Destination Port (+0.088), Packet Length Mean (+0.070), and Fwd Packet Length Max (+0.064).
- Recommended policy action: `block_ip`.
- Executed prevention actions: 0.

The `block_ip` result was a recommendation only. No actual network blocking was performed. The additivity check supports the numerical consistency of the explanation for this example but does not prove that the predicted class was correct.

## 5. Rejected Small Samples

The earlier files `dns_sample.flows.csv` and `tcp_sample.flows.csv` were rejected by Batch Analysis with the message:

> Need at least 10 valid rows after cleaning.

The earlier `normal_download.flows.csv` was also too small for the intended evaluation. Fresh captures and the regenerated download sample were used for subsequent tests.

## 6. Findings and Limitations

1. The public Neris botnet CSV produced both normal and attack predictions. However, the dashboard processed only the first 2,000 of 2,369 available windows.
2. All five windows in the fresh TCP test and all five windows in the fresh DNS test were predicted as BENIGN.
3. The download sample contained only three analyzed sequences and is too small to support broad conclusions.
4. Some windows in the locally generated web-browsing and YouTube tests were predicted as attacks. These may be false positives if the underlying traffic was benign, but this cannot be confirmed without independent labels and flow-level verification.
5. The public capture's source page is documented above, but the exact applicable redistribution terms have not been independently verified.
6. A zero count for executed actions means no real prevention action was attempted. Recommendation and review counts are policy-engine outputs, not evidence that traffic was blocked.
7. This evaluation tests data conversion, dashboard integration, predictions, and explanations. It is not a controlled benchmark of detection accuracy, recall, false-positive rate, or performance on zero-day attacks.
8. Locally captured PCAPNG files may contain private network metadata and must remain outside version control.
9. The public-capture predictions must not be interpreted as confirmed detection rates because independently verified labels were not used to calculate these metrics.
10. The two TCP-related CSV entries are not independent observations because they were generated from the same underlying capture.

## 7. Reproducibility

The flow conversion was performed using the project's `model/flow_features.py` script. The resulting CSV files were uploaded through the ThreatLens Batch Analysis interface. Dashboard sequence counts, predicted classes, action counts, truncation status, and SHAP outputs were recorded manually.

For a formal accuracy evaluation, use independently labelled captures, document the label-to-flow mapping, and report a confusion matrix alongside class-wise precision, recall, and F1 score. Evaluate false positives using traffic whose benign status is established independently.

## 8. Repository and Privacy Notes

- The public-derived flow CSV intended for this evaluation is `output/live_captures/botnet_neris_verified.flows.csv`.
- The original `.pcap` file is kept outside the repository.
- Private/local `.pcap` and `.pcapng` files must not be committed.
- Only the report and the intended public-derived flow CSV should be staged for this task.
- No files in the `model/` directory were changed as part of this report update.