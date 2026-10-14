# Person A — Dataset Preparation and Handoff Report

## 1. Overview

Person A was responsible for dataset acquisition, cleaning, feature preparation, session construction, temporal ordering, and preparation of the final training handoff for the CNN-LSTM intrusion detection pipeline.

Two datasets were prepared:

- **CICIDS2017** — used for the main IDS training pipeline.
- **MU-IoT** — used for IoT-specific validation and temporal/generalization experiments.

---

# 2. CICIDS2017 Dataset Preparation

## 2.1 Dataset Loading

The CICIDS2017 dataset was collected from the official CICIDS2017 capture files.

The dataset contains eight capture-day CSV files. The original files contained approximately 79 columns before preprocessing.

The preprocessing pipeline included:

1. Loading the individual CSV files.
2. Standardizing column names.
3. Handling missing values.
4. Removing duplicate rows.
5. Removing constant columns.
6. Encoding the target label.
7. Combining the cleaned files.
8. Adding the `source_day` field.
9. Selecting the final 20 model features.

## 2.2 Cleaning Results

The main cleaning statistics were:

| Capture | Raw Rows | Missing Rows Removed | Duplicate Rows Removed | Constant Columns Removed | Cleaned Rows |
|---|---:|---:|---:|---:|---:|
| Monday | 529,918 | 874 | 14,278 | 11 | 515,203 |
| Wednesday | 692,703 | 2,594 | 66,975 | 10 | 624,431 |

The final day-aware CICIDS2017 file is:

`dataset/merged/cicids2017_cleaned_with_day.csv`

It contains:

- **2,655,060 rows**
- **70 columns**
- `Label` column present
- `source_day` column present
- No missing target labels

The earlier malformed-row issue in which some rows lacked the expected `Label` field was resolved in the final day-aware dataset.

---

# 3. CICIDS2017 Feature Selection

## 3.1 Selection Method

The final CICIDS2017 feature set was selected using Random Forest feature importance.

The selection procedure was:

1. Load the encoded CICIDS2017 dataset.
2. Separate the `Label` target.
3. Randomly sample **100,000 rows** using `random_state=42`.
4. Train a `RandomForestClassifier` with:
   - `n_estimators=100`
   - `random_state=42`
   - `n_jobs=-1`
5. Calculate `feature_importances_`.
6. Sort features in descending order of importance.
7. Select the top 20 features.

This procedure is implemented in:

`src/06_feature_selection.py`

## 3.2 Final 20 Features

| Rank | Feature | Importance |
|---:|---|---:|
| 1 | Bwd Packet Length Mean | 0.056773 |
| 2 | Packet Length Variance | 0.054928 |
| 3 | Packet Length Std | 0.048950 |
| 4 | Average Packet Size | 0.045397 |
| 5 | Total Length of Bwd Packets | 0.042390 |
| 6 | Bwd Packet Length Std | 0.041585 |
| 7 | Bwd Packet Length Max | 0.041043 |
| 8 | Total Length of Fwd Packets | 0.040565 |
| 9 | Packet Length Mean | 0.039009 |
| 10 | Max Packet Length | 0.039000 |
| 11 | Subflow Fwd Bytes | 0.036560 |
| 12 | Avg Bwd Segment Size | 0.033499 |
| 13 | Fwd IAT Std | 0.030443 |
| 14 | Fwd Packet Length Mean | 0.023912 |
| 15 | Subflow Bwd Bytes | 0.021658 |
| 16 | Flow IAT Max | 0.021546 |
| 17 | Avg Fwd Segment Size | 0.021295 |
| 18 | Fwd Packet Length Max | 0.019947 |
| 19 | Destination Port | 0.017957 |
| 20 | Subflow Fwd Packets | 0.014876 |

---

# 4. CICIDS2017 Temporal Ordering

The original CICIDS2017 feature set did not provide a reliable timestamp column for the final training representation.

Therefore, the preserved row order within each original capture-day file was used as the available chronological ordering proxy.

Each row was tagged with a `source_day` value corresponding to its original capture-day file.

This allows the sequence-building process to distinguish different capture days and prevents a sequence window from crossing from one capture day into another.

