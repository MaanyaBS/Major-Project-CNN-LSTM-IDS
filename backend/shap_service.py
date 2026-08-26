import numpy as np
import pandas as pd

from model_service import service, SEQ_LEN, NUM_FEATURES, FEATURE_COLS

BACKGROUND_SEQUENCES = 32
MAX_EXPLAIN_FEATURES = 20


class ShapService:
    def __init__(self):
        self.explainer = None
        self.background = None
        self.ready = False

    def init(self):
        import shap

        rng = np.random.default_rng(42)
        self.background = rng.standard_normal(
            (BACKGROUND_SEQUENCES, SEQ_LEN, NUM_FEATURES)
        ).astype("float32")
        self.explainer = shap.GradientExplainer(service.model, self.background)
        self.ready = True

    def explain(self, flow_rows, max_display=MAX_EXPLAIN_FEATURES):
        X_raw = service._rows_to_raw(flow_rows)
        return self.explain_matrix(X_raw, max_display=max_display)

    def explain_matrix(self, X_raw, max_display=MAX_EXPLAIN_FEATURES):
        if not self.ready:
            raise RuntimeError("SHAP explainer not initialized")

        X_scaled = service.scaler.transform(
            pd.DataFrame(X_raw, columns=FEATURE_COLS)
        ).astype("float32")
        X_seq = X_scaled[np.newaxis, :, :]

        probs = service.model.predict(X_seq, verbose=0)[0]
        pred_idx = int(np.argmax(probs))

        shap_values = self.explainer.shap_values(X_seq)
        sv = np.asarray(shap_values)

        if sv.ndim == 5:
            sv = sv[0]
        if sv.shape[0] == 1:
            sv = sv[0]

        if sv.ndim == 3 and sv.shape[-1] == len(probs):
            class_sv = sv[:, :, pred_idx]
        elif sv.ndim == 3 and sv.shape[0] == len(probs):
            class_sv = sv[pred_idx]
        else:
            raise RuntimeError(f"Unexpected SHAP output shape: {sv.shape}")

        feature_attr = class_sv.mean(axis=0)
        raw_means = X_raw.mean(axis=0)

        order = np.argsort(-np.abs(feature_attr))
        attributions = [
            {
                "feature": FEATURE_COLS[i],
                "shap_value": float(feature_attr[i]),
                "abs_shap_value": float(abs(feature_attr[i])),
                "raw_value_mean": float(raw_means[i]),
            }
            for i in order[:max_display]
        ]

        bg_preds = service.model.predict(self.background, verbose=0)
        base_value = float(bg_preds[:, pred_idx].mean())

        return {
            "predicted_class": service.int_to_label[pred_idx],
            "confidence": float(probs[pred_idx]),
            "base_value": base_value,
            "f_x": float(probs[pred_idx]),
            "attributions": attributions,
            "all_features": [a["feature"] for a in attributions],
        }


shap_service = ShapService()
