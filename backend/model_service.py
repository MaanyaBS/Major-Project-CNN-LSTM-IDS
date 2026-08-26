import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

from class_action_mapping import get_action
from cert_in_mapping import get_cert_in_category, LOW_CONFIDENCE_CLASSES

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR.parent / "model" / "artifacts" / "cnn_lstm_best_v2.keras"
SCALER_PATH = BASE_DIR.parent / "model" / "artifacts" / "scaler_v2.pkl"
LABEL_MAP_PATH = BASE_DIR.parent / "model" / "artifacts" / "label_mapping_v2.json"

FEATURE_COLS = [
    'Destination Port', 'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
    'Fwd Packet Length Max', 'Fwd Packet Length Mean', 'Bwd Packet Length Max',
    'Bwd Packet Length Mean', 'Bwd Packet Length Std', 'Flow IAT Max', 'Fwd IAT Std',
    'Max Packet Length', 'Packet Length Mean', 'Packet Length Std', 'Packet Length Variance',
    'Average Packet Size', 'Avg Fwd Segment Size', 'Avg Bwd Segment Size',
    'Subflow Fwd Packets', 'Subflow Fwd Bytes', 'Subflow Bwd Bytes',
]

SEQ_LEN = 10
NUM_FEATURES = 20


class ModelService:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.int_to_label = {}
        self.loaded = False

    def load(self):
        from tensorflow import keras

        self.model = keras.models.load_model(MODEL_PATH)
        with open(SCALER_PATH, "rb") as f:
            self.scaler = pickle.load(f)
        with open(LABEL_MAP_PATH) as f:
            label_to_int = json.load(f)
        self.int_to_label = {v: k for k, v in label_to_int.items()}
        self.loaded = True

    def _rows_to_raw(self, flow_rows):
        if len(flow_rows) != SEQ_LEN:
            raise ValueError(f"Expected {SEQ_LEN} flow rows for one sequence, got {len(flow_rows)}")
        try:
            return np.array(
                [[float(row[col]) for col in FEATURE_COLS] for row in flow_rows],
                dtype="float32",
            )
        except KeyError as e:
            raise ValueError(f"Missing feature column in input: {e}") from e
        except (TypeError, ValueError) as e:
            raise ValueError(f"Non-numeric feature value in input: {e}") from e

    def predict_matrix(self, X_raw):
        X_df = pd.DataFrame(X_raw, columns=FEATURE_COLS)
        X_scaled = self.scaler.transform(X_df).astype("float32")
        n_seq = len(X_scaled) // SEQ_LEN
        if n_seq == 0:
            raise ValueError("Not enough rows to form one sequence")
        X_seq = X_scaled[: n_seq * SEQ_LEN].reshape(n_seq, SEQ_LEN, NUM_FEATURES)
        probs = self.model.predict(X_seq, verbose=0)
        return probs

    def predict_one(self, flow_rows):
        X_raw = self._rows_to_raw(flow_rows)
        probs = self.predict_matrix(X_raw)[0]
        return self._build_result(probs)

    def predict_batch(self, sequences):
        mats = [self._rows_to_raw(seq) for seq in sequences]
        X_raw = np.vstack(mats)
        probs = self.predict_matrix(X_raw)
        return [self._build_result(p) for p in probs]

    def _build_result(self, probs):
        pred_idx = int(np.argmax(probs))
        predicted_class = self.int_to_label[pred_idx]
        confidence = float(probs[pred_idx])
        prevention = get_action(predicted_class, confidence)
        return {
            "predicted_class": predicted_class,
            "cert_in_category": get_cert_in_category(predicted_class),
            "confidence": confidence,
            "probabilities": {
                self.int_to_label[i]: float(p) for i, p in enumerate(probs)
            },
            "prevention": prevention,
            "low_confidence_class": predicted_class in LOW_CONFIDENCE_CLASSES,
        }


service = ModelService()