The model-side chronological split uses:

- `source_day`
- original row position (`orig_idx`)
- label grouping
- chronological ordering within each source day

The final sequence construction therefore preserves the temporal order available from the original capture files rather than randomly shuffling rows.

---

# 5. MU-IoT Dataset Preparation

## 5.1 Raw Dataset

The MU-IoT dataset consisted of:

- **40 raw CSV files**
- Approximately **12.4 GB** of raw data
- **124 columns** before cleaning

The raw files were organized into attack and normal traffic recordings.

A session mapping process grouped the 40 files into **32 capture sessions**.

The resulting mapping is stored in:

`output/mu_iot/mu_iot_capture_sessions.csv`

The capture-session identifier is preserved as `capture_session` in the cleaned dataset.

---

# 6. MU-IoT Cleaning

The preprocessing pipeline processes the raw files in chunks and produces the canonical cleaned dataset:

`dataset/processed/mu_iot/mu_iot_cleaned.csv`

Final cleaned dataset:

- **24,171,263 rows**
- **118 columns**

## 6.1 Columns Removed

The following completely empty columns were removed:

- `HTTPDeletC`
- `HTTPPatchC`
- `HTTPTraceC`
- `HTTPConC`
- `RTSP_SPC`
- `RTSP_RecordC`
- `RTSP_RedirectC`
- `RTSP_PauseC`

Constant columns removed:

- `CE`
- `HTTPHeadC`
- `MQTT_MTM`
- `RTSP_OptionC`
- `RTSP_DESCC`
- `RTSP_TeardownC`
- `RTSP_PlayC`

The following target/leakage columns were also removed:

- `label`
- `type`

## 6.2 HTTP and RTSP Encoding

HTTP request methods were converted to compact integer representations using `HTTPRM_M`:

- GET → 0
- POST → 1
- OPTIONS → 2
- HEAD → 3
- PUT → 4
- DELETE → 5
- Unknown/missing → -1

RTSP methods were encoded using `RTSP_MM`:

- GET_PARAMETER → 0
- SETUP → 1
- OPTIONS → 2
- TEARDOWN → 3
- DESCRIBE → 4
- PLAY → 5
- Unknown/missing → -1

These encodings convert categorical protocol-method information into numeric features suitable for machine-learning processing.

## 6.3 IP Address Conversion

The original SIP and DIP fields were converted into numeric/indicator features.

For both source IP (`SIP`) and destination IP (`DIP`), the following six features were produced:

- private
- loopback
- multicast
- link-local
- first octet
- last octet

Invalid or missing addresses were represented using indicator values and `-1` for unavailable octet values.

The original SIP and DIP columns were then removed.

---

# 7. MU-IoT Feature Selection

The MU-IoT feature-selection process was based on the feature ranking reported in the reference paper's Table 8.

The initial Table 8 feature set contained 48 ranked features.

A feature-quality filtering stage produced the intermediate:

`paper_top48_coverage95_nonconstant`

feature set containing 40 features.

Two highly timing-related features were subsequently removed:

- `FPT`
- `LPT`

This produced the final **38-feature** set:

`paper_top48_coverage95_nonconstant_38`

The final feature list is:

1. FPC
2. RTSP_ML
3. RTSP_MUL
4. ECE_FC
5. DNS_RCUL
6. FD
7. DNS_QTUL
8. RTSP_MM
9. DNS_RCL
10. DNSQTL
11. URG_FC
12. MQTT_MTUL
13. HTTP_SCL
14. ECN_M
15. MQTT_MTL
16. DSCP_S
17. ECN_S
18. TPackets
19. TCPWS_Mode
20. PLM
21. DSCP_M
22. TCPWS_Mean
23. BJitter
24. BThroughput
25. HL_Mode
26. TCPWS_Sum
27. MGA_UL
28. FAMax
29. FH_M
30. DSCP_UV
31. SDuration
32. FlowR
33. MGA_L
34. PacketsPS
35. FIMin
36. ECN_C
37. FAMean
38. RCount

`FPT` and `LPT` are intentionally absent from the final set.

---

# 8. MU-IoT Block Construction

