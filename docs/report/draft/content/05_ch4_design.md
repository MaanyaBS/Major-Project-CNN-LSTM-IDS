# 4 | System Design

This chapter presents the design of the system: its architecture (Section 4.1), the use cases it supports (Section 4.2), the flow of data through it (Section 4.3), the interactions between its components over time (Section 4.4) and the algorithms it uses (Section 4.5).

## 4.1 System Architecture

The system has three layers (Fig. 4.1). The presentation layer is the dashboard in the user's web browser. The application layer is a Flask backend that runs on the protected computer and contains the processing pipeline: input sources, the packet-to-flow extractor, the window builder, the CNN-LSTM classifier, the prevention policy, target selection, the prevention engine and the SHAP service. The host and data layer holds the trained artifacts, the prevention log and the Windows Firewall, which actually enforces the blocks.

::figure docs/report_assets/figures/fig_4_1_system_architecture.png | 4.1 | System architecture | 5.4

Data enters the application layer from one of three sources. A live network interface delivers packets through the Npcap driver, and an uploaded Wireshark capture (.pcap or .pcapng) delivers recorded packets; both go through the packet-to-flow extractor, which produces one row of 20 features per flow. An uploaded flow CSV already contains the features and goes straight to the window builder. From there every source follows the same path: windows of ten flows are scaled and classified, the predicted class and confidence are checked against the prevention policy, a target address is selected, and the prevention engine adds or refuses a firewall rule. The SHAP service explains any window on request by querying the model repeatedly. The dashboard talks to the backend only through a REST API with JSON messages.

Table 4.1 maps each component of Fig. 4.1 to the module that implements it and the team member responsible for it.

::table 4.1 | Components of the system and their implementation
| Component | Module | Responsibility |
|:---|:---|:---|
| Dashboard (batch analysis, live feed, SHAP view, blocked devices) | frontend/src/routes/dashboard.tsx, components/LiveFeed.tsx | Varshini D N |
| REST API, upload handling, CERT-In mapping | backend/app.py, backend/cert_in_mapping.py | Varshini D N |
| SHAP service | backend/shap_service.py | Varshini D N |
| Data cleaning, feature selection, MU-IoT handoff | src/ scripts, output/ metadata | Maanya B S |
| Packet-to-flow extractor | model/flow_features.py | Ruthwik Sai Ganesh |
| Live capture engine | backend/live_capture.py | Ruthwik Sai Ganesh |
| CNN-LSTM model and training | model/cnn_lstm_architecture.py, model/train_cnn_lstm.py | Ruthwik Sai Ganesh |
| Prevention policy | model/class_action_mapping.py | Ruthwik Sai Ganesh |
| Target selection | model/target_selection.py | Ruthwik Sai Ganesh |
| Prevention engine | model/prevention_executor.py, backend/prevention_runtime.py | Ruthwik Sai Ganesh |

Three design decisions shape the architecture.

1. **One pipeline for all inputs.** Live traffic, Wireshark captures and flow CSV files are converted to the same 20 features and go through the same model and policy, so a result obtained on a capture file carries over to live traffic.
2. **Blocking does not depend on the dashboard.** The live engine calls the prevention engine itself. A scan is blocked even if no browser is open, and the dashboard only reports what happened.
3. **Safety is enforced in the engine, not in the user interface.** The kill switch can only be turned on through an environment variable when the backend is started; no API request can enable execution or widen the set of addresses that may be blocked.

## 4.2 Use Case Diagram

Fig. 4.2 shows the use cases of the system. The primary actor is the security analyst who operates the dashboard. Two secondary actors take part: the network traffic source, which produces the packets that are analysed (and may be an attacker), and the Windows Firewall, which enforces and removes blocks.

::figure docs/report_assets/figures/fig_4_2_use_case.png | 4.2 | Use case diagram | 4.8

The analyst's ten use cases (UC1 to UC10) cover controlling the input, viewing results and managing blocks. Four system use cases (UC11 to UC14) are included by them: starting a capture or uploading a Wireshark file includes extracting flows from packets; extracting flows, or uploading a flow CSV, includes classifying windows; classification includes applying the prevention policy; and the policy includes adding a firewall rule when an automatic action is approved. Revoking a block (UC9) removes a rule.

## 4.3 Data Flow Diagram

The data flow diagrams show what data the system consumes and produces, without the timing of the interactions. At level 0 (Fig. 4.3(a)) the whole system is a single process. It receives live packets from the network interface and capture files or flow CSV files from the analyst, receives the analyst's requests (start or stop capture, upload, explain, revoke), returns verdicts, SHAP values and the list of blocked devices, and exchanges block and unblock rules and their status with the Windows Firewall.

::figure docs/report_assets/figures/fig_4_3a_dfd_level0.png | 4.3(a) | Data flow diagram, level 0 | 5.6

Level 1 (Fig. 4.3(b)) decomposes the system into seven processes and four data stores.

::figure docs/report_assets/figures/fig_4_3b_dfd_level1.png | 4.3(b) | Data flow diagram, level 1 | 4.8

The analyst never writes to the policy table or the engine's settings; requests reach process 5.0 only as revocations, and every attempt to act, including refusals, is written to the prevention log (D4).

## 4.4 Sequence Diagram

The sequence diagrams show the order of the interactions between the components for the four main scenarios.

**Live detection and blocking (Fig. 4.4(a)).** After the analyst starts a capture (messages 1 and 2), the live engine builds flows from the captured packets (3). Once per second it classifies the ten most recently ended flows (4 and 5), asks the policy for the action (6 and 7), selects the target (8) and calls the prevention engine (9), which runs its safety checks (10) before adding the firewall rules (11 and 12). The dashboard collects the results by polling once per second (14 and 15); blocking itself does not wait for it.

::figure docs/report_assets/figures/fig_4_4a_sequence_live_block.png | 4.4(a) | Sequence diagram: live detection and automatic blocking | 5.4

**Upload of a Wireshark capture (Fig. 4.4(b)).** The backend checks the file (2), extracts flows (3 and 4), builds windows (5), and classifies every window (6 and 7) and passes it through the policy (8 and 9); executions are attempted only within the allowed scope and with the kill switch on (10 and 11). A flow CSV skips steps 2 to 4.

::figure docs/report_assets/figures/fig_4_4b_sequence_upload.png | 4.4(b) | Sequence diagram: analysis of an uploaded capture | 5.4

**SHAP explanation (Fig. 4.4(c)).** The SHAP service groups the selected window's 200 inputs into 20 features (4), queries the model on 1,000 perturbed samples built from a real-traffic background (5 and 6) and solves Kernel SHAP's weighted regression, checking that the attributions add up to the model's output (7).

::figure docs/report_assets/figures/fig_4_4c_sequence_shap.png | 4.4(c) | Sequence diagram: SHAP explanation of a window | 5.0

**Revocation of a block (Fig. 4.4(d)).** Revocation checks only the target's scope and administrator rights; the kill switch is not required, so a block can always be undone (7).

::figure docs/report_assets/figures/fig_4_4d_sequence_revoke.png | 4.4(d) | Sequence diagram: revoking a firewall block | 5.0

## 4.5 Algorithms Used

### 4.5.1 Packet-to-Flow Extraction

The extractor groups packets into bidirectional flows identified by the five-tuple (source and destination address and port, protocol); the direction of a flow's first packet is its forward direction. For each flow it keeps the length L and timestamp t of every packet in each direction. When the flow ends, the 20 features are computed with CICFlowMeter-V3's definitions. Packet-length statistics count the first packet L₁ twice, and standard deviations are sample standard deviations, so for a flow of n packets:

::equation pl_mean | 4.1

::equation pl_std | 4.2

::equation avg_size | 4.3

Inter-arrival times are differences between consecutive packet timestamps, in whole microseconds:

::equation iat | 4.4

::algorithm 4.1 | Packet-to-flow extraction (model/flow_features.py)
```
for each packet p (from Npcap or a capture file):
    parse IPv4 or IPv6 header, skip IPv6 extension headers; keep TCP and UDP
    length := transport payload bytes, padded to Ethernet's 60-byte minimum
    key := (src, sport, dst, dport, proto), direction-independent
    if key not in table:
        create flow; forward := direction of p
        add p; continue                  # a FIN that starts a flow does not end it
    flow := table[key]
    if p.time - flow.start > 120 s:
        emit features(flow); create a new flow with p; continue
    add p to flow (forward or backward)
    if p has FIN, or (live mode and p has RST):
        emit features(flow); remove flow from table
at end of capture: emit features of every open flow
```

### 4.5.2 Window Construction and Scaling

Each flow's 20 features are standardised with Equation (3.1), using the mean and standard deviation of the training rows, and windows of ten consecutive flows are formed as in Equation (3.2). In training and evaluation the window slides by one flow. In live operation the engine classifies, once per second, the window made of the ten most recently ended flows.

### 4.5.3 Hybrid CNN-LSTM Classifier

