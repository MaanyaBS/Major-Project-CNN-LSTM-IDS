"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Class-to-Action Mapping & Prevention Policy
Author  : Person B (Model Development)
==========================================================
Maps predicted intrusion classes to automated prevention actions,
severity levels, and confidence thresholds calibrated against
Random Forest baseline per-class F1-scores.
"""

from typing import Dict, Any

# Map of 15 CICIDS2017 classes (1 BENIGN + 14 Attack Classes)
# Confidence thresholds are calibrated inversely to RF baseline F1-scores:
# Higher F1 (high reliability) -> Lower threshold (less conservative)
# Lower F1 (low reliability)   -> Higher threshold (more conservative)
CLASS_ACTION_MAP: Dict[str, Dict[str, Any]] = {
    "BENIGN": {
        "action": "no_action",
        "severity": "low",
        "threshold": 0.50,
        "f1_score": 1.00,
    },
    "Bot": {
        "action": "isolate_host",
        "severity": "high",
        "threshold": 0.85,  # RF F1 ~0.63 -> higher threshold
        "f1_score": 0.63,
    },
    "DDoS": {
        "action": "block_ip",
        "severity": "critical",
        "threshold": 0.55,  # RF F1 1.00 -> lower threshold
        "f1_score": 1.00,
    },
    "DoS GoldenEye": {
        "action": "rate_limit",
        "severity": "high",
        "threshold": 0.65,  # RF F1 0.97
        "f1_score": 0.97,
    },
    "DoS Hulk": {
        "action": "rate_limit",
        "severity": "high",
        "threshold": 0.60,  # RF F1 0.99
        "f1_score": 0.99,
    },
    "DoS Slowhttptest": {
        "action": "drop_connection",
        "severity": "medium",
        "threshold": 0.60,  # RF F1 0.99
        "f1_score": 0.99,
    },
    "DoS slowloris": {
        "action": "drop_connection",
        "severity": "medium",
        "threshold": 0.60,  # RF F1 0.99
        "f1_score": 0.99,
    },
    "FTP-Patator": {
        "action": "block_ip",
        "severity": "high",
        "threshold": 0.55,  # RF F1 1.00
        "f1_score": 1.00,
    },
    "Heartbleed": {
        "action": "terminate_session",
        "severity": "critical",
        "threshold": 0.55,  # RF F1 1.00
        "f1_score": 1.00,
    },
    "Infiltration": {
        "action": "isolate_host",
        "severity": "critical",
        "threshold": 0.70,  # RF F1 0.92
        "f1_score": 0.92,
    },
    "PortScan": {
        "action": "block_ip",
        "severity": "medium",
        "threshold": 0.60,  # RF F1 0.99
        "f1_score": 0.99,
    },
    "SSH-Patator": {
        "action": "block_ip",
        "severity": "high",
        "threshold": 0.65,  # RF F1 0.97
        "f1_score": 0.97,
    },
    "Web Attack - Brute Force": {
        "action": "block_ip",
        "severity": "high",
        "threshold": 0.80,  # RF F1 0.69
        "f1_score": 0.69,
    },
    "Web Attack - Sql Injection": {
        "action": "block_ip",
        "severity": "critical",
        "threshold": 0.95,  # RF F1 0.00 -> conservative threshold
        "f1_score": 0.00,
    },
    "Web Attack - XSS": {
        "action": "sanitize_input",
        "severity": "high",
        "threshold": 0.90,  # RF F1 0.35 -> conservative threshold
        "f1_score": 0.35,
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
