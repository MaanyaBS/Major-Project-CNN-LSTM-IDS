# Real-Time Explainable Hybrid CNN-LSTM Intrusion Detection System

## Project Overview

This project develops a real-time, explainable Intrusion Detection System (IDS) using a hybrid CNN-LSTM deep learning architecture.

The system is designed to detect network attacks by learning both:

* **Spatial patterns** in network traffic using Convolutional Neural Networks (CNN).
* **Temporal dependencies** across traffic sequences using Long Short-Term Memory (LSTM) networks.

The project uses two network-security datasets:

* **CICIDS2017** for general intrusion-detection evaluation.
* **MU-IoT** for IoT-focused, chronological and held-out-recording evaluation.

The final system also includes explainability using SHAP and a prevention-policy layer for recommended/simulated responses.

---

## Repository Layout

```text
Major-Project-CNN-LSTM-IDS/
│
├── config/                  # Project/configuration files
├── dataset/                 # Local datasets; not committed to Git
├── docs/                    # Project documentation and reports
│   └── report/
├── frontend/                # ThreatLens dashboard
├── model/                   # CNN-LSTM model, evaluation and interfaces
├── models/                  # Local/generated model files
├── notebooks/               # Jupyter notebooks and experiments
├── output/                  # Reproducible generated metadata and handoffs
│   └── mu_iot/
│       └── handoff_v3/
├── reports/                 # Generated analysis/report outputs
├── scripts/                 # Data analysis and handoff utilities
├── src/                     # Main data preparation pipeline
└── README.md
```

### Important

The raw and large processed datasets are intentionally excluded from Git. They should be stored locally or on the project's shared Drive.

The MU-IoT V3 metadata required to understand and reproduce the final split is committed under:

```text
output/mu_iot/handoff_v3/
```

The large `.npy` and `.npz` feature arrays are not committed.

---

## Data Pipeline

### 1. CICIDS2017

The CICIDS2017 pipeline prepares the network-flow data for chronological CNN-LSTM modelling.

The main stages are:

```text
Raw CICIDS2017 CSV files
        ↓
Data loading and EDA
        ↓
Cleaning and redundant-column removal
        ↓
Column-name correction
        ↓
Label encoding
        ↓
Feature selection
        ↓
Source-day / chronological ordering
        ↓
Train/validation/test preparation
```

Relevant scripts include:

```text
src/01_data_loading.py
src/02_basic_eda.py
src/03_data_cleaning.py
src/04_merge_cleaned_data.py
src/05a_fix_column_names.py
src/05_label_encoding.py
src/06_feature_selection.py
src/07_class_distribution.py
src/08a_train_validation_split.py
src/08_train_test_split.py
src/09_feature_scaling.py
```

The final day-aware CICIDS2017 dataset used by the model is:

```text
dataset/merged/cicids2017_cleaned_with_day.csv
```

The final dataset contains **2,655,060 rows and 70 columns**, including the attack label and `source_day`.

---

## 2. MU-IoT

The MU-IoT pipeline prepares IoT network traffic while preserving capture-session and chronological information.

The major stages are:

```text
40 raw CSV files
        ↓
Capture-session mapping
        ↓
Schema audit
        ↓
Cleaning and protocol-field conversion
        ↓
Feature analysis / selection
        ↓
Temporal block construction
        ↓
Train / validation / test split
        ↓
Held-out recording evaluation
        ↓
MU-IoT V3 handoff
```

Important scripts include:

```text
src/10_mu_iot_create_sessions.py.py
src/11_mu_iot_schema_audit.py
src/12_mu_iot_preprocess.py
src/13_feature_separability_analysis.py
```

Additional MU-IoT analysis and handoff utilities are located under:

```text
scripts/
```

### MU-IoT cleaning

The preprocessing includes:

* Removing completely empty columns.
* Removing constant columns.
* Removing the original `label` and `type` fields after deriving the required target.
* Encoding HTTP and RTSP method fields numerically.
* Converting source and destination IP information into derived numeric/network-property features.
* Preserving `category` as the target.
* Preserving `capture_session` for temporal and recording-level splitting.

---

## Final MU-IoT V3 Package

The final V3 package uses **38 selected features** and sequence windows of:

```text
20 timesteps × 38 features
```

The final feature matrix contains:

```text
3,936,753 rows × 38 features
```

The 38-feature selection is based on the paper's Table 8 ranking, with FPT and LPT removed from the final feature set.

The final handoff metadata is available at:

```text
output/mu_iot/handoff_v3/
```

It contains:

```text
README.md
class_counts_by_split.csv
block_manifest.csv
session_regions.json
split_regions.json
```

