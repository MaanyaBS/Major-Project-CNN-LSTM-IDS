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
