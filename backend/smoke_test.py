import json
import numpy as np

from model_service import service, FEATURE_COLS, SEQ_LEN
from shap_service import shap_service
from cert_in_mapping import DASHBOARD_CATEGORIES


def main():
    print("Loading model artifacts...")
    service.load()
    print(f"Model loaded. Classes: {len(service.int_to_label)}")

    rng = np.random.default_rng(7)
    flows = [
        {col: float(abs(rng.normal())) for col in FEATURE_COLS}
        for _ in range(SEQ_LEN)
    ]

    result = service.predict_one(flows)
    assert abs(sum(result["probabilities"].values()) - 1.0) < 1e-5
    assert result["predicted_class"] in service.int_to_label.values()
    assert result["cert_in_category"] in DASHBOARD_CATEGORIES
    print("\nPredict OK:")
    print(json.dumps({k: v for k, v in result.items() if k != "probabilities"}, indent=2))

    batch = service.predict_batch([flows, flows])
    assert len(batch) == 2
    print("Batch OK")

    print("\nInitializing SHAP...")
    shap_service.init()
    exp = shap_service.explain(flows)
    assert len(exp["attributions"]) > 0
    assert "feature" in exp["attributions"][0]
    print("Explain OK:")
    print(f"  predicted={exp['predicted_class']} base={exp['base_value']:.4f} f_x={exp['f_x']:.4f}")
    for a in exp["attributions"][:5]:
        print(f"  {a['feature']:<30} shap={a['shap_value']:+.4f}")

    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
