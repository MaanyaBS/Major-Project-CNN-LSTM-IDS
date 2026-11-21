# 4 | Hardware and Software Requirement

This chapter lists the hardware and software that were used to develop, train and run the system and the minimum requirements for running it, states the functional and non-functional requirements the system meets, and describes the development environment. The project was developed on ordinary student equipment: one laptop serves as both development machine and protected host, and model training was done on free cloud GPUs.

## 4.1 Hardware Requirement

Table 4.1 lists the hardware actually used. All speed measurements in this report were taken on the laptop listed, without a GPU.

::table 4.1 | Hardware used in the project
| Item | Specification | Use |
|:---|:---|:---|
| Laptop (protected host) | AMD Ryzen 3 5300U, 4 cores / 8 threads, 7.3 GB RAM, Windows 11 Home, Wi-Fi | Development, backend, dashboard, live capture, firewall |
| Cloud GPU | Google Colab GPU runtime (NVIDIA T4 for the MU-IoT model) | Training, large evaluations, extractor validation |
| Second device (attacker) | Android tablet with Termux and nmap | Port scans and page requests in the live tests |
| Network | Phone hotspot (captures) and a home Wi-Fi router (live run) | Shared network for the protected host and the second device |

Training was done in the cloud because the full datasets do not fit comfortably in the laptop's memory: the MU-IoT feature matrix alone has almost four million rows, and training draws up to 300,000 windows per class per epoch. Inference, by contrast, is light: one window takes 1.48 ms on the laptop's CPU, so a GPU is not needed to run the system.

Table 4.2 gives the minimum requirements for running the trained system on one protected host.

::table 4.2 | Minimum hardware requirements for running the system
| Component | Minimum | Reason |
|:---|:---|:---|
| Processor | 64-bit dual-core x86 CPU | TensorFlow inference and the three capture threads |
| Memory | 4 GB RAM (8 GB recommended) | Model, SHAP explainer and flow table in memory |
| Storage | 2 GB free | Python environment, model artifacts, logs |
| Network interface | Wired or Wi-Fi adapter supported by Npcap | Live packet capture |
| Operating system | Windows 10 or 11, run as administrator | Npcap and Windows Firewall rules (netsh) |

## 4.2 Software Requirement

Table 4.3 lists the software and libraries with the versions used. The backend's Python dependencies are pinned in `backend/requirements.txt`; SHAP is pinned exactly, because the explainer uses an internal SHAP class whose interface may change between versions.

::table 4.3 | Software used in the project
| Software | Version | Purpose |
|:---|:---|:---|
| Windows 11 Home | 10.0.26300 | Operating system of the protected host |
| Python | 3.13.2 | Backend, model, extractor and tests |
| TensorFlow / Keras | 2.21.0 / 3.15.0 | CNN-LSTM training and inference |
| scikit-learn | 1.6.1 | Random forest, StandardScaler, metrics |
| NumPy / pandas | 2.5.1 / 3.0.3 | Numerical arrays and tables |
| SHAP | 0.52.0 | Kernel SHAP explanations |
| Scapy | 2.8.0 | Reading live packets (Npcap) and capture files |
| Flask, Flask-CORS | 3.x, 4.x | REST API of the backend |
| Matplotlib | 3.11 | Figures and diagrams of this report |
| Node.js | 24.22 | Building and serving the dashboard |
| React / TypeScript | 19.2 / 5.8 | Dashboard user interface |
| Vite / TanStack Router | 8.0 / 1.170 | Dashboard build tool and routing |
| Recharts / Tailwind CSS | 2.15 / 4.2 | Charts and styling of the dashboard |
| Wireshark | 4.6.9 | Recording packet captures |
| Npcap | 1.88 | Packet capture driver for Wireshark and the live engine |
| nmap (Termux, Android) | Termux package | Port scans from the second device |
| Windows Firewall (netsh advfirewall) | Built in | Enforcing blocks |
| Google Colab | Cloud service | GPU training and large evaluations |
| Git and GitHub | - | Version control and collaboration between the three members |

The backend must run with administrator rights, to capture packets and to change firewall rules, and no VPN may be active during live capture.

## 4.3 Functional Requirements

The functional requirements state what the system must do. Table 4.4 lists them with the part of the design that realises each one.

