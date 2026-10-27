# 1 | Introduction

## 1.1 Introduction

Computer networks carry almost every service an organisation depends on, from email and file sharing to industrial control and the growing number of Internet-of-Things (IoT) devices in homes, campuses and hospitals. Every one of these services is reachable over the network, and every one can be probed, overloaded or broken into from it. An attacker usually begins by scanning a network for open services, continues by guessing passwords or exploiting a vulnerable application, and may finish by flooding a server until it stops answering legitimate users. Each of these steps leaves traces in the traffic: unusual numbers of connections, unusual packet sizes, unusual timing. An intrusion detection system (IDS) watches the traffic for such traces and raises an alert when it finds them.

This report describes the design, implementation and evaluation of an intrusion detection and prevention system built around a hybrid deep-learning model that combines a convolutional neural network (CNN) with a long short-term memory (LSTM) network. The model reads short sequences of network flows, decides whether they are benign or belong to one of several attack classes, and explains each decision with SHAP (SHapley Additive exPlanations). A prevention layer turns trusted decisions into Windows Firewall rules that block the attacking device, and a web dashboard shows the predictions, the explanations and the blocked devices. The system works on recorded datasets, on packet captures made with Wireshark, and on live traffic captured from the network interface of the protected computer.

### 1.1.1 Network Intrusions

A network intrusion is any unauthorised activity on a network: an attempt to discover, access, disrupt or misuse systems that the attacker has no right to use. The attacks studied in this project fall into a few families, each with its own traffic pattern: reconnaissance (a port scan produces many short flows from one source, most answered by a reset), denial of service (floods of requests, or many connections held open with very slow requests), brute force (automated password guessing against FTP, SSH or a web login), web application attacks (cross-site scripting and SQL injection), exploits, botnets and infiltration. The CICIDS2017 dataset [@K9], the main benchmark used in this project, contains fourteen attack classes from these families (Table 1.1). The MU-IoT dataset [@K30], recorded on an IoT testbed at Manipur University, India, contains six attack classes against IoT devices and services (Table 1.2).

::table 1.1 | Traffic classes of the CICIDS2017 dataset
| Class | Family | Description |
|:---|:---|:---|
| BENIGN | Normal | Ordinary user activity (web, email, file transfer) |
| PortScan | Reconnaissance | Scans of the victim's ports with nmap |
| DDoS | Denial of service | Flood from several attacking machines (LOIC) |
| DoS Hulk | Denial of service | Flood of unique HTTP requests |
| DoS GoldenEye | Denial of service | HTTP flood that keeps connections alive |
| DoS slowloris | Denial of service | Many connections held open with partial requests |
| DoS Slowhttptest | Denial of service | Slow HTTP requests and slow reading of replies |
| FTP-Patator | Brute force | Password guessing against an FTP server |
| SSH-Patator | Brute force | Password guessing against an SSH server |
| Web Attack - Brute Force | Web attack | Password guessing against a web login form |
| Web Attack - XSS | Web attack | Cross-site scripting through a vulnerable web application |
| Web Attack - Sql Injection | Web attack | SQL injection through a vulnerable web application |
| Heartbleed | Exploit | Memory disclosure through the OpenSSL Heartbleed flaw |
| Bot | Botnet | Infected hosts contacting the Ares botnet's command server |
| Infiltration | Infiltration | Internal host compromised and used to scan the network |

::table 1.2 | Traffic classes of the MU-IoT dataset used in this project
| Class | Description |
|:---|:---|
| normal | Benign IoT and user traffic on the testbed |
| DDoS | Flooding attacks against IoT services (for example UDP floods) |
| Scan | Port and vulnerability scans of IoT devices |
| Password_Hacking | Dictionary and brute-force attacks on IoT services such as MQTT |
| Injection | Application-layer injection attacks such as cross-site scripting |
| MiTM | Man-in-the-middle interception of IoT traffic |
| Spyware | Spyware activity on IoT devices |

### 1.1.2 Intrusion Detection Systems

Intrusion detection systems are commonly divided along two lines [@K3, K1]. By the data they observe, a host-based IDS inspects the logs and processes of one computer, whereas a network-based IDS (NIDS) inspects the traffic passing a point of the network. By the way they decide, a signature-based IDS matches traffic against known attack patterns and misses attacks it has no signature for, whereas an anomaly-based IDS learns what normal traffic looks like and reports departures from it, at the cost of more false alarms [@K4].

Most modern NIDS research works on flows rather than on individual packets. A flow is the group of packets exchanged between two endpoints in one connection, identified by the source and destination addresses and ports and the protocol. Tools such as CICFlowMeter [@K27] summarise every flow with dozens of statistical features: its duration, the number and sizes of packets in each direction, and the times between packets. Flow features are compact, they do not require reading the encrypted payload, and they are the representation in which the CICIDS2017 dataset is published.

### 1.1.3 Intrusion Prevention

An intrusion prevention system (IPS) goes one step further than detection: it acts on its alerts, for example by dropping the attacker's packets or blocking its address in a firewall. Acting is more useful than alerting, because a scan or a flood is stopped instead of merely recorded, but it is also riskier. A detection model that is wrong 1% of the time on benign traffic produces a steady stream of false alarms; a prevention system with the same error rate cuts legitimate users off the network. Any system that blocks automatically must therefore decide when a prediction is reliable enough to act on, and must keep a human in control of the cases where it is not.

### 1.1.4 Machine Learning and Deep Learning for Intrusion Detection

