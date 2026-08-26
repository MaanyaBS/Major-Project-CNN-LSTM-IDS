import json
import sys
import time
import io
import csv

import requests

BASE = "http://127.0.0.1:5000"

def main():
    for _ in range(120):
        try:
            r = requests.get(f"{BASE}/api/health", timeout=2)
            if r.ok and r.json().get("status") == "ok":
                break
        except requests.ConnectionError:
            pass
        time.sleep(2)
    else:
        sys.exit("Server did not come up or model not loaded")

    print("health OK:", r.json()["status"])

    # build test CSV
    cols = [
        "Destination Port", "Total Length of Fwd Packets", "Total Length of Bwd Packets",
        "Fwd Packet Length Max", "Fwd Packet Length Mean", "Bwd Packet Length Max",
        "Bwd Packet Length Mean", "Bwd Packet Length Std", "Flow IAT Max", "Fwd IAT Std",
        "Max Packet Length", "Packet Length Mean", "Packet Length Std",
        "Packet Length Variance", "Average Packet Size", "Avg Fwd Segment Size",
        "Avg Bwd Segment Size", "Subflow Fwd Packets", "Subflow Fwd Bytes",
        "Subflow Bwd Bytes",
    ]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for i in range(120):
        w.writerow([str(i % 100)] + [str((i * j + 1) % 200) for j in range(1, 20)])
    csv_bytes = buf.getvalue().encode()

    # stream/load
    resp = requests.post(f"{BASE}/api/stream/load", files={"file": ("test.csv", csv_bytes, "text/csv")})
    assert resp.ok, resp.json()
    tw = resp.json()
    assert tw["total_windows"] == 12
    print(f"stream/load OK: {tw['total_windows']} windows")

    # stream/next x12
    results = []
    for i in range(12):
        r = requests.get(f"{BASE}/api/stream/next")
        d = r.json()
        print(f"  window {i}: status={r.status_code} done={d.get('done')} err={d.get('error','')}")
        if d.get("error"):
            sys.exit(f"stream/next failed at window {i}: {d['error']}")
        assert not d["done"]
        results.append(d)
    print(f"stream/next: got {len(results)} results")

    # stream/next should now return done
    r = requests.get(f"{BASE}/api/stream/next")
    d = r.json()
    assert d["done"], f"Expected done=True, got: {d}"
    assert d["total"] == 12
    print(f"stream/next done OK")

    # verify results have correct fields
    for d in results:
        res = d["result"]
        assert "predicted_class" in res, f"Missing predicted_class in {res.keys()}"
        assert "probabilities" in res
        assert "prevention" in res
        assert "window" in res
    print("field validation OK")

    # reload and stream all
    requests.post(f"{BASE}/api/stream/load", files={"file": ("test.csv", csv_bytes, "text/csv")})
    for i in range(12):
        r = requests.get(f"{BASE}/api/stream/next")
        assert not r.json()["done"]
    r = requests.get(f"{BASE}/api/stream/next")
    assert r.json()["done"]
    print("reload + full drain OK")

    # reload with 2 rows (below SEQ_LEN) - should error
    small = b"f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f19,f20\n1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20\n"
    r = requests.post(f"{BASE}/api/stream/load", files={"file": ("small.csv", small, "text/csv")})
    assert r.status_code == 400
    print("small file rejected:", r.status_code)

    print("\nALL STREAM TESTS PASSED")

    print("\nALL STREAM TESTS PASSED")


if __name__ == "__main__":
    main()