::table 4.4 | Functional requirements
| ID | Functional requirement | Realised in |
|:---|:---|:---|
| FR1 | Capture live packets from a selected network interface and read Wireshark captures (.pcap, .pcapng) | Section 3.6.1 |
| FR2 | Convert packets into bidirectional flows with the 20 CICFlowMeter-V3 features | Section 3.5.1 |
| FR3 | Accept flow CSV files that already contain the 20 features | Section 3.1 |
| FR4 | Classify windows of ten flows into benign traffic or one of 14 attacks, with a confidence | Section 3.5.3 |
| FR5 | Decide for each prediction: no action, review, recommendation or automatic action | Section 3.5.6 |
| FR6 | Block the attacking device with Windows Firewall rules, only within the allowed scope | Section 3.5.7 |
| FR7 | Revoke any block on request, also with the kill switch off | Section 3.4 |
| FR8 | Explain any prediction with a SHAP value per feature | Section 3.5.5 |
| FR9 | Show predictions, statistics, explanations and blocked devices in a web dashboard | Section 5.1 |
| FR10 | Log every prevention attempt, including refusals and expiries | Section 3.6.4 |

## 4.4 Non-Functional Requirements

The non-functional requirements state how well the system must do its work. Table 4.5 lists each with the measure by which it is met.

::table 4.5 | Non-functional requirements and how they are met
| ID | Requirement | Measure |
|:---|:---|:---|
| NFR1 | Performance: classification fast enough for live use | 1.48 ms per window on a laptop CPU |
| NFR2 | Responsiveness: an attack is reported and blocked within seconds | Scan blocked about 2 s after its first probes |
| NFR3 | Capacity: bursts of packets never wait for the model | Separate capture thread, 100,000-packet queue |
| NFR4 | Safety: no device outside the allowed scope is ever blocked | Kill switch, allow-list, deny-list; 35 tests |
| NFR5 | Reversibility: every action can be undone | Revoke without the kill switch; timed expiry |
| NFR6 | Reliability: rules in force survive a restart | Startup sweep and log-based rule registry |
| NFR7 | Explainability: explanations add up to the model's output | Additivity error about 10⁻⁹ |
| NFR8 | Usability: the system is operated from a web browser | Dashboard with live feed and revoke control |
| NFR9 | Portability: runs on an ordinary laptop without a GPU | Ryzen 3, 7.3 GB RAM, Windows 11 |
| NFR10 | Maintainability: every change can be checked | 88 automated tests; results written by scripts |

## 4.5 Development and Deployment Environment

**Repository.** The project is kept in one Git repository (Table 4.6).

::table 4.6 | Organisation of the project repository
| Folder | Contents |
|:---|:---|
| src/, output/ | Data cleaning, feature selection and MU-IoT handoff scripts and their metadata |
| model/ | Model definition and training, evaluation, baselines, SHAP analysis, prevention policy and engine, flow extractor, target selection, tests |
| model/artifacts/ | Trained models, scalers and label mappings for both datasets |
| model/results/ | Every reported result as a text or Markdown file, with the command that produced it |
| backend/ | Flask API, SHAP service, prevention runtime, live capture engine and their tests |
| frontend/ | React and TypeScript dashboard |
| docs/ | Interface documents, team reports, live demonstration checklist, this report |

**Configuration.** The behaviour of the running system is controlled by environment variables that are set when the backend is started (Table 4.7). No request to the API can change them; in particular, firewall execution can only be switched on by the person who starts the backend.

::table 4.7 | Environment variables of the backend
| Variable | Effect | Default |
|:---|:---|:---|
| IDS_PREVENTION_EXECUTION_ENABLED | Kill switch: "1" allows real firewall rules | Off |
| IDS_PREVENTION_DEMO_TARGETS | Single private LAN addresses that may be blocked, besides the RFC 5737 ranges | None |
| IDS_LIVE_IPV6 | "0" analyses IPv4 only in live capture | IPv4 and IPv6 |
| IDS_MAX_PCAP_MB | Largest capture file accepted for upload, in MB | 200 |
| OPENBLAS_NUM_THREADS | Set to "1" on a laptop with little free memory | Library default |

**Network ports.** The dashboard is served on port 8080, the backend API on port 5000, and the test page used in the live demonstration on port 8000.

**Setting up a machine.** A new machine is prepared in five steps:

1. Install Python 3.13 and the backend's dependencies (`pip install -r backend/requirements.txt`).
2. Install Wireshark together with the Npcap driver it offers.
3. Install Node.js and the dashboard's dependencies (`npm install` in `frontend/`).
4. Start the backend from an administrator PowerShell window, with the environment variables of Table 4.7.
5. Start the dashboard (`npm run dev` in `frontend/`) and open it in a browser.
