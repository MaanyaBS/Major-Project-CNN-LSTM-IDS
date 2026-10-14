# PERSON A — MU-IoT DATA PIPELINE HANDOFF

## Project

Real-Time Explainable Hybrid CNN-LSTM Intrusion Detection System
with IoT-based Data Collection and Cloud Deployment

---

# 1. Dataset

Dataset:

MU-IoT

Canonical cleaned dataset:

D:\Major_Project\dataset\processed\mu_iot\mu_iot_cleaned.csv

Total cleaned rows:

24,171,263

Cleaned columns:

118

Target:

category

Metadata:

capture_session

Raw files:

40 CSV files

Capture sessions:

32

---

# 2. Final V3 Handoff

Final handoff directory:

D:\Major_Project\dataset\processed\mu_iot\handoff_v3

Final selected rows:

3,936,753

Final feature count:

38

Final feature matrix:

(3,936,753, 38)

Datatype:

float32

The final V3 handoff is constructed from the canonical cleaned dataset.

row_id represents the zero-based physical row position in:

D:\Major_Project\dataset\processed\mu_iot\mu_iot_cleaned.csv

---

# 3. Final Feature Selection

Feature-selection basis:

2024 IEEE Access MU-IoT paper
Table 8 — AverageRanking

The initial Table 8 feature set contained 48 ranked features.

Coverage/non-constant validation produced:

paper_top48_coverage95_nonconstant

with 40 features.

The following two features were then removed:

FPT
LPT

Final configuration key:

paper_top48_coverage95_nonconstant_38

Final feature count:

38

---

# 4. Final 38 Features

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

FPT and LPT are intentionally absent.

Feature metadata:

D:\Major_Project\dataset\processed\mu_iot\handoff_v3\feature_list_38.json

---

# 5. Final Split Strategy

Random row-level splitting was NOT used for the final V3 handoff.

Four complete capture sessions were reserved exclusively for:

test_heldout

Held-out sessions:

MU_SESSION_013
MU_SESSION_021
MU_SESSION_026
MU_SESSION_031

The remaining sessions were divided chronologically within each session into approximately:

70% → train
15% → validation
15% → test_within

Final split names:

train
val
test_within
test_heldout

Held-out sessions never appear in train, validation, or test_within.

---

# 6. Block Selection

The final V3 handoff uses complete temporal blocks.

Block rules:

- Preferred block size: 10,000 rows
- Minimum accepted block size: 20 rows
- Partial blocks are not used
- Blocks remain within one capture session
- Blocks remain within one split
- Blocks remain within one category
- Selected blocks do not overlap
- Row IDs are consecutive within selected blocks

The final package contains the block manifest:

D:\Major_Project\dataset\processed\mu_iot\handoff_v3\block_manifest.csv

---

# 7. Final Class Counts

| Split | Class | Rows |
|---|---|---:|
| train | DDoS | 496,750 |
| train | Injection | 165,355 |
| train | MiTM | 18,623 |
| train | Password_Hacking | 500,000 |
| train | Scan | 500,000 |
| train | Spyware | 95,071 |
| train | normal | 396,196 |
| val | DDoS | 99,261 |
| val | Injection | 35,433 |
| val | MiTM | 3,991 |
| val | Password_Hacking | 100,000 |
| val | Scan | 100,000 |
| val | Spyware | 20,373 |
| val | normal | 84,899 |
| test_within | DDoS | 149,984 |
| test_within | Injection | 35,435 |
| test_within | MiTM | 3,992 |
| test_within | Password_Hacking | 149,174 |
| test_within | Scan | 144,179 |
| test_within | Spyware | 20,373 |
| test_within | normal | 84,900 |
| test_heldout | DDoS | 200,000 |
| test_heldout | Injection | 132,764 |
| test_heldout | MiTM | 0 |
| test_heldout | Password_Hacking | 200,000 |
| test_heldout | Scan | 200,000 |
| test_heldout | Spyware | 0 |
| test_heldout | normal | 0 |

Split totals:

Train:

2,171,995

Validation:

443,957

