import io
import sys
import time

import numpy as np
import requests

from model_service import FEATURE_COLS, SEQ_LEN

BASE = "http://127.0.0.1:5000"


def main():
    for _ in range(60):
        try:
            r = requests.get(f"{BASE}/api/health", timeout=2)
            if r.ok:
                break
        except requests.ConnectionError:
            time.sleep(1)
    else:
        sys.exit("Server did not come up")
    print("health:", r.json())

    meta = requests.get(f"{BASE}/api/meta", timeout=10).json()
    assert len(meta["feature_cols"]) == 20
    print("meta OK:", len(meta["dashboard_categories"]), "dashboard categories")

    rng = np.random.default_rng(3)
    flows = [{c: float(abs(rng.normal())) for c in FEATURE_COLS} for _ in range(SEQ_LEN)]
    pred = requests.post(f"{BASE}/api/predict", json={"flows": flows}, timeout=30).json()
    assert "result" in pred and "summary" in pred
    print("predict OK:", pred["result"]["predicted_class"], "->", pred["result"]["prevention"]["status"])

    batch = requests.post(
        f"{BASE}/api/predict", json={"sequences": [flows, flows, flows]}, timeout=30
    ).json()
    assert len(batch["results"]) == 3
    print("batch predict OK:", batch["summary"])

    exp = requests.post(f"{BASE}/api/explain", json={"flows": flows}, timeout=120).json()
    assert len(exp["attributions"]) == 20
    print("explain OK: top feature =", exp["attributions"][0]["feature"])

    rows = np.abs(rng.normal(size=(45, 20)))
    csv_data = ",".join(FEATURE_COLS) + "\n" + "\n".join(
        ",".join(f"{v:.4f}" for v in row) for row in rows
    )
    csv_resp = requests.post(
        f"{BASE}/api/predict_csv",
        files={"file": ("test.csv", csv_data.encode(), "text/csv")},
        timeout=60,
    ).json()
    assert csv_resp["summary"]["total_sequences"] == 4, csv_resp["summary"]
    assert len(csv_resp["timeline"]) > 0
    print("predict_csv OK:", csv_resp["summary"]["total_sequences"], "sequences")

    exp_w = requests.post(f"{BASE}/api/explain_window", json={"window": 2}, timeout=120).json()
    assert "attributions" in exp_w and exp_w.get("window") == 2
    print("explain_window OK: top feature =", exp_w["attributions"][0]["feature"])

    bad_w = requests.post(f"{BASE}/api/explain_window", json={"window": 99}, timeout=10)
    assert bad_w.status_code == 400
    print("explain_window bounds OK (400 on out-of-range)")

    bad = requests.post(f"{BASE}/api/predict", json={"flows": flows[:5]}, timeout=10)
    assert bad.status_code == 400
    print("error handling OK (400 on short sequence)")

    print("\nALL API TESTS PASSED")


if __name__ == "__main__":
    main()