The large feature arrays and other generated training data remain outside Git.

---

## MU-IoT Split Strategy

The final package separates the data into:

* Training
* Validation
* Within-recording test
* Held-out-recording test

Four recordings are reserved for the held-out evaluation:

```text
MU_SESSION_013
MU_SESSION_021
MU_SESSION_026
MU_SESSION_031
```

The held-out recordings are kept completely separate from training and validation so that the model can be evaluated on recordings that were not seen during training.

The final sequence input is:

```text
(20, 38)
```

and the scaler is fitted using training data only.

---

## Running the Data Pipeline

Create/activate the project Python environment first.

From the repository root:

```powershell
cd D:\Major_Project
```

Activate the local environment if required:

```powershell
.\venv\Scripts\Activate.ps1
```

For CICIDS2017, run the required preparation scripts in their numbered pipeline order, starting with:

```powershell
python src\01_data_loading.py
```

and continue through the required cleaning, feature-selection, splitting and scaling stages.

For MU-IoT session creation and preprocessing:

```powershell
python src\10_mu_iot_create_sessions.py.py
python src\11_mu_iot_schema_audit.py
python src\12_mu_iot_preprocess.py
```

The more specialized validation, analysis and V3 handoff utilities are available in `scripts/`.

> Large dataset-processing steps can require substantial disk space and memory. The exact paths used by individual scripts should be checked before running them on a new machine.

---

## Model

The model, its evaluation, the prevention layer and all model-side results are under `model/`. Start with `docs/report/person_b_report.md`.

| | CICIDS2017 | MU-IoT |
|---|---|---|
| Input window | 10 flows × 20 features | 20 flows × 38 features |
| Classes | 15 | 7 |
| Model file | `model/artifacts/cnn_lstm_best_v2.keras` | `model/artifacts/mu_iot/best.keras` |
| How to use it | `model/MODEL_INTERFACE.md` | `model/MU_IOT_MODEL_INTERFACE.md` |
| CNN-LSTM | accuracy 0.984, macro F1 0.586 | unseen recordings: accuracy 0.680, macro F1 0.676 |
| Random forest, same test examples | accuracy 0.991, macro F1 0.780 | unseen recordings: macro F1 0.404 |

* On CICIDS2017 a single-flow random forest does better than the CNN-LSTM. On MU-IoT, where single flow records are often ambiguous, the CNN-LSTM is clearly better.
* Accuracy is dominated by benign traffic; macro F1 is the honest summary. Weak and rare classes, and other limitations, are listed in `model/MODEL_INTERFACE.md` (Section 6) and `docs/report/person_b_report.md` (Section 9).

Checks that run on a normal laptop:

```bash
python model/test_prevention.py        # 31 tests of the prevention policy and engine (no real firewall access)
python model/test_mu_iot_windows.py    # 8 tests of the MU-IoT windowing rules
python model/benchmark_inference.py    # CPU speed of both models
python model/evaluate_model.py         # CICIDS2017 evaluation (needs datasets/verify_run_ruthwik/)
```

Training, the MU-IoT evaluation, the baselines and the SHAP error analysis run in Google Colab; the commands are in `docs/report/person_b_report.md`, Section 10.

---

## Explainability and Prevention

The project includes:

* **SHAP-based explainability** to identify influential input features.
* **Threat classification** based on the CNN-LSTM prediction.
* **Prevention-policy logic** that maps detected threats to recommended actions; weak or data-starved classes always go to human review. Actions can be executed as real Windows Firewall rules, but only when `IDS_PREVENTION_EXECUTION_ENABLED` is set and only for RFC 5737 TEST-NET demo addresses (`model/PREVENTION_EXECUTION_INTERFACE.md`).
* **Audit logging** for prevention decisions.

These components are maintained primarily under the model and frontend portions of the repository.

---

## Dashboard

The ThreatLens frontend provides the user-facing security dashboard.

The dashboard is located under:

```text
frontend/
```

It presents model predictions, threat severity, explanations and prevention information in a security-monitoring interface.

---

## Data and Reproducibility Notes

* Raw datasets are not committed to Git.
* Large generated arrays are not committed to Git.
* The final MU-IoT V3 metadata is committed under `output/mu_iot/handoff_v3/`.
* Train-only scaling is used for the final MU-IoT package.
* Capture sessions are preserved to support chronological and held-out-recording evaluation.
* The final sequence format for MU-IoT is `(20, 38)`.

For detailed data methodology, see:

```text
docs/report/person_a_report.md
PERSON_A_HANDOFF.md
```
