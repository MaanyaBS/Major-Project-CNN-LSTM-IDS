# Backend — Flask API for CNN-LSTM IDS

Serves the trained CNN-LSTM v2 model (per `model/MODEL_INTERFACE.md`), SHAP
explanations, and the prevention policy to the frontend.

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python app.py
```

Server runs at `http://127.0.0.1:5000`.

## Endpoints

### `GET /api/health`
Model + SHAP load status and headline metrics.

### `GET /api/meta`
Feature columns (contract order), sequence length, dashboard categories,
label mapping, model metrics.

### `POST /api/predict`
Single sequence:
```json
{ "flows": [ { "Destination Port": 80, "...": 0 }, ... 10 rows ] }
```
Batch:
```json
{ "sequences": [ [ ...10 rows... ], [ ...10 rows... ] ] }
```
Returns per-sequence: predicted class, CERT-In category, confidence, full
15-class probability breakdown, prevention action/severity/status (from
`model/class_action_mapping.py`), and a `low_confidence_class` flag for the
known-weak classes.

### `POST /api/explain`
Body: `{ "flows": [...10 rows...] }`.
Returns SHAP attributions for the predicted class: per-feature shap values,
raw feature means, base value — enough data to render summary bar / waterfall /
force-style plots in the frontend.

### `POST /api/predict_csv`
Multipart form with a `file` field containing a CSV that includes all 20
feature columns. Windows the rows into 10-step sequences (max 2000 windows),
returns summary stats, class counts, timeline buckets for charts, and the
first 200 per-window results.

## Notes

- Scaling is applied row-wise with `scaler_v2.pkl` before windowing, exactly as
  the contract requires.
- The SHAP background distribution approximates the standardized training
  distribution (N(0,1) in scaled space) since raw training arrays are not in
  the repo. Swap in real background samples from `train.npy` when available.
- Sequence gaps across capture sessions (MODEL_INTERFACE.md §6) are not yet
  handled; CSV inference treats the file as one continuous stream. Documented
  as a known limitation.
