"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Prevention Simulation Script (PoC)
Author  : Person B (Model Development)
==========================================================
Simulates the intrusion prevention policy engine by reading model
predictions and confidence scores, evaluating class-action thresholds,
and generating a CSV prevention log (auto_action / held_for_review / no_action_needed).
"""

import os
import sys
import argparse
import random
import pandas as pd

# Add project root to sys.path so imports work when run from any directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from model.class_action_mapping import get_action, CLASS_ACTION_MAP


def generate_demo_data() -> pd.DataFrame:
    """
    Generates ~20 synthetic prediction rows covering a realistic mix of
    intrusion classes and confidence levels to demonstrate all three
    prevention status outcomes (auto_action, held_for_review, no_action_needed).
    """
    demo_samples = [
        # (predicted_class, confidence)
        ("BENIGN", 0.99),
        ("BENIGN", 0.85),
        ("BENIGN", 0.45),
        ("DDoS", 0.98),                   # threshold 0.55 -> auto_action
        ("DDoS", 0.40),                   # threshold 0.55 -> held_for_review
        ("PortScan", 0.95),               # threshold 0.60 -> auto_action
        ("PortScan", 0.50),               # threshold 0.60 -> held_for_review
        ("Bot", 0.92),                    # threshold 0.85 -> auto_action
        ("Bot", 0.70),                    # threshold 0.85 -> held_for_review
        ("DoS GoldenEye", 0.90),          # threshold 0.65 -> auto_action
        ("DoS GoldenEye", 0.55),          # threshold 0.65 -> held_for_review
        ("FTP-Patator", 0.88),            # threshold 0.55 -> auto_action
        ("SSH-Patator", 0.40),            # threshold 0.65 -> held_for_review
        ("Web Attack - Brute Force", 0.85),# threshold 0.80 -> auto_action
        ("Web Attack - Brute Force", 0.72),# threshold 0.80 -> held_for_review
        ("Web Attack - Sql Injection", 0.98),# threshold 0.95 -> auto_action
        ("Web Attack - Sql Injection", 0.80),# threshold 0.95 -> held_for_review
        ("Web Attack - XSS", 0.95),       # threshold 0.90 -> auto_action
        ("Web Attack - XSS", 0.60),       # threshold 0.90 -> held_for_review
        ("Infiltration", 0.91),           # threshold 0.70 -> auto_action
    ]

    df = pd.DataFrame(demo_samples, columns=["predicted_class", "confidence"])
    return df


def run_simulation(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Applies class-action policy lookup to each prediction row.
    Appends 'action', 'severity', and 'status' columns.
    """
    actions = []
    severities = []
    statuses = []

    for _, row in df_input.iterrows():
        pred_class = str(row["predicted_class"])
        conf = float(row["confidence"])

        result = get_action(pred_class, conf)
        actions.append(result["action"])
        severities.append(result["severity"])
        statuses.append(result["status"])

    df_out = df_input.copy()
    df_out["action"] = actions
    df_out["severity"] = severities
    df_out["status"] = statuses

    return df_out[["predicted_class", "confidence", "action", "severity", "status"]]


def main():
    parser = argparse.ArgumentParser(
        description="Intrusion Prevention Policy Simulation Script"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run simulation on synthetic demo data demonstrating all policy outcomes.",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=os.path.join("model", "results", "rf_predictions.csv"),
        help="Path to input CSV containing predicted_class and confidence columns (for non-demo mode).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="prevention_simulation_output.csv",
        help="Path where the output prevention log CSV will be written.",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("INTRUSION PREVENTION POLICY SIMULATION")
    print("=" * 70)

    if args.demo:
        print("[+] Running in DEMO mode with synthetic predictions...")
        df_input = generate_demo_data()
    else:
        print(f"[+] Running in REAL mode using input file: {args.input}")
        if not os.path.exists(args.input):
            print(f"[-] ERROR: Input prediction file not found at: {args.input}")
            print("    Note: model/baseline_random_forest.py does not currently save predict_proba() / prediction CSVs.")
            print("    Run with --demo flag to evaluate policy logic, or save real predictions with probabilities first.")
            sys.exit(1)
        df_input = pd.read_csv(args.input)

    print(f"[+] Loaded {len(df_input)} prediction records for processing.")
    print("[+] Evaluating class-action policy and confidence thresholds...")

    df_result = run_simulation(df_input)

    # Write output CSV
    output_dir = os.path.dirname(os.path.abspath(args.output))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    df_result.to_csv(args.output, index=False)

    print(f"[+] Simulation complete. Results written to: {args.output}")
    print("\nSummary of Prevention Status Distribution:")
    print(df_result["status"].value_counts().to_string())
    print("=" * 70)


if __name__ == "__main__":
    main()
