"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Class-to-Action Mapping & Prevention Policy
Author  : Person B (Model Development)
==========================================================
Maps predicted intrusion classes to automated prevention actions,
severity levels, and confidence thresholds, one policy per dataset:

    cicids2017  CNN-LSTM v2 per-class F1-scores (full 530,951-row
                chronological test set — see model/MODEL_INTERFACE.md)
    mu_iot      MU-IoT CNN-LSTM per-class F1-scores on held-out
                recordings (see model/MU_IOT_MODEL_INTERFACE.md)

get_action(predicted_class, confidence) uses the CICIDS2017 policy;
pass dataset="mu_iot" for MU-IoT predictions. The two models share the
class name "DDoS", so the dataset must be explicit, never guessed.
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


# Map of the 7 MU-IoT classes (normal + 6 attack categories)
#
# Same F1 -> threshold curve as the CICIDS2017 map above (thresholds are
# that curve interpolated at each class's F1, rounded to 2 decimals), but
# applied to the F1 on HELD-OUT recordings (test_heldout in
# model/results/mu_iot/mu_iot_metrics.json): whole recordings the model
# never saw in training. Scores on recordings seen in training overstated
# every class that could be checked (DDoS 0.980 -> 0.446, Scan 0.994 ->
# 0.420, Password_Hacking 0.990 -> 0.804, Injection 0.978 -> 0.918).
#
# A class with no held-out recording has no evidence of how it does on
# unseen traffic, so it is hard-locked to held_for_review (MiTM, Spyware).
# Actions match the nearest CICIDS2017 class (DDoS -> DDoS, Scan ->
# PortScan, Password_Hacking -> FTP/SSH-Patator).
MU_IOT_CLASS_ACTION_MAP: Dict[str, Dict[str, Any]] = {
    "normal": {
        "action": "no_action",
        "severity": "low",
        "threshold": 0.50,
        "f1_score": 0.9093,
        "f1_source": "test_within",  # no held-out normal recording
    },
    "Injection": {
        "action": "block_ip",
        "severity": "high",
        "threshold": 0.63,  # held-out F1 0.9180 (XSS recording)
        "f1_score": 0.9180,
        "f1_source": "test_heldout",
    },
    "Password_Hacking": {
        "action": "block_ip",
        "severity": "high",
        "threshold": 0.71,  # held-out F1 0.8036 (MQTT dictionary attack)
        "f1_score": 0.8036,
        "f1_source": "test_heldout",
    },
    "DDoS": {
        "action": "block_ip",
        "severity": "critical",
        "threshold": 0.84,  # held-out F1 0.4463 (hping3 flood, mostly called Scan)
        "f1_score": 0.4463,
        "f1_source": "test_heldout",
    },
    "Scan": {
        "action": "block_ip",
        "severity": "medium",
        "threshold": 0.84,  # held-out F1 0.4197 (vulnerability scan)
        "f1_score": 0.4197,
        "f1_source": "test_heldout",
    },
    "MiTM": {
        "action": "isolate_host",
        "severity": "high",
        "threshold": float("inf"),  # unreachable by design — see note
        "never_auto_fire": True,
        "f1_score": 0.9630,
        "f1_source": "test_within",
        "note": "No held-out recording, so no evidence of performance on unseen traffic; "
                "within-recording F1 overstated every class that could be checked. Only "
                "3,954 test windows from two recordings. Always held_for_review.",
    },
    "Spyware": {
        "action": "isolate_host",
        "severity": "high",
        "threshold": float("inf"),  # unreachable by design — see note
        "never_auto_fire": True,
        "f1_score": 0.7466,
        "f1_source": "test_within",
        "note": "Main false-alarm source: 6.2% of normal test windows are predicted as "
                "Spyware (quiet keylogger exfiltration resembles background traffic). "
                "One recording, no held-out evidence. Always held_for_review.",
    },
}

POLICIES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "cicids2017": CLASS_ACTION_MAP,
    "mu_iot": MU_IOT_CLASS_ACTION_MAP,
}


def get_action(predicted_class: str, confidence: float, dataset: str = "cicids2017") -> Dict[str, str]:
    """
    Looks up the predicted class in the dataset's policy map and
    determines the automated response, severity level, and execution
    status.

    Status logic:
        - 'no_action_needed' if the class's action is 'no_action' (BENIGN / normal)
        - 'auto_action' if confidence >= threshold and action != 'no_action'
        - 'held_for_review' if confidence < threshold (for attack classes)

    dataset: "cicids2017" (default) or "mu_iot". An unknown dataset
    raises ValueError rather than silently applying the wrong policy.

    Returns:
        Dict with keys: 'action', 'severity', 'status'
    """
    if dataset not in POLICIES:
        raise ValueError(f"Unknown dataset {dataset!r}; expected one of {sorted(POLICIES)}")
    policy = POLICIES[dataset].get(predicted_class)

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
