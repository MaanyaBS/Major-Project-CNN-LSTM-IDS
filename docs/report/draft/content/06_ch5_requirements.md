# 5 | Hardware and Software Requirement

This chapter lists the hardware and software that were used to develop, train and run the system, and the minimum requirements for running it. The project was developed on ordinary student equipment: one laptop serves as both development machine and protected host, and model training was done on free cloud GPUs.

## 5.1 Hardware Requirement

Table 5.1 lists the hardware actually used. All speed measurements in this report were taken on the laptop listed, without a GPU.

::table 5.1 | Hardware used in the project
| Item | Specification | Use |
|:---|:---|:---|
| Laptop (protected host) | AMD Ryzen 3 5300U, 4 cores / 8 threads, 7.3 GB RAM, Windows 11 Home, Wi-Fi | Development, backend, dashboard, live capture, firewall |
| Cloud GPU | Google Colab GPU runtime (NVIDIA T4 for the MU-IoT model) | Training, large evaluations, extractor validation |
| Second device (attacker) | Android tablet with Termux and nmap | Port scans and page requests in the live tests |
| Network | Phone hotspot (captures) and a home Wi-Fi router (live run) | Shared network for the protected host and the second device |

Training was done in the cloud because the full datasets do not fit comfortably in the laptop's memory: the MU-IoT feature matrix alone has almost four million rows, and training draws up to 300,000 windows per class per epoch. Inference, by contrast, is light: one window takes 1.48 ms on the laptop's CPU, so a GPU is not needed to run the system.

Table 5.2 gives the minimum requirements for running the trained system on one protected host.

::table 5.2 | Minimum hardware requirements for running the system
| Component | Minimum | Reason |
|:---|:---|:---|
| Processor | 64-bit dual-core x86 CPU | TensorFlow inference and the three capture threads |
| Memory | 4 GB RAM (8 GB recommended) | Model, SHAP explainer and flow table in memory |
| Storage | 2 GB free | Python environment, model artifacts, logs |
| Network interface | Wired or Wi-Fi adapter supported by Npcap | Live packet capture |
| Operating system | Windows 10 or 11, run as administrator | Npcap and Windows Firewall rules (netsh) |

## 5.2 Software Requirement

Table 5.3 lists the software and libraries with the versions used. The backend's Python dependencies are pinned in `backend/requirements.txt`; SHAP is pinned exactly, because the explainer uses an internal SHAP class whose interface may change between versions.

::table 5.3 | Software used in the project
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
