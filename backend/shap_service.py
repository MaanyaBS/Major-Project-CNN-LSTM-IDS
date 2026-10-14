"""
SHAP explainability service.

Background
----------
SHAP compares each explained window against a *background* distribution, and
what that background contains decides what the attributions mean.

The background used to be 32 sequences of N(0,1) noise. That is not a traffic
distribution - it is a plausible-looking stand-in for the post-scaler feature
space. Explanations read as "how does this window differ from random noise"
rather than "how does this window differ from the traffic the model sees".

The background is now real training windows sampled from X_train_seq.npy and
committed as backend/shap_background.npy (~80 KB), a few per class so no single
class dominates the reference set. Regenerate with
`python model/build_shap_background.py`. If the file is missing the service
falls back to synthetic noise so the API still works, and reports
background_source so the fallback can never be mistaken for real traffic.

Explainer choice: KernelExplainer, not GradientExplainer
---------------------------------------------------------
GradientExplainer was the previous choice. Measured on this model
(TensorFlow 2.21 / Keras 3.15 / shap 0.52), it could not satisfy the one
property an explanation has to have - that the attributions reconstruct the
prediction:

  - Additivity error was ~1.3e-01 on a single window: the attributions summed
    to 0.903 against a required 0.988, a 9% shortfall. This is inherent to
    GradientExplainer's path-dependent gradient integration on a recurrent
    model with softmax output, not a tuning problem.
  - The error was also unstable, varying 0.69 / 0.90 / 1.04 for the same input
    across runs, because it samples from the background.
  - It was also 5-50x slower (1-16 s per window vs ~200 ms).
  - It exposed no expected_value in this shap version, so the base value had to
    be recomputed by predicting on the background.

KernelExplainer is model-agnostic and, for a model this small, fast enough to be
interactive.

Explained features: 20 groups, not 200 scalars
----------------------------------------------
The window is flattened to 200 columns (10 timesteps x 20 features) before
being handed to shap - a (n, 10, 20) array is ambiguous to shap, which tries
to interpret it as an image stack. But shap does NOT explain those 200
scalars independently: DenseData is given one group per feature (that feature
at all 10 timesteps), so KernelExplainer estimates 20 grouped values - exactly
the 20 features the dashboard shows.

Measured against a converged reference (KernelExplainer at 5,000 samples,
whose results are stable from seed to seed), the 200-scalar setup does not
hold up even though its additivity error is ~1e-9:

  setup                          agreement r   same top-5   same window, new seed
  200 scalars, nsamples=100         0.34         2.2 / 5          0.08
  20 groups,   nsamples=1000        0.98         4.6 / 5          0.96

The 200-scalar setup failed for two reasons: shap 0.52's default
l1_reg="num_features(10)" silently keeps only 10 of the 200 inputs and zeroes
the rest, and 100 reference samples are far too few to estimate 200 values.
Exact additivity (1e-9) held by construction in BOTH setups - it is a property
of the constrained regression, not evidence that the values are right. The
fixed seed made the bad values repeatable, not correct: a different seed gave
an almost unrelated answer (r = 0.08). Grouping is also honest about what the
model consumes: it never looks at one timestep of one feature in isolation,
so claiming a per-timestep attribution would overstate the resolution we have.

The remaining implementation details:
  - nsamples=1000 costs ~1.5 s per window (about half that on a fast machine).
    nsamples=300 gives r = 0.92 in ~0.5 s if that is ever too slow.
  - np.random.seed() is set before each call. KernelExplainer draws its
    reference samples from the global numpy RNG, so without this the same
    window returns different attributions on every click (measured r = 0.96
    between seeds with the grouped setup - close, but not identical).
  - shap.utils._legacy.DenseData is an internal class, which is why
    requirements.txt pins shap==0.52.0 exactly.

Local accuracy still holds in the form the API returns:
    base_value + sum(attributions) == model output for the predicted class
There is no aggregation step at all now - the 20 grouped values ARE the
per-feature attributions, so nothing is summed or averaged over timesteps.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from model_service import service, SEQ_LEN, NUM_FEATURES, FEATURE_COLS

# Committed sample of real training windows. Regenerate with
# `python model/build_shap_background.py` where X_train_seq.npy is available.
BACKGROUND_PATH = Path(__file__).resolve().parent / "shap_background.npy"

# Used only if the committed real-traffic background is missing, so the API
# still works rather than failing closed.
FALLBACK_BACKGROUND_SEQUENCES = 32

# KernelExplainer reference samples per explanation. 1000 is the measured
# convergence point against a 5,000-sample reference (r = 0.98); 100 was far
# too few to estimate anything reliably. nsamples=300 gives r = 0.92 at about
# a third of the cost if this is ever too slow.
KERNEL_NSAMPLES = 1000

# Fixed so repeated clicks on the same window return the same explanation.
EXPLAIN_SEED = 0

MAX_EXPLAIN_FEATURES = 20


class ShapService:
    def __init__(self):
        self.explainer = None
        self.background = None
        self.ready = False
        self.background_source = "uninitialised"
        self.background_flat = None
        # Background predictions are fixed at init, so the base value is a
        # constant rather than something recomputed per request.
        self._bg_preds = None

    def init(self):
        import shap
        from shap.utils._legacy import DenseData  # internal API - hence the shap pin

        self.background, self.background_source = self._load_background()

        # Flatten (n, SEQ_LEN, NUM_FEATURES) -> (n, SEQ_LEN * NUM_FEATURES) so
        # shap treats the window as tabular rather than guessing it is an
        # image stack.
        self.background_flat = self.background.reshape(len(self.background), -1)

        # One group per feature = that feature at all 10 timesteps, so shap
        # explains 20 grouped features - exactly what the dashboard shows -
        # instead of 200 scalars it cannot estimate from 1000 samples.
        groups = [[t * NUM_FEATURES + f for t in range(SEQ_LEN)] for f in range(NUM_FEATURES)]
        self.explainer = shap.KernelExplainer(
            self._predict_flat, DenseData(self.background_flat, FEATURE_COLS, groups)
        )
        self.ready = True

    def _predict_flat(self, flat):
        """shap's entry point: flat (n, SEQ_LEN*NUM_FEATURES) -> (n, n_classes)."""
        X = np.asarray(flat, dtype="float32").reshape(-1, SEQ_LEN, NUM_FEATURES)
        return np.asarray(service.model.predict_on_batch(X))

    def _load_background(self):
        if BACKGROUND_PATH.exists():
            arr = np.load(BACKGROUND_PATH)
            if arr.ndim == 3 and arr.shape[1:] == (SEQ_LEN, NUM_FEATURES):
                return arr.astype("float32"), "real_training_windows"
            raise ValueError(
                f"{BACKGROUND_PATH.name} has shape {arr.shape}, expected "
                f"(n, {SEQ_LEN}, {NUM_FEATURES}). Regenerate it with "
                "model/build_shap_background.py."
            )

        rng = np.random.default_rng(42)
        fallback = rng.standard_normal(
            (FALLBACK_BACKGROUND_SEQUENCES, SEQ_LEN, NUM_FEATURES)
        ).astype("float32")
        return fallback, "synthetic_fallback"

    def background_info(self):
        return {
            "source": self.background_source,
            "explainer": "KernelExplainer",
            "sequences": int(self.background.shape[0]) if self.background is not None else 0,
            "real_traffic": self.background_source == "real_training_windows",
            "path": str(BACKGROUND_PATH) if BACKGROUND_PATH.exists() else None,
        }

    def explain(self, flow_rows, max_display=MAX_EXPLAIN_FEATURES):
        X_raw = service._rows_to_raw(flow_rows)
        return self.explain_matrix(X_raw, max_display=max_display)

    def explain_matrix(self, X_raw, max_display=MAX_EXPLAIN_FEATURES):
        if not self.ready:
            raise RuntimeError("SHAP explainer not initialized")

        X_scaled = service.scaler.transform(
            pd.DataFrame(X_raw, columns=FEATURE_COLS)
        ).astype("float32")
        X_flat = X_scaled.reshape(1, SEQ_LEN * NUM_FEATURES)

        probs = service.model.predict_on_batch(X_scaled[np.newaxis, :, :])[0]
        pred_idx = int(np.argmax(probs))
        f_x = float(probs[pred_idx])

        # KernelExplainer samples from the global numpy RNG, so seed it to keep
        # repeated explanations of the same window identical. l1_reg=False
        # matters: shap 0.52's default "num_features(10)" silently zeroes all
        # but 10 features, which is what made the old 200-scalar setup so
        # unreliable. With 20 groups there is nothing to prune and nothing
        # to gain from pruning.
        np.random.seed(EXPLAIN_SEED)
        shap_values = self.explainer.shap_values(
            X_flat, nsamples=KERNEL_NSAMPLES, l1_reg=False, silent=True
        )
        sv = np.asarray(shap_values)

        if sv.ndim == 3 and sv.shape[-1] == len(probs):
            # (1, 20 groups, n_classes): one value per feature group.
            feature_attr = sv[0, :, pred_idx]
        elif sv.ndim == 2 and sv.shape[0] == 1 and sv.shape[1] == NUM_FEATURES:
            feature_attr = sv[0]
        else:
            raise RuntimeError(f"Unexpected SHAP output shape: {sv.shape}")

        # No aggregation step: the explainer was given one group per feature
        # (that feature at all 10 timesteps), so feature_attr already holds
        # exactly NUM_FEATURES values. Summing or averaging here would either
        # break additivity or divide every contribution by SEQ_LEN.
        raw_means = X_raw.mean(axis=0)

        base_value = self._base_value(pred_idx)

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

        # SHAP's local accuracy, reported so the claim is checkable rather than
        # assumed. `attributions` is the top-N display subset, so this uses the
        # full 20-feature vector.
        full_sum = float(feature_attr.sum())

        return {
            "predicted_class": service.int_to_label[pred_idx],
            "confidence": f_x,
            "base_value": base_value,
            "f_x": f_x,
            "attributions": attributions,
            "all_features": [a["feature"] for a in attributions],
            "aggregation": "grouped_by_feature_over_timesteps",
            "explainer": "KernelExplainer",
            "timesteps": int(SEQ_LEN),
            "background_source": self.background_source,
            "local_accuracy": {
                "base_value": base_value,
                "sum_all_attributions": full_sum,
                "model_output": f_x,
                "reconstructed": base_value + full_sum,
                "abs_error": abs(base_value + full_sum - f_x),
            },
        }

    def _base_value(self, pred_idx):
        """
        The model's average output for this class over the background - the
        E[f(x)] term that SHAP's attributions are measured against.
        """
        if self._bg_preds is None:
            self._bg_preds = np.asarray(self._predict_flat(self.background_flat))
        return float(self._bg_preds[:, pred_idx].mean())


shap_service = ShapService()