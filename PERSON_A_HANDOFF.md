# PERSON A — MU-IoT DATA PIPELINE HANDOFF

## Project

Real-Time Explainable Hybrid CNN-LSTM Intrusion Detection System
with IoT-based Data Collection and Cloud Deployment

---

# 1. Dataset

Dataset:
MU-IoT

Cleaned dataset:

D:\Major_Project\dataset\processed\mu_iot\mu_iot_cleaned.csv

Total rows:

24,171,263

Original cleaned feature count:

118 columns

Target:

category

Metadata:

capture_session

---

# 2. Final Feature Selection

Feature-selection basis:

2024 IEEE Access MU-IoT paper
Table 8 — AverageRanking

Final selected features:

1. FPC
2. RTSP_ML
3. FPT
4. RTSP_MUL
5. ECE_FC
6. DNS_RCUL
7. FD
8. DNS_QTUL
9. RTSP_MM
10. DNS_RCL
11. DNSQTL
12. URG_FC
13. MQTT_MTUL
14. HTTP_SCL
15. ECN_M
16. MQTT_MTL
17. DSCP_S
18. ECN_S
19. TPackets
20. LPT
21. TCPWS_Mode
22. PLM
23. DSCP_M
24. TCPWS_Mean
25. BJitter
26. BThroughput
27. HL_Mode
28. TCPWS_Sum
29. MGA_UL
30. FAMax
31. FH_M
32. DSCP_UV
33. SDuration
34. FlowR
35. MGA_L
36. PacketsPS
37. FIMin
38. ECN_C
39. FAMean
40. RCount

Final feature count:

40

Configuration:

D:\Major_Project\config\mu_iot_feature_sets.json

Configuration key:

paper_top48_coverage95_nonconstant

---

# 3. Feature Quality Processing

The original Table 8 list contained 48 available ranked
features.

Coverage/non-constant validation was performed.

Features removed because of insufficient coverage:

DNS_RCM
RTSP_SETUPC
DNS_QTM
HTTPOptC
HTTP_SCM
HTTPPutC
HTTPPostC

ECN_UV was also removed because it was constant.

Final feature count:

40

No remaining constant features.

No remaining NaN values.

No remaining infinite values.

---

# 4. Temporal Split

Random row-level splitting was NOT used for the final experiment.

Final split method:

Within each capture session:

70% → Training
15% → Validation
15% → Test

Rows remain chronological.

Output:

D:\Major_Project\dataset\processed\mu_iot\mu_iot_temporal_split_assignment.csv

Final row counts:

Training:
16,919,867

Validation:
3,625,675

Testing:
3,625,721

Total:
24,171,263

---

# 5. Classes

Seven categories are present:

DDoS
Injection
MiTM
Password_Hacking
Scan
Spyware
normal

All seven classes are represented in the training data.

---

# 6. Scaling

Scaler:

StandardScaler

The scaler was fitted ONLY on chronological training rows.

Validation and test data were transformed using the
same training-fitted scaler.

Scaler:

D:\Major_Project\dataset\processed\mu_iot\scaler_temporal_paper_top48_coverage95_nonconstant.pkl

Feature configuration:

D:\Major_Project\dataset\processed\mu_iot\temporal_paper_top48_coverage95_nonconstant_features.json

Training rows used to fit scaler:

16,919,867

Features:

40

Missing values:

0

Infinite values:

0

---

# 7. Scaled Memmap

Scaled data is stored as a NumPy float32 memory-mapped file.

Path:

D:\Major_Project\dataset\processed\mu_iot\temporal_training_data\mu_iot_scaled_40features_float32.dat

Shape:

(24,171,263, 40)

Datatype:

float32

Approximate size:

3.60 GB

The complete dataset does NOT need to be loaded into RAM.

---

# 8. Temporal Sequence Representation

Sequence length:

20

Features per timestep:

40

Therefore:

X shape:

(batch_size, 20, 40)

Example:

(128, 20, 40)

Each sequence consists of 20 consecutive records.

Sequences are prevented from crossing:

- capture-session boundaries
- train/validation/test boundaries

---

# 9. Sequence Counts

Training:

16,919,259 sequences

Validation:

3,625,067 sequences

Testing:

3,625,113 sequences

---

# 10. Sequence Loader

Loader:

D:\Major_Project\scripts\mu_iot_stream_sequence_loader.py

The loader:

- reads the scaled memmap
- generates temporal sequences
- uses 20 consecutive records
- returns 40 features per timestep
- supports train/validation/test
- avoids loading the entire feature matrix into RAM
- checks sequence boundaries
- checks consecutive row IDs
- checks NaN/Inf
- verifies sequence shape

Validation result:

STREAMING SEQUENCE LOADER TEST PASSED

---

# 11. Verified Batch

Batch size:

128

X:

(128, 20, 40)

y:

(128,)

Validation:

PASS

---

# 12. Integrity Checks

Train:

PASS

Validation:

PASS

Test:

PASS

NaN/Inf:

PASS

Shape:

PASS

Consecutive rows:

PASS

Session boundary:

PASS

Split boundary:

PASS

---

# 13. Important Instructions for Person B

DO NOT:

1. Use the old random training subset as the final temporal experiment.

2. Fit another scaler on validation or test data.

3. Randomly shuffle the complete raw dataset before creating temporal sequences.

4. Allow sequences to cross capture-session boundaries.

5. Allow sequences to cross train/validation/test boundaries.

6. Re-select a different feature set without team agreement.

7. Load the complete 3.6 GB memmap into RAM unnecessarily.

---

# 14. CNN-LSTM Input

Final model input:

20 timesteps × 40 features

Input shape:

(20, 40)

Batch shape:

(batch_size, 20, 40)

Expected architecture concept:

Input
↓
1D CNN
↓
LSTM
↓
Dense
↓
Softmax
↓
7-class prediction

---

# 15. Person A Status

DATA LOADING                     COMPLETE
DATA CLEANING                   COMPLETE
FEATURE VALIDATION              COMPLETE
FEATURE SELECTION               COMPLETE
TEMPORAL SPLIT                  COMPLETE
TRAINING SCALER                 COMPLETE
SCALED MEMMAP                   COMPLETE
SEQUENCE SANITY TEST            COMPLETE
STREAMING SEQUENCE LOADER       COMPLETE
INTEGRITY VALIDATION             COMPLETE

PERSON A DATA PIPELINE:

COMPLETE AND READY FOR MODEL TRAINING