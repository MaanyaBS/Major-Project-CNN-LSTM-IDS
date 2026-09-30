"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Inference Speed Benchmark (CPU)
Author  : Maanya B S, Ruthwik Sai Ganesh , Varshini D N
==========================================================
Measures how fast the trained CNN-LSTM models run on a CPU:

    load time        keras.models.load_model, once per process
    latency          one window per call, the way backend/model_service.py
                     calls it (pandas -> scaler -> model.predict), plus the
                     lighter Keras call styles for comparison
    throughput       windows per second with model.predict at larger batches

and writes:

    model/results/inference_benchmark.txt    readable report
    model/results/inference_benchmark.json   the same numbers

Timing does not depend on the input values (the network has no
data-dependent branches). CICIDS2017 uses real test windows; MU-IoT uses
random windows of the right shape because its data stays on Drive.

Usage (paths default to the repo layout, so it runs from any directory):

    python model/benchmark_inference.py                  # every model whose files exist
    python model/benchmark_inference.py --models cicids
"""

import os

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")  # CPU numbers only
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import argparse
import json
import pickle
import platform
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODELS = {
    "cicids": {
        "title": "CICIDS2017 CNN-LSTM (v2)",
        "model": "model/artifacts/cnn_lstm_best_v2.keras",
        "scaler": "model/artifacts/scaler_v2.pkl",
        "windows": "datasets/verify_run_ruthwik/X_test_seq.npy",  # already scaled
    },
    "mu_iot": {
        "title": "MU-IoT CNN-LSTM",
        "model": "model/artifacts/mu_iot/best.keras",
        "scaler": "model/artifacts/mu_iot/scaler_38.pkl",
        "windows": None,
    },
}
THROUGHPUT_BATCHES = (32, 256, 2048)
THROUGHPUT_RUNS = 3
WARMUP_CALLS = 20


def repo_path(path):
    return path if os.path.isabs(path) else os.path.join(REPO, path)


def display_path(path):
    return os.path.relpath(path, REPO).replace(os.sep, "/")


def cpu_name():
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def power_source():
    """Laptops throttle on battery, so the report records which one was in use."""
    if sys.platform != "win32":
        return "unknown"
    import ctypes

    class SystemPowerStatus(ctypes.Structure):
        _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
                    ("BatteryLifePercent", ctypes.c_ubyte), ("SystemStatusFlag", ctypes.c_ubyte),
                    ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]

    status = SystemPowerStatus()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return "unknown"
    return {0: "battery", 1: "plugged in"}.get(status.ACLineStatus, "unknown")


def summarize_ms(samples_ns):
    ms = np.asarray(samples_ns, dtype=np.float64) / 1e6
    return {"median": float(np.median(ms)), "p95": float(np.percentile(ms, 95)),
            "p99": float(np.percentile(ms, 99)), "mean": float(ms.mean()), "calls": len(ms)}


def time_calls(fn, inputs, warmup=WARMUP_CALLS):
    """Time fn(x) once per input, after warm-up calls that are discarded."""
    for x in inputs[:warmup]:
        fn(x)
    samples, outputs = [], []
    for x in inputs:
        t0 = time.perf_counter_ns()
        out = fn(x)
        samples.append(time.perf_counter_ns() - t0)
        outputs.append(out)
    return summarize_ms(samples), outputs


def sample_windows(cfg, seq_len, n_features, n, rng):
    """Scaled windows of shape (n, seq_len, n_features)."""
    if cfg["windows"]:
        X = np.load(repo_path(cfg["windows"]), mmap_mode="r")
        idx = np.sort(rng.choice(len(X), size=min(n, len(X)), replace=False))
        return np.ascontiguousarray(X[idx], dtype=np.float32), f"real test windows from {cfg['windows']}"
    return rng.standard_normal((n, seq_len, n_features)).astype(np.float32), "random windows of the model's input shape"


def benchmark(name, cfg, latency_calls, throughput_windows, seed):
    from tensorflow import keras

    rng = np.random.default_rng(seed)
    model_path = repo_path(cfg["model"])

    t0 = time.perf_counter()
    model = keras.models.load_model(model_path)
    load_s = time.perf_counter() - t0

    _, seq_len, n_features = model.input_shape
    with open(repo_path(cfg["scaler"]), "rb") as f:
        scaler = pickle.load(f)
    feature_cols = list(getattr(scaler, "feature_names_in_", [])) or None

    X, source = sample_windows(cfg, seq_len, n_features, max(latency_calls, throughput_windows), rng)
    X_lat = X[:latency_calls]
    raw_rows = [scaler.inverse_transform(w) for w in X_lat]  # what a CSV upload would contain

    # Mirrors backend/model_service.py predict_matrix() for a single window.
    def backend_path(rows):
        X_df = pd.DataFrame(rows, columns=feature_cols)
        X_scaled = scaler.transform(X_df).astype("float32")
        return model.predict(X_scaled.reshape(1, seq_len, n_features), verbose=0)[0]

    def scaling_only(rows):
        return scaler.transform(pd.DataFrame(rows, columns=feature_cols)).astype("float32")

    one = [w[None] for w in X_lat]
    latency = {}
    latency["backend path (scale + model.predict)"], backend_probs = time_calls(backend_path, raw_rows)
    latency["  of which scaling (pandas + scaler)"], _ = time_calls(scaling_only, raw_rows)
    latency["model.predict"], _ = time_calls(lambda x: model.predict(x, verbose=0), one)
    latency["model.predict_on_batch"], direct_probs = time_calls(model.predict_on_batch, one)
    latency["model(x) direct call"], _ = time_calls(lambda x: np.asarray(model(x, training=False)), one)

    agree = int(np.sum(np.argmax(backend_probs, axis=1) == np.argmax(np.concatenate(direct_probs), axis=1)))

    X_tp = X[:throughput_windows]
    throughput = {"1 (backend path, one call per window)":
                  1000.0 / latency["backend path (scale + model.predict)"]["median"]}
    for batch in THROUGHPUT_BATCHES:
        model.predict(X_tp[:batch * 2], batch_size=batch, verbose=0)  # warm-up
        runs = []
        for _ in range(THROUGHPUT_RUNS):
            t0 = time.perf_counter()
            model.predict(X_tp, batch_size=batch, verbose=0)
            runs.append(len(X_tp) / (time.perf_counter() - t0))
        throughput[str(batch)] = float(np.median(runs))

    return {
        "name": name, "title": cfg["title"], "model": cfg["model"],
        "seq_len": int(seq_len), "n_features": int(n_features),
        "n_classes": int(model.output_shape[-1]),
        "parameters": int(model.count_params()),
        "file_size_mb": os.path.getsize(model_path) / 2**20,
        "dtype_policies": sorted({layer.dtype_policy.name for layer in model.layers}),
        "load_seconds": load_s,
        "input_source": source, "throughput_windows": len(X_tp),
        "latency_ms": latency, "throughput_windows_per_s": throughput,
        "backend_agreement": [agree, len(X_lat)],
    }


def format_report(env, results, skipped):
    lines = [
        "=" * 70,
        "CNN-LSTM INFERENCE SPEED ON CPU",
        "=" * 70,
        f"Generated : {env['generated']}",
        f"CPU       : {env['cpu']} ({env['logical_cores']} logical cores)",
        f"Power     : {env['power']}",
        f"Software  : Python {env['python']}, TensorFlow {env['tensorflow']}, "
        f"Keras {env['keras']}, GPU disabled",
        f"Method    : {WARMUP_CALLS} warm-up calls discarded before every latency series;",
        f"            throughput is the median of {THROUGHPUT_RUNS} runs with model.predict.",
        "",
    ]
    for r in results:
        lines += [
            "-" * 70,
            f"{r['title']}   {r['model']}",
            "-" * 70,
            f"Input window   : {r['seq_len']} flows x {r['n_features']} features -> {r['n_classes']} classes",
            f"Parameters     : {r['parameters']:,}",
            f"File size      : {r['file_size_mb']:.2f} MB",
            f"Compute dtype  : {', '.join(r['dtype_policies'])}",
            f"Load time      : {r['load_seconds']:.2f} s (first load in a fresh process)",
            f"Inputs         : {r['input_source']}",
            "",
            f"Latency, one window per call (ms)       median      p95      p99   calls",
        ]
        for label, s in r["latency_ms"].items():
            lines.append(f"  {label:<38}{s['median']:>8.2f} {s['p95']:>8.2f} {s['p99']:>8.2f} {s['calls']:>7}")
        lines += ["", f"Throughput (windows/s, {r['throughput_windows']:,} windows per run)"]
        for batch, wps in r["throughput_windows_per_s"].items():
            lines.append(f"  batch {batch:<40}{wps:>10,.0f}")
        agree, total = r["backend_agreement"]
        lines += ["", f"Check: the backend path gave the same class as the direct model call on "
                      f"{agree}/{total} windows.", ""]
    for name, reason in skipped:
        lines += [f"{MODELS[name]['title']}: not measured ({reason})", ""]
    lines += [
        "How to read windows/s as flows/s",
        "  Non-overlapping windows (backend predict_matrix() cuts rows into blocks):",
        "      flows/s = windows/s x window length",
        "  Sliding windows, one new window per arriving flow (how training and",
        "  evaluation windows were built):",
        "      flows/s = windows/s",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Measure CNN-LSTM inference speed on CPU")
    parser.add_argument("--models", nargs="+", choices=sorted(MODELS), default=sorted(MODELS))
    parser.add_argument("--output-dir", default="model/results")
    parser.add_argument("--latency-calls", type=int, default=300)
    parser.add_argument("--throughput-windows", type=int, default=16384)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    import keras
    import tensorflow as tf

    env = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cpu": cpu_name(), "logical_cores": os.cpu_count(), "power": power_source(),
        "python": platform.python_version(), "tensorflow": tf.__version__, "keras": keras.__version__,
    }
    print(f"CPU: {env['cpu']} | power: {env['power']}")

    results, skipped = [], []
    for name in args.models:
        cfg = MODELS[name]
        missing = [cfg[k] for k in ("model", "scaler", "windows") if cfg[k] and not os.path.exists(repo_path(cfg[k]))]
        if missing:
            skipped.append((name, "file not found: " + ", ".join(missing)))
            print(f"Skipping {name}: file not found: {', '.join(missing)}")
            continue
        print(f"Benchmarking {name} ...")
        results.append(benchmark(name, cfg, args.latency_calls, args.throughput_windows, args.seed))
    if not results:
        sys.exit("No model could be measured.")

    report = format_report(env, results, skipped)
    out_dir = repo_path(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    txt_path = os.path.join(out_dir, "inference_benchmark.txt")
    json_path = os.path.join(out_dir, "inference_benchmark.json")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"environment": env, "results": results,
                   "skipped": [{"model": n, "reason": r} for n, r in skipped]}, f, indent=2)
    print("\n" + report)
    print(f"Wrote {display_path(txt_path)} and {display_path(json_path)}")


if __name__ == "__main__":
    main()