The classifier (Fig. 4.5, Table 4.2) maps a window of 10 x 20 values to a probability for each of the 15 classes.

::figure docs/report_assets/figures/fig_4_5_cnn_lstm_architecture.png | 4.5 | Architecture of the hybrid CNN-LSTM model with the output shape of each layer | 5.6

::table 4.2 | Layers of the CNN-LSTM models
| Layer | CICIDS2017 model | MU-IoT model |
|:---|:---|:---|
| Input | 10 flows x 20 features | 20 flows x 38 features |
| Conv1D, 64 filters, kernel 3, ReLU, no padding; BatchNorm; MaxPool 2 | Yes | Yes |
| Conv1D, 128 filters, kernel 3, ReLU, same padding; BatchNorm; MaxPool 2 | Yes | Yes |
| LSTM, 64 units | Yes | Yes |
| Dense, 64 units, ReLU | Yes | Yes |
| Dense, softmax | 15 classes | 7 classes |
| Trainable and non-trainable parameters | 83,919 | 86,855 |
| Numerical precision | float32 | mixed float16 (float32 output) |

**Convolution.** A one-dimensional convolution slides 64 filters of width three along the ten flows. Each filter k combines three neighbouring flows t, t+1, t+2 over all C input features with weights w and a bias b, followed by the rectified linear unit:

::equation conv | 4.5

**Batch normalisation and pooling.** Batch normalisation rescales each filter's output with the mean μ and variance σ² of the mini-batch and two learned parameters γ and β, which stabilises training; max pooling keeps the larger of each pair of neighbouring values and halves the length of the sequence:

::equation bn | 4.6

::equation pool | 4.7

The second block repeats these operations with 128 filters and same padding. After both blocks the ten flows have become a sequence of two steps of 128 learned features.

**LSTM.** The LSTM [@K22] reads this sequence step by step. At each step t its forget gate f, input gate i and output gate o, computed from the current input x and the previous hidden state h with weight matrices W and U and biases b, decide what the memory cell c forgets, stores and exposes:

::equation lstm_gates | 4.8

::equation lstm_cell | 4.9

::equation lstm_out | 4.10

where σ is the logistic sigmoid and ⊙ is element-wise multiplication. The final hidden state h, of 64 values, summarises the whole window.

**Output.** A dense layer of 64 units with ReLU is followed by a softmax layer that turns the K output scores z into class probabilities. The predicted class is the one with the largest probability, and that probability is the prediction's confidence c:

::equation softmax | 4.11

**Training objective.** The model minimises the class-weighted sparse categorical cross-entropy over N training windows with true classes y:

::equation loss | 4.12

with the deployed square-root-balanced class weights, where Nₖ is the number of training windows of class k:

::equation class_weights | 4.13

Square-root weights give rare classes more influence than they would have otherwise without letting them dominate: a class one hundred times rarer than another is weighted ten times more, not one hundred times.

### 4.5.4 Random-Forest Baseline

The baseline is a random forest [@K29] of 100 decision trees with a fixed random seed of 42, trained on single flows with the same features and split. Each tree is grown on a bootstrap sample of the training data, and at each split considers a random subset of the features; the forest predicts the class chosen by most trees. It is scored on the last flow of each CNN-LSTM test window, so both models see the same test examples.

### 4.5.5 SHAP Explanations

SHAP [@K16] explains a prediction f(x) by giving every feature i a value φᵢ, its Shapley value: the average change in the model's output when feature i is added to a subset S of the other features, over all subsets F, weighted by how many orderings produce each subset:

::equation shapley | 4.14

The values satisfy local accuracy: together with the base value φ₀, the model's average output over the background data, they add up exactly to the prediction being explained:

::equation additivity | 4.15

Computing Equation (4.14) exactly requires the model's output for every subset of features, which is infeasible for 20 features. Kernel SHAP estimates the values by sampling subsets (coalitions) z of the M features, replacing absent features with values from the background data, and fitting a weighted linear regression with the SHAP kernel weight:

::equation kernel | 4.16

The dashboard uses Kernel SHAP with M = 20 feature groups, 1,000 sampled coalitions and a background of 100 real training windows. The offline error analysis uses expected gradients, which average the gradient of the model along straight paths from background samples x' to the input x:

::equation expected_gradients | 4.17

and compares the mean SHAP profiles a and b of two groups of windows with the cosine similarity:

::equation cosine | 4.18

### 4.5.6 Prevention Policy