The final V3 handoff was constructed from the canonical cleaned dataset.

Important rules were applied during block selection:

- Complete blocks of **10,000 rows** were preferred.
- Minimum accepted block size was **20 rows**.
- Partial blocks were not used.
- A selected block remained within one session, split, and category.
- Row IDs correspond to physical row positions in the canonical cleaned CSV.
- Selected blocks do not overlap.
- Held-out sessions were isolated from the other splits.

The final feature matrix contains:

**3,936,753 rows × 38 features**

The stored feature matrix uses `float32`.

---

# 9. MU-IoT Split Strategy

Four complete capture sessions were held out exclusively for `test_heldout`:

- `MU_SESSION_013`
- `MU_SESSION_021`
- `MU_SESSION_026`
- `MU_SESSION_031`

The remaining sessions were split chronologically within each session into approximately:

- 70% training
- 15% validation
- 15% within-session testing

This produces four evaluation groups:

1. `train`
2. `val`
3. `test_within`
4. `test_heldout`

The held-out split is intended to evaluate behavior on recordings that were not used during training or validation.

---

# 10. MU-IoT Class Distribution

The final V3 handoff contains the following row counts.

| Class | Train | Validation | Test Within | Test Held-out |
|---|---:|---:|---:|---:|
| DDoS | 496,750 | 99,261 | 149,984 | 200,000 |
| Injection | 165,355 | 35,433 | 35,435 | 132,764 |
| MiTM | 18,623 | 3,991 | 3,992 | 0 |
| Password_Hacking | 500,000 | 100,000 | 149,174 | 200,000 |
| Scan | 500,000 | 100,000 | 144,179 | 200,000 |
| Spyware | 95,071 | 20,373 | 20,373 | 0 |
| normal | 396,196 | 84,899 | 84,900 | 0 |
| **Total** | **2,171,995** | **443,957** | **588,037** | **732,764** |

Total selected rows:

**3,936,753**

The training cap was applied where necessary, with maximum class-specific training selection of 500,000 rows.

---

# 11. Scaling

A `StandardScaler` was fitted using **training rows only**.

The scaler was not fitted using validation or test data.

This prevents information from the evaluation sets from influencing the normalization parameters.

The final scaler is stored as:

`scaler_38.pkl`

---

# 12. Data-Quality Findings

## 12.1 Slowloris Duplicate Content

Two MU-IoT files were found to contain exactly identical content:

- `Botnet_Slowloris.csv`
- `Slowloris.csv`

Both contain:

- 150,577 rows
- 124 columns

A complete dataframe comparison returned `True`, indicating identical contents.

Neither file contains a timestamp/date/time column. Therefore, the CSV contents alone do not provide evidence that these are two independently distinguishable captures.

The established 40-file to 32-session mapping was retained for the final handoff, while this provenance limitation is documented.

## 12.2 Small DNS Amplification Recording

`Botnet_DNS_amplification.csv`, corresponding to `MU_SESSION_002`, contains:

- 4,243 raw rows
- 124 columns
- DDoS category

Its relatively small representation in the held-out evaluation is therefore attributable to the small size of the original recording rather than an unexplained preprocessing loss.

---

# 13. Final Handoff Package

The final MU-IoT V3 handoff is located at:

`dataset/processed/mu_iot/handoff_v3/`

Important metadata files include:

- `README.md`
- `class_counts_by_split.csv`
- `block_manifest.csv`
- `session_regions.json`
- `split_regions.json`
- `feature_list_38.json`
- `label_mapping.json`
- `scaler_38.pkl`

The large feature arrays are kept outside Git tracking where appropriate.

---

# 14. Final Dataset Summary

| Dataset | Classes | Final Rows | Features Used | Main Purpose |
|---|---:|---:|---:|---|
| CICIDS2017 | 15 | 2,655,060 | 20 | Main IDS training pipeline |
| MU-IoT | 7 | 3,936,753 | 38 | IoT validation and temporal/generalization evaluation |

The prepared datasets preserve the required labels, temporal/session information, selected features, and split metadata for integration with the CNN-LSTM model and downstream explainability/dashboard components.
