"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Class-to-Action Mapping & Prevention Policy
Author  : Person B (Model Development)
==========================================================
Maps predicted intrusion classes to automated prevention actions,
severity levels, and confidence thresholds calibrated against
CNN-LSTM v2 per-class F1-scores (full 530,951-row chronological
test set — see model/MODEL_INTERFACE.md).
"""

from typing import Dict, Any

# Map of 15 CICIDS2017 classes (1 BENIGN + 14 Attack Classes)
#
# Confidence thresholds are calibrated inversely to CNN-LSTM v2's own
# per-class F1-scores (previously RF-calibrated — recalibrated once the
# real CNN-LSTM per-class breakdown existed):
#   Higher F1 (high reliability) -> Lower threshold (less conservative)
#   Lower F1 (low reliability)   -> Higher threshold (more conservative)
#
# Two distinct reasons a class can be hard-locked to held_for_review
# (threshold=inf) regardless of confidence — kept separate deliberately:
#   1. Insufficient test data to trust ANY F1 estimate either way
#      (Heartbleed: 3 test rows, Web Attack - Sql Injection: 5 test rows,
#      Infiltration: 0 test rows — a known window-boundary artifact, not
#      a real absence of the attack).
#   2. Real, well-supported, measured poor reliability (Bot, Web Attack -
#      Brute Force, Web Attack - XSS all have 131-381 test rows and still
#      score near-zero F1) — these get very high (not infinite) thresholds,
#      since the model DOES sometimes get them right, just rarely.
CLASS_ACTION_MAP: Dict[str, Dict[str, Any]] = {
    "BENIGN": {
        "action": "no_action",
        "severity": "low",
        "threshold": 0.50,
        "f1_score": 0.9912,
    },
    "DDoS": {
        "action": "block_ip",
        "severity": "critical",
        "threshold": 0.55,  # CNN-LSTM F1 0.9897 -> lower threshold
        "f1_score": 0.9897,
    },
    "DoS Hulk": {
        "action": "rate_limit",
        "severity": "high",
        "threshold": 0.55,  # CNN-LSTM F1 0.9898
        "f1_score": 0.9898,
    },
    "PortScan": {
        "action": "block_ip",
        "severity": "medium",
        "threshold": 0.60,  # CNN-LSTM F1 0.9711
        "f1_score": 0.9711,
    },
    "DoS Slowhttptest": {
        "action": "drop_connection",
        "severity": "medium",
        "threshold": 0.65,  # CNN-LSTM F1 0.8857
        "f1_score": 0.8857,
    },
    "DoS GoldenEye": {
        "action": "rate_limit",
        "severity": "high",
        "threshold": 0.70,  # CNN-LSTM F1 0.8159
        "f1_score": 0.8159,
    },
    "FTP-Patator": {
        "action": "block_ip",
        "severity": "high",
        "threshold": 0.72,  # CNN-LSTM F1 0.7732
        "f1_score": 0.7732,
    },
    "DoS slowloris": {
        "action": "drop_connection",
        "severity": "medium",
        "threshold": 0.75,  # CNN-LSTM F1 0.7249
        "f1_score": 0.7249,
    },
    "SSH-Patator": {
        "action": "block_ip",
        "severity": "high",
        "threshold": 0.78,  # CNN-LSTM F1 0.6562
        "f1_score": 0.6562,
    },
    "Web Attack - Brute Force": {
        "action": "block_ip",
        "severity": "high",
        "threshold": 0.92,  # CNN-LSTM F1 0.1249 -> real, measured weakness
        "f1_score": 0.1249,
    },
    "Bot": {
        "action": "isolate_host",
        "severity": "high",
        "threshold": 0.94,  # CNN-LSTM F1 0.0564 -> real, measured weakness
        "f1_score": 0.0564,
    },
    "Web Attack - XSS": {
        "action": "sanitize_input",
        "severity": "high",
        "threshold": 0.97,  # CNN-LSTM F1 0.0064 -> real, measured weakness
        "f1_score": 0.0064,
    },
    "Heartbleed": {
        "action": "terminate_session",
        "severity": "critical",
        "threshold": float("inf"),  # unreachable by design — see note
        "never_auto_fire": True,
        "note": "Only 3 test rows in the full chronological test set. A high raw F1 on "
                "3 samples isn't a real signal — insufficient data to trust in either "
                "direction, always held_for_review regardless of confidence.",
    },
    "Infiltration": {
        "action": "isolate_host",
        "severity": "critical",
        "threshold": float("inf"),  # unreachable by design — see note
        "never_auto_fire": True,
        "note": "Zero test rows in the sequence-windowed test set — a known dataset-size "
                "artifact (all raw test rows fell within the first 9 rows of a day's "
                "sequence-window boundary and were excluded during windowing), not evidence "
                "the attack is absent. No F1 can be computed at all, always held_for_review "
                "regardless of confidence.",
    },
    "Web Attack - Sql Injection": {
        "action": "block_ip",       # what to do IF confirmed — same as other injection-class attacks
        "severity": "critical",     # reflects real-world danger, unchanged by detection uncertainty
        "threshold": float("inf"),  # unreachable by design — see note
        "never_auto_fire": True,    # explicit flag in case get_action() checks this directly
        "note": "Only 5 test rows (full chronological test set). Insufficient data to "
                "trust the F1 estimate in either direction — always held_for_review, "
                "regardless of confidence.",
    },
}


def get_action(predicted_class: str, confidence: float) -> Dict[str, str]:
    """
    Looks up the predicted class in CLASS_ACTION_MAP and determines
    the automated response, severity level, and execution status.

    Status logic:
        - 'no_action_needed' if predicted_class is BENIGN or action is 'no_action'
        - 'auto_action' if confidence >= threshold and action != 'no_action'
        - 'held_for_review' if confidence < threshold (for non-BENIGN attacks)

    Returns:
        Dict with keys: 'action', 'severity', 'status'
    """
    policy = CLASS_ACTION_MAP.get(predicted_class)

    if not policy:
        # Fallback policy for unexpected/unknown class
        return {
            "action": "alert_only",
            "severity": "medium",
            "status": "held_for_review",
        }

    action = policy["action"]
    severity = policy["severity"]
    threshold = policy["threshold"]

    if predicted_class == "BENIGN" or action == "no_action":
        status = "no_action_needed"
    elif confidence >= threshold:
        status = "auto_action"
    else:
        status = "held_for_review"

    return {
        "action": action,
        "severity": severity,
        "status": status,
    }