The policy table (Table 4.3) assigns every class an action, a severity and a confidence threshold. Thresholds were calibrated inversely to each class's F1 score on the test set, through a decreasing piecewise-linear curve: the CICIDS2017 classes define the calibration points (F1ⱼ, θⱼ), and the threshold of any other F1 value, such as those of the MU-IoT classes, is interpolated between the two nearest points:

::equation threshold | 4.19

::table 4.3 | Prevention policy for the CICIDS2017 classes
| Class | Action | Severity | F1 | Threshold | Automatic |
|:---|:---|:---|---:|---:|:---|
| BENIGN | No action | Low | 0.991 | 0.50 | - |
| DDoS | Block IP | Critical | 0.990 | 0.55 | Yes |
| DoS Hulk | Rate limit (120 s) | High | 0.990 | 0.55 | Yes |
| PortScan | Block IP | Medium | 0.971 | 0.60 | Yes |
| DoS Slowhttptest | Drop connection (60 s) | Medium | 0.886 | 0.65 | Yes |
| DoS GoldenEye | Rate limit (120 s) | High | 0.816 | 0.70 | Yes |
| FTP-Patator | Block IP | High | 0.773 | 0.72 | Yes |
| DoS slowloris | Drop connection (60 s) | Medium | 0.725 | 0.75 | Yes |
| SSH-Patator | Block IP | High | 0.656 | 0.78 | Yes |
| Web Attack - Brute Force | Block IP | High | 0.125 | 0.92 | No, review |
| Bot | Isolate host | High | 0.056 | 0.94 | No, review |
| Web Attack - XSS | Sanitise input | High | 0.006 | 0.97 | No, review |
| Web Attack - Sql Injection | Block IP | Critical | - | - | No, review |
| Heartbleed | Terminate session | Critical | - | - | No, review |
| Infiltration | Isolate host | Critical | - | - | No, review |

For MU-IoT the same curve gives thresholds of 0.63 for Injection, 0.71 for Password_Hacking and 0.84 for DDoS and Scan, from the F1 scores on the held-out recordings; every automatic MU-IoT action is a block of the source address, and MiTM and Spyware are locked to review. A prediction ŷ with confidence c triggers an automatic action only if it is not benign, its class is not in the set 𝓡 of classes locked to review, and its confidence reaches the class's threshold:

::equation decision | 4.20

Otherwise the prediction is held for review (locked class or confidence below threshold) or needs no action (benign). The decision procedure, including target selection and the execution checks, is shown as a flowchart in Fig. 4.6.

::figure docs/report_assets/figures/fig_4_6_prevention_flowchart.png | 4.6 | Flowchart of the prevention decision for one window | 4.6

### 4.5.7 Target Selection and Firewall Execution

**Target selection.** A window contains ten flows that may come from several devices. The target is the most frequent source address a among the eligible sources A of the window W:

::equation target | 4.21

A source is eligible only if it is a private (local network) IPv4 unicast address, is neither the protected computer itself nor its gateway, and has sent traffic to the protected computer. The last condition was added after the live run (Section 6.3.7): a device that only broadcasts discovery messages to the whole network never addresses the protected computer and must never be blocked by it. If no source is eligible, the action stays a recommendation.

**Execution.** The prevention engine turns an approved action into two Windows Firewall rules, inbound and outbound, named after the action and the address (for example `IDS_DEMO_block_ip_<address>_in`), through `netsh advfirewall`. Algorithm 4.2 shows the checks it applies.

::algorithm 4.2 | Execution of a prevention action (model/prevention_executor.py)
```
execute(action, target, class, confidence):
    if kill switch is off:                       refuse "execution disabled"
    if target not a valid single IPv4 address:   refuse
    if target in deny-list (loopback, broadcast, unspecified): refuse
    if target not in RFC 5737 TEST-NET ranges and
       target not listed in IDS_PREVENTION_DEMO_TARGETS:      refuse "out of scope"
    if not running as administrator:             refuse
    if a rule for target is already active:      return "already blocked"
    add inbound and outbound block rules (netsh advfirewall)
    if action is drop_connection or rate_limit:  start expiry timer (60 s / 120 s)
    log the attempt and its outcome (JSONL)

revoke(action, target):                          # kill switch not required
    if target out of scope or not administrator: refuse
    delete both rules; cancel timer; log the revocation
```

Only one rule is kept per device, whatever class flags it and however many windows do, and a startup sweep restores the engine's view of the firewall after a crash. Rate limiting is implemented as a temporary full block, because Windows offers no simple per-address bandwidth limit, and input sanitisation against XSS remains a recommendation, because a network firewall cannot perform it.
