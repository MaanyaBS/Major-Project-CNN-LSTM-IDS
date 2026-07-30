# Status Report & Handoff Questions — Person B (Model Development)

## 1. Status Report

### Baseline Models
Trained and evaluated on a 100,000-row stratified sample of the cleaned CICIDS2017 dataset:
- **Logistic Regression**:
  - Accuracy: `98.86%`
  - Weighted F1: `0.9875`
  - Macro F1: `0.70`
- **Random Forest**:
  - Accuracy: `99.80%`
  - Weighted F1: `0.9977`
  - Macro F1: `0.85`

### CNN-LSTM Architecture & Pipeline
Modular deep learning pipeline implemented and verified end-to-end:
1. `model/load_data.py`: Chunk-based loading, filtering malformed rows (68 cols), infinity/NaN cleaning, label sanitisation.
2. `model/cnn_lstm_architecture.py`: Hybrid CNN-LSTM Keras model (`Conv1D` + `BN` + `MaxPool` → `Conv1D` + `BN` + `MaxPool` → `LSTM` → `Dropout` → `Dense`).
3. `model/sequence_reshaping.py`: Sliding-window transformer converting 2D tabular flow data `(samples, features)` into 3D temporal sequences `(samples, sequence_length, features)`.
4. `model/evaluate_model.py`: Automated evaluation module outputting text classification reports (`cnn_lstm_results.txt`) and confusion matrix heatmaps (`cnn_lstm_confusion_matrix.png`).

---

## 2. Important Catch (Data Integrity Issue)

- **Issue**: **780,373 rows** out of 2,655,060 (29.4%) in `datasets/merged/cicids2017_cleaned.csv` were malformed (contained 68 columns instead of 69, missing the `' Label'` column).
- **Root Cause**: `03_data_cleaning.py` dropped constant columns independently per raw file without aligning column schemas before `04_merge_cleaned_data.py` concatenated them.
- **Interim Fix**: `model/load_data.py` drops malformed rows to use only the **1,874,687 well-formed rows**.

---

## 3. Requirements from Person A (Data Preprocessing & Feature Pipeline)

1. **Schema Alignment**: Ensure all daily raw CSV files share an aligned, uniform column schema after cleaning before merging.
2. **Feature Scaling & Encoding**: Provide final preprocessed feature arrays or a reusable `StandardScaler` / `LabelEncoder` pipeline so sequence inputs match expected scaling during inference.
3. **Class Imbalance Handling**: Address severe minority classes (e.g. `Heartbleed`: 11 rows, `Web Attack - Sql Injection`: 21 rows, `Web Attack - XSS`: 652 rows) via SMOTE, class weights, or focused sampling.

---

## 4. Requirements from Person C (Frontend & API Integration)

1. **Backend Endpoint Contract**: Define API specification (e.g., FastAPI / Flask) to expose the trained CNN-LSTM model for real-time or batch network intrusion predictions.
2. **Payload Structure**: Align frontend UI network metric feeds with the feature vector structure expected by the model pipeline.
