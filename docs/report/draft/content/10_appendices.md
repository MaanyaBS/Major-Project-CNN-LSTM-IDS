# A | Backend API Reference

The Flask backend (`backend/app.py`) exposes the endpoints in Table A.1. All requests and responses use JSON, except the file uploads, which use multipart form data. No endpoint can enable firewall execution or change the set of permitted targets; both are fixed by environment variables when the backend is started.

::table A.1 | Endpoints of the backend API
| Method | Endpoint | Purpose |
|:---|:---|:---|
| GET | /api/health | Model and SHAP status, SHAP background source, headline metrics, execution mode |
| GET | /api/meta | Feature columns in contract order, window length, dashboard categories, label mapping |
| POST | /api/predict | Prediction for one or more windows, with the prevention decision |
| POST | /api/explain | SHAP explanation of one window, with an additivity check |
| POST | /api/predict_csv | Batch analysis of an uploaded flow CSV |
| POST | /api/predict_pcap | Batch analysis of an uploaded Wireshark capture (.pcap or .pcapng, up to 200 MB) |
| POST | /api/explain_window | SHAP explanation of one window of the last upload |
| POST | /api/stream/load | Load a file for window-by-window replay |
| GET | /api/stream/next | Next window of the replay, with its prediction |
| GET | /api/live/interfaces | Network interfaces available for live capture |
| POST | /api/live/start | Start live capture on an interface |
| GET | /api/live/poll | New window results since the last poll, with counters |
| POST | /api/live/stop | Stop live capture |
| GET | /api/prevention/active | Firewall rules in force |
| POST | /api/prevention/revoke | Remove a rule created by the prevention engine |
# B | MU-IoT Features and Dashboard Categories

## B.1 MU-IoT Features

Table B.1 lists the 38 MU-IoT features used by the MU-IoT model, in the order of the feature matrix. The names are those of the published dataset [@K30]; FPT and LPT, the times of a flow's first and last packet, were deliberately excluded (Section 3.2.3).

::table B.1 | The 38 MU-IoT features
| No. | Feature | No. | Feature | No. | Feature |
|---:|:---|---:|:---|---:|:---|
| 1 | FPC | 14 | ECN_M | 27 | MGA_UL |
| 2 | RTSP_ML | 15 | MQTT_MTL | 28 | FAMax |
| 3 | RTSP_MUL | 16 | DSCP_S | 29 | FH_M |
| 4 | ECE_FC | 17 | ECN_S | 30 | DSCP_UV |
| 5 | DNS_RCUL | 18 | TPackets | 31 | SDuration |
| 6 | FD | 19 | TCPWS_Mode | 32 | FlowR |
| 7 | DNS_QTUL | 20 | PLM | 33 | MGA_L |
| 8 | RTSP_MM | 21 | DSCP_M | 34 | PacketsPS |
| 9 | DNS_RCL | 22 | TCPWS_Mean | 35 | FIMin |
| 10 | DNSQTL | 23 | BJitter | 36 | ECN_C |
| 11 | URG_FC | 24 | BThroughput | 37 | FAMean |
| 12 | MQTT_MTUL | 25 | HL_Mode | 38 | RCount |
| 13 | HTTP_SCL | 26 | TCPWS_Sum | | |

## B.2 Dashboard Categories

The dashboard groups the fifteen CICIDS2017 classes into nine operational categories that follow CERT-In's grouping of incidents (`backend/cert_in_mapping.py`), so that an analyst sees a short list of incident types instead of fifteen dataset labels (Table B.2). The categories are a display decision only; the model, the policy and all reported scores use the fifteen original classes.

::table B.2 | Mapping of CICIDS2017 classes to dashboard categories
| CICIDS2017 classes | Dashboard category |
|:---|:---|
| BENIGN | Normal |
| DDoS | DDoS |
| DoS GoldenEye, DoS Hulk, DoS Slowhttptest, DoS slowloris | DoS |
| PortScan | Port Scan |
| FTP-Patator, SSH-Patator, Web Attack - Brute Force | Brute Force |
| Web Attack - Sql Injection, Web Attack - XSS | Web Attack |
| Bot | Botnet |
| Heartbleed | Exploit |
| Infiltration | Infiltration |

# C | Flow Features Used by the Model

Table C.1 defines the 20 CICIDS2017 features used by the model, as computed by CICFlowMeter-V3 and reproduced by the project's extractor. "Payload" is the transport-layer payload in bytes, including Ethernet padding; the forward direction is the direction of the flow's first packet.

::table C.1 | Definitions of the 20 flow features
| Feature | Definition |
|:---|:---|
| Destination Port | Destination port of the flow's first packet (the service contacted) |
| Total Length of Fwd Packets | Sum of the payload lengths of the forward packets |
| Total Length of Bwd Packets | Sum of the payload lengths of the backward packets |
| Fwd Packet Length Max | Largest forward payload |
| Fwd Packet Length Mean | Mean forward payload |
| Bwd Packet Length Max | Largest backward payload |
| Bwd Packet Length Mean | Mean backward payload |
| Bwd Packet Length Std | Sample standard deviation of the backward payloads |
| Flow IAT Max | Longest time between two consecutive packets of the flow, in microseconds |
| Fwd IAT Std | Sample standard deviation of the times between consecutive forward packets |
| Max Packet Length | Largest payload in either direction |
| Packet Length Mean | Mean payload over the flow, with the first packet counted twice |
| Packet Length Std | Sample standard deviation of the payloads, first packet counted twice |
| Packet Length Variance | Square of Packet Length Std |
| Average Packet Size | Sum of the payloads plus the first payload, divided by the number of packets |
| Avg Fwd Segment Size | Mean forward payload (equal to Fwd Packet Length Mean) |
| Avg Bwd Segment Size | Mean backward payload (equal to Bwd Packet Length Mean) |
| Subflow Fwd Packets | Number of forward packets (one subflow per flow) |
| Subflow Fwd Bytes | Forward payload bytes (equal to Total Length of Fwd Packets) |
| Subflow Bwd Bytes | Backward payload bytes (equal to Total Length of Bwd Packets) |

