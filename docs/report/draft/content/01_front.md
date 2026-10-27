::toc

::lof

::lot

::heading NOMENCLATURE

The abbreviations and symbols used in this report are listed below. Symbols are also defined where they first appear.

::table - | Abbreviations
| Abbreviation | Meaning |
|:---|:---|
| API | Application Programming Interface |
| CICIDS2017 | Canadian Institute for Cybersecurity Intrusion Detection Evaluation Dataset 2017 |
| CNN | Convolutional Neural Network |
| CERT-In | Indian Computer Emergency Response Team |
| CSV | Comma-Separated Values |
| DDoS / DoS | Distributed Denial of Service / Denial of Service |
| F1 | Harmonic mean of precision and recall |
| FIN / RST / SYN | TCP flags: finish, reset, synchronise |
| IAT | Inter-Arrival Time |
| IDS / IPS | Intrusion Detection System / Intrusion Prevention System |
| IoT / IIoT | Internet of Things / Industrial Internet of Things |
| IPv4 / IPv6 | Internet Protocol version 4 / version 6 |
| LAN | Local Area Network |
| LIME | Local Interpretable Model-agnostic Explanations |
| LSTM | Long Short-Term Memory |
| MiTM | Man-in-the-Middle |
| ML / DL | Machine Learning / Deep Learning |
| MQTT | Message Queuing Telemetry Transport |
| MU-IoT | Manipur University IoT intrusion dataset |
| NIDS | Network Intrusion Detection System |
| Npcap | Windows packet capture driver used by Wireshark |
| pcap / pcapng | Packet capture file formats |
| QUIC | UDP-based transport protocol used by modern web traffic |
| ReLU | Rectified Linear Unit |
| RF | Random Forest |
| RFC 5737 | Internet standard that reserves three address ranges for documentation (TEST-NET) |
| SHAP | SHapley Additive exPlanations |
| SSDP | Simple Service Discovery Protocol |
| TCP / UDP | Transmission Control Protocol / User Datagram Protocol |
| XAI | Explainable Artificial Intelligence |
| XSS | Cross-Site Scripting |

::table - | Symbols
| Symbol | Meaning |
|:---|:---|
| x, z; μ, σ | Raw and standardised feature values; mean and standard deviation |
| Xₜ | Window of ten consecutive standardised flows ending at flow t |
| K, N, Nₖ | Number of classes, examples, and examples of class k |
| wₖ | Class weight of class k in the training loss |
| ŷₖ, c | Predicted probability of class k; confidence (largest probability) |
| Pₖ, Rₖ, F1ₖ | Precision, recall and F1 score of class k |
| fₜ, iₜ, oₜ | LSTM forget, input and output gates at step t |
| cₜ, hₜ | LSTM cell state and hidden state at step t |
| σ(·), tanh(·) | Logistic sigmoid and hyperbolic tangent |
| φᵢ, φ₀ | SHAP value of feature i; base value (expected model output) |
| θₖ | Automatic-action confidence threshold of class k |
| 𝓡 | Set of classes locked to human review |
| Lᵢ, tᵢ | Length and timestamp of the i-th packet of a flow |

::frontend