Machine-learning classifiers learn the boundary between benign and malicious traffic from labelled examples instead of hand-written signatures. Classical models such as random forests [@K29] work on one flow at a time and remain strong baselines. Deep-learning models learn their own intermediate representations: convolutional networks [@K23] detect local patterns, and recurrent networks such as the LSTM [@K22] model how a sequence develops over time. Studies across several datasets have found deep models competitive with classical ones [@K7, K25], and hybrid CNN-LSTM architectures are a common choice for sequences of flows [@K8], because an attack often shows itself not in one flow but in a run of similar flows from the same source.

High benchmark scores have to be read with care. Neighbouring flows in a capture are often near-identical, so a random split of the data places near-copies in both the training and the test set and rewards memorisation; benign traffic dominates most datasets, so overall accuracy hides failures on rare attacks; and a model that does well on traffic recorded in a laboratory may behave differently on a real network [@K2, K28]. This project treats these pitfalls as part of the problem rather than as footnotes.

### 1.1.5 Explainable Artificial Intelligence

A deep network does not explain itself. When it flags a device as an attacker, the analyst who has to decide whether to block that device needs to know why. Explainable artificial intelligence (XAI) provides methods that attribute a model's prediction to its inputs. SHAP [@K16] is the most widely used of them: it assigns each input feature a contribution, based on Shapley values from cooperative game theory, such that the contributions add up exactly to the model's output. In this project SHAP serves two purposes: the dashboard shows the contributions behind every prediction, and an offline analysis uses them to find out why the model makes the mistakes it makes.

## 1.2 Problem Statement

Deep-learning intrusion detectors are usually evaluated as accuracy figures on benchmark datasets. Such figures do not show whether a detector is better than a simple classical model trained on the same examples, whether it recognises attack recordings it has never seen, why it fails when it fails, or whether it can work on live traffic at all. A detector that is to protect a network must in addition act on its decisions, which raises a question that benchmark scores do not answer: when may a model's prediction be trusted to block a device automatically, and how is the damage limited when it is wrong?

The problem addressed by this project is therefore to build a hybrid CNN-LSTM intrusion detection system that (a) is evaluated honestly against a fair baseline with leakage-controlled data splits, on a benchmark dataset and on Indian IoT traffic; (b) explains its decisions; (c) prevents attacks automatically only where its measured reliability justifies it; and (d) works on live network traffic and on real packet captures, not only on prepared test files.

## 1.3 Motivation

The first version of this system analysed flow records uploaded as CSV files taken from the CICIDS2017 test set. At the project review, the guide asked for two changes: the input had to be live traffic, and it had to come from real captures made with free tools such as Wireshark rather than from prepared test data. The team added a third requirement of its own: detection alone would not stop an attack, so the system should also prevent it, live.

Meeting these requirements turned out to be the most instructive part of the project: live use requires exactly the training features, quirks included; automatic blocking on a shared network requires safety limits; and present-day traffic exposes the gap between benchmark data and real networks. The title of the project refers to Indian network databases because the second dataset, MU-IoT, was recorded at Manipur University, India, and is used to test whether the approach carries over to IoT traffic.

## 1.4 Objectives

The objectives of the project, detailed in Section 3.1, are to:

1. Detect fourteen attack classes from windows of consecutive network flows with a hybrid CNN-LSTM model.
2. Evaluate the model with leakage-controlled splits against a random-forest baseline on identical examples, on CICIDS2017 and on the Indian MU-IoT dataset.
3. Explain the model's predictions with SHAP, both per prediction in the dashboard and as an analysis of its errors.
4. Prevent attacks through a per-class policy whose automatic actions are limited by measured reliability and by explicit safety checks.
5. Operate on live traffic and on Wireshark captures, through a packet-to-flow extractor validated against the original dataset.

## 1.5 Scope of the Project

The project covers the full path from data to action. Within that path its scope is deliberately bounded, and the bounds are stated here so that the results can be read correctly.

- **Data.** Two existing, published datasets are used: CICIDS2017 and MU-IoT. No new labelled dataset was collected. Own traffic was captured with Wireshark and live, but it carries no ground-truth labels and is used to test the system's behaviour, not to measure accuracy.
- **Deployment.** The system runs on the computer it protects (a Windows laptop) and blocks devices through that computer's own firewall. It is not a network appliance placed in front of other machines, and it is not hosted in the cloud.
- **Prevention.** Prevention is deliberately limited (called IPS-lite in this report): rules are created only for documentation addresses reserved by RFC 5737 or for local devices listed explicitly for a demonstration, and only when a kill switch is turned on.
- **Live attacks.** One attack type, a TCP port scan, was run live against the system, on one network, from one device. The other attack classes need victim servers, vulnerable services or several attacking machines on an isolated laboratory network, and were evaluated on the recorded datasets only.
- **Dashboard.** The dashboard serves the CICIDS2017 model, because live traffic is converted into CICIDS2017 features. The MU-IoT model is evaluated offline.

## 1.6 Organisation of the Report

Chapter 2 surveys the literature on intrusion detection datasets, deep-learning detectors, hybrid CNN-LSTM models and explainable AI, and identifies the gap this project addresses. Chapter 3 states the objectives and describes the methodology: the datasets, preprocessing, evaluation design, model, explainability, prevention policy, live capture and dashboard. Chapter 4 presents the system design: the architecture, use case, data flow and sequence diagrams, and the algorithms with their equations. Chapter 5 lists the hardware and software requirements. Chapter 6 describes the implementation and testing and reports all results, including the live run. The report closes with conclusions and future enhancements, the references and appendices.