# D | Live Demonstration Procedure

The live demonstration follows a written checklist (`docs/LIVE_DEMO_CHECKLIST.md`), summarised here so that it can be repeated. Only the protected laptop may be scanned, the network's gateway may never be a target, and the network owner's permission is required.

**Preparation.**

1. Connect the laptop and the second device (an Android tablet with Termux and nmap) to the same network, with any VPN turned off; the second device must not be the hotspot or router itself.
2. Note the laptop's IPv4 address and default gateway (`ipconfig`) and the tablet's address.
3. In an administrator PowerShell window, remove any rules left from earlier tests (`IDS_DEMO_*`), and allow the tablet to reach the laptop with a temporary inbound allow rule; a block rule created by the system overrides it.
4. Start a test web page on the laptop (port 8000) and open it from the tablet to confirm that the two devices can reach each other.
5. Confirm that Windows' stealth mode is off, so that the laptop answers the scan as the CICIDS2017 servers did.

**Running the demonstration.**

1. Start the backend as administrator with execution enabled and the tablet's address as the only permitted target (`IDS_PREVENTION_EXECUTION_ENABLED=1`, `IDS_PREVENTION_DEMO_TARGETS=<tablet address>`), and start the dashboard.
2. In the dashboard, select the Wi-Fi interface and start live capture; normal traffic appears as BENIGN windows.
3. From the tablet, run `nmap -sT <laptop address>`. Within about two seconds the dashboard shows PortScan with an executed block, and the tablet appears in the Blocked devices panel.
4. Reload the test page on the tablet: it no longer loads. Repeated scan windows are reported as already blocked.
5. Revoke the block in the dashboard; the test page loads again.

**Cleaning up.** Stop the capture and the backend, remove the temporary allow rule and any remaining `IDS_DEMO_*` rules, and, after the project, turn Windows' stealth mode back on.

# E | Selected Source Code

The listings below are taken unchanged from the project's source code, apart from comments shortened for space.

::listing E.1 | Definition of the CNN-LSTM model (model/cnn_lstm_architecture.py)
```
def build_cnn_lstm_model(input_shape, num_classes):
    model = Sequential([
        # --- CNN Feature Extraction Block 1 ---
        Conv1D(filters=64, kernel_size=3, activation='relu',
               input_shape=input_shape),
        BatchNormalization(),
        MaxPooling1D(pool_size=2),

        # --- CNN Feature Extraction Block 2 ---
        Conv1D(filters=128, kernel_size=3, activation='relu',
               padding='same'),
        BatchNormalization(),
        MaxPooling1D(pool_size=2),

        # --- LSTM Temporal Learning ---
        LSTM(64, return_sequences=False),

        # --- Fully Connected Classifier ---
        Dense(64, activation='relu'),
        Dense(num_classes, activation='softmax'),
    ])

    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy'],
    )
    return model
```

::listing E.2 | The prevention decision (model/class_action_mapping.py)
```
def get_action(predicted_class, confidence, dataset="cicids2017"):
    if dataset not in POLICIES:
        raise ValueError(f"Unknown dataset {dataset!r}; "
                         f"expected one of {sorted(POLICIES)}")
    policy = POLICIES[dataset].get(predicted_class)

    if not policy:
        # Fallback policy for unexpected/unknown class
        return {"action": "alert_only", "severity": "medium",
                "status": "held_for_review"}

    action = policy["action"]
    severity = policy["severity"]
    threshold = policy["threshold"]

    if predicted_class == "BENIGN" or action == "no_action":
        status = "no_action_needed"
    elif policy.get("never_auto_fire"):
        status = "held_for_review"
    elif confidence >= threshold:
        status = "auto_action"
    else:
        status = "held_for_review"
    return {"action": action, "severity": severity, "status": status}
```

::listing E.3 | Selection of the device to block (model/target_selection.py)
```
def is_candidate(ip, excluded=()):
    """True for a unicast RFC 1918 IPv4 address not in excluded."""
    if not isinstance(ip, str) or ip in excluded:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return (addr.version == 4 and any(addr in net for net in RFC1918)
            and not ip.endswith(".255"))


def select_target(source_ips, local_ips=(), gateway_ips=(), dest_ips=None):
    excluded = set(local_ips) | set(gateway_ips)
    if dest_ips is not None:
        local = set(local_ips)
        source_ips = [s if d in local else None
                      for s, d in zip(source_ips, dest_ips)]
    counts = Counter(ip for ip in source_ips if is_candidate(ip, excluded))
    if not counts:
        return None
    last_seen = {ip: i for i, ip in enumerate(source_ips)}
    return max(counts, key=lambda ip: (counts[ip], last_seen[ip]))
```
