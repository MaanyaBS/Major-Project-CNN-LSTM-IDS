from typing import Dict

CERT_IN_CATEGORY_MAP: Dict[str, str] = {
    "BENIGN": "Normal",
    "DDoS": "DDoS",
    "DoS GoldenEye": "DoS",
    "DoS Hulk": "DoS",
    "DoS Slowhttptest": "DoS",
    "DoS slowloris": "DoS",
    "PortScan": "Port Scan",
    "FTP-Patator": "Brute Force",
    "SSH-Patator": "Brute Force",
    "Web Attack - Brute Force": "Brute Force",
    "Web Attack - Sql Injection": "Web Attack",
    "Web Attack - XSS": "Web Attack",
    "Bot": "Botnet",
    "Heartbleed": "Exploit",
    "Infiltration": "Infiltration",
}

DASHBOARD_CATEGORIES = [
    "Normal",
    "DDoS",
    "DoS",
    "Port Scan",
    "Brute Force",
    "Web Attack",
    "Botnet",
    "Exploit",
    "Infiltration",
]

LOW_CONFIDENCE_CLASSES = {
    "Bot",
    "Web Attack - Brute Force",
    "Web Attack - XSS",
    "Web Attack - Sql Injection",
    "Infiltration",
}


def get_cert_in_category(predicted_class: str) -> str:
    return CERT_IN_CATEGORY_MAP.get(predicted_class, "Uncategorized")