Test within:

588,037

Test held-out:

732,764

Grand total:

3,936,753

Class-specific caps were applied during handoff construction.

---

# 8. Scaling

Scaler:

StandardScaler

The scaler was fitted using training rows only.

Validation and test rows were not used to fit the scaler.

Training rows used for scaler fitting:

2,171,995

Final scaler:

D:\Major_Project\dataset\processed\mu_iot\handoff_v3\scaler_38.pkl

This prevents evaluation data from influencing the normalization parameters.

---

# 9. CNN-LSTM Sequence Representation

Final sequence length:

20

Features per timestep:

38

Final model input:

(20, 38)

Therefore, the batch input shape is:

(batch_size, 20, 38)

Example:

(128, 20, 38)

Sequences must not cross:

- capture-session boundaries
- split boundaries
- category/block boundaries where the handoff metadata defines separate blocks

---

# 10. Handoff Metadata

The final V3 handoff contains:

README.md
class_counts_by_split.csv
block_manifest.csv
session_regions.json
split_regions.json
feature_list_38.json
label_mapping.json
scaler_38.pkl

Important metadata paths:

D:\Major_Project\dataset\processed\mu_iot\handoff_v3\class_counts_by_split.csv

D:\Major_Project\dataset\processed\mu_iot\handoff_v3\block_manifest.csv

D:\Major_Project\dataset\processed\mu_iot\handoff_v3\session_regions.json

D:\Major_Project\dataset\processed\mu_iot\handoff_v3\split_regions.json

D:\Major_Project\dataset\processed\mu_iot\handoff_v3\feature_list_38.json

D:\Major_Project\dataset\processed\mu_iot\handoff_v3\label_mapping.json

D:\Major_Project\dataset\processed\mu_iot\handoff_v3\scaler_38.pkl

Large NumPy arrays are not intended to be committed to Git.

---

# 11. Important Instructions for Person B

DO NOT:

1. Use the old 40-feature temporal pipeline as the final V3 experiment.

2. Use FPT or LPT.

3. Fit another scaler using validation or test data.

4. Randomly shuffle the complete cleaned dataset before temporal sequence construction.

5. Allow sequences to cross capture-session boundaries.

6. Allow sequences to cross train/validation/test boundaries.

7. Re-select a different feature set without team agreement.

8. Treat the four held-out sessions as training or validation data.

9. Assume every class must be represented in test_heldout; the held-out recording composition determines its class counts.

10. Load the complete feature array into RAM unnecessarily.

---

# 12. Data-Quality Notes

## Slowloris

The following two raw files contain exactly identical content:

Botnet_Slowloris.csv
Slowloris.csv

Both contain:

150,577 rows
124 columns

A complete dataframe comparison returned True.

Neither file contains a timestamp/date/time column.

Therefore, the CSV contents alone cannot establish that the two files represent independently distinguishable captures.

The established 40-file to 32-session mapping is retained, with this provenance limitation documented.

## DNS Amplification

MU_SESSION_002 corresponds to:

Botnet_DNS_amplification.csv

Raw size:

4,243 rows
124 columns

Category:

DDoS

The small representation of this recording in the final evaluation is therefore attributable to the small original recording size.

---

# 13. Final Status

DATA LOADING                  COMPLETE
DATA CLEANING                 COMPLETE
SESSION MAPPING               COMPLETE
FEATURE VALIDATION            COMPLETE
38-FEATURE SELECTION          COMPLETE
TEMPORAL BLOCK SELECTION      COMPLETE
TRAIN/VAL/TEST SPLIT          COMPLETE
HELD-OUT SESSION SPLIT        COMPLETE
TRAIN-ONLY SCALING            COMPLETE
V3 HANDOFF VALIDATION         COMPLETE
CLASS COUNT VALIDATION        COMPLETE
METADATA GENERATION            COMPLETE

PERSON A MU-IoT DATA HANDOFF:

COMPLETE AND READY FOR MODEL INTEGRATION

Final representation:

3,936,753 rows
38 features
20 timesteps
Input shape: (20, 38)
