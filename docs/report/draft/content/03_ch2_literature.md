# 2 | Literature Survey

## 2.1 Literature Survey

The survey is organised around the questions the project has to answer: what intrusion detection is and what makes it hard (Section 2.1.1), which datasets exist and what is known about their flaws (Sections 2.1.2 and 2.1.3), which deep-learning models have been applied (Sections 2.1.4 and 2.1.5), and how their decisions can be explained (Section 2.1.6). Section 2.2 summarises the surveyed works in a table, and Section 2.3 states the gap this project addresses. Only what each work states about its own method, data and findings is reported here; numerical results of other papers are not quoted, because they were obtained on different data and splits and are not comparable with ours.

### 2.1.1 Foundations of Intrusion Detection

**Surveys of methods.** Buczak and Guven [@K1] surveyed data-mining and machine-learning methods for cyber-security intrusion detection, covering misuse (signature) and anomaly detection, and described for each family of methods how it has been applied, what data it needs and how expensive it is to train and to run. They emphasised that the field lacks good labelled datasets and that a method's practical value depends on its time complexity and on how often it must be retrained. Khraisat et al. [@K3] gave a taxonomy of intrusion detection systems that separates signature-based from anomaly-based detection, reviewed the machine-learning techniques used for anomaly detection and the public datasets used to evaluate them, and discussed evasion techniques that attackers use against detectors. García-Teodoro et al. [@K4] reviewed anomaly-based network intrusion detection, grouping techniques into statistical, knowledge-based and machine-learning approaches, and named the open problems that remain relevant: high false-alarm rates, the difficulty of obtaining representative training data, and the lack of realistic evaluation.

Liu and Lang [@K34] surveyed machine-learning and deep-learning methods for intrusion detection and organised them by the data they consume: packets, flows, sessions or logs, a distinction that places this project among the flow-based methods. Ahmad et al. [@K37] carried out a systematic study of machine-learning and deep-learning approaches to network intrusion detection, compared the datasets they use, and discussed open problems such as imbalanced data and the lack of recent, realistic datasets.

**Pitfalls of machine learning in security.** Sommer and Paxson [@K2] argued that machine learning has been far less successful in operational network intrusion detection than in other domains, and explained why: detecting attacks is closer to finding outliers than to classifying well-defined categories, errors are very costly, there is a semantic gap between an alert and what the operator must do with it, network traffic is extremely diverse, and sound evaluation is hard. Arp et al. [@K28] examined machine-learning work in computer security systematically and identified ten recurring pitfalls, among them sampling bias, label inaccuracy, data snooping (information from the test data influencing training), inappropriate baselines, inappropriate performance measures, and evaluation in the laboratory only. These two works shaped the evaluation design of this project directly: a chronological split against data snooping, a random-forest baseline on identical examples, macro F1 alongside accuracy, and measurement on real traffic.

### 2.1.2 Benchmark Datasets and Flow Features

**KDD Cup 99 and its problems.** Tavallaee et al. [@K15] analysed the KDD Cup 99 dataset, for many years the standard benchmark, and showed that it contains a very large number of redundant records, which bias learning towards frequent records and make evaluation results unreliable. They proposed a reduced dataset, NSL-KDD, as a remedy. The analysis is an early example of a recurring lesson: a benchmark's flaws are inherited by every model evaluated on it.

**UNSW-NB15.** Moustafa and Slay [@K10] created UNSW-NB15 with a commercial traffic generator in a cyber-range environment, combining modern normal traffic with nine families of attacks, and described its feature set and its differences from the older KDD datasets.

**CICIDS2017.** Sharafaldin et al. [@K9] generated CICIDS2017 at the Canadian Institute for Cybersecurity. Benign background traffic was produced from profiles of human behaviour, and attacks were run over five working days: brute force against FTP and SSH, several denial-of-service tools, Heartbleed, web attacks, infiltration, a botnet, port scans and DDoS. Flows were extracted with CICFlowMeter, which computes more than 80 features per flow, and labelled. The dataset also publishes the original packet captures, which this project uses to validate its own flow extractor.

**CICFlowMeter.** The flow-feature tool behind CICIDS2017 was introduced by Lashkari et al. [@K27] in a study that characterised Tor traffic with time-based flow features. Because the CICIDS2017 features are defined by this tool's behaviour, a model trained on them can only be applied to new traffic if the new traffic is processed in exactly the same way.

**Flaws in CICIDS2017.** Engelen, Rimmer and Joosen [@K26] examined CICIDS2017 and CICFlowMeter in detail and documented errors in both flow construction and labelling. One artefact is the "TCP appendix": after a TCP connection is terminated by a FIN packet, the remaining packets of the connection are collected into a separate, new flow. Their study is directly relevant here: the model in this project was trained on flows built this way, so the project's live extractor deliberately reproduces the artefact instead of correcting it (Section 3.5.1).

**Further re-examinations.** Rosay et al. [@K40] examined CIC-IDS2017 in detail, documented problems in the dataset and studied their effect on the evaluation of machine-learning detectors. Lanvin et al. [@K41] identified further errors in CICIDS2017 and showed that correcting them changes the measured detection performance significantly. Together with Engelen et al. [@K26], these studies show that results on CICIDS2017 depend on how its flows were built and labelled. This is why the present project validated its own extractor against the original capture instead of assuming that the published features are exact.

**Feature standardisation.** Sarhan et al. [@K38] pointed out that intrusion detection datasets are published with different feature sets, so that a model trained on one dataset cannot be evaluated on another, and proposed a standard flow-based feature set shared across datasets. This project meets the same problem: its CICIDS2017 and MU-IoT models use different features (20 and 38) and can only be compared side by side, not on each other's data.

**Dataset surveys.** Ring et al. [@K14] surveyed network-based intrusion detection datasets and compared them along a common set of properties, such as the type of traffic, the recording environment, labelling and the formats in which the data are published. The survey makes the point that no single dataset is representative of all networks, which supports evaluating on more than one dataset, as this project does.

### 2.1.3 IoT Intrusion Datasets

IoT devices run different protocols (MQTT, CoAP, RTSP), have limited resources and are often poorly secured, so IoT traffic and IoT attacks differ from those in enterprise datasets such as CICIDS2017.

- **N-BaIoT.** Meidan et al. [@K11] infected commercial IoT devices with the Mirai and BASHLITE botnets and detected the infected devices from their network traffic with deep autoencoders trained per device on benign traffic only.
- **Bot-IoT.** Koroniotis et al. [@K12] built a realistic testbed for IoT botnet traffic and network forensics, combining normal traffic with denial of service, distributed denial of service, scanning and information-theft attacks.
- **TON_IoT.** Alsaedi et al. [@K13] collected telemetry data from IoT and industrial IoT services together with operating-system and network data, labelled for both binary and multi-class detection, and evaluated machine-learning models on it.
- **MU-IoT.** Clinton and Hoque [@K30] recorded a new IoT intrusion dataset on a testbed at Manipur University, India, covering attacks on both the network layer and the application layer of IoT devices. It is the Indian dataset used in this project.

**Deep learning for IoT attacks.** Diro and Chilamkurti [@K24] proposed a distributed deep-learning scheme for attack detection in the Internet of Things, in which detection is performed close to the devices, and reported that the deep model was more effective than shallow models in their experiments.

### 2.1.4 Deep Learning for Intrusion Detection

**Building blocks.** Two architectures underlie the model of this project. LeCun et al. [@K23] showed how convolutional networks trained by gradient descent learn local features directly from raw input, using shared weights and pooling. Hochreiter and Schmidhuber [@K22] introduced the long short-term memory, a recurrent unit whose gated memory cell keeps information over long sequences and avoids the vanishing gradients of simple recurrent networks.

**Deep detectors.** Shone et al. [@K5] proposed a non-symmetric deep autoencoder for unsupervised feature learning, stacked and combined with a random-forest classifier, and evaluated it on the KDD Cup 99 and NSL-KDD benchmarks. Yin et al. [@K6] applied a recurrent neural network to NSL-KDD for both binary and multi-class detection and compared it with classical classifiers. Vinayakumar et al. [@K7] evaluated deep neural networks of different depths against classical machine-learning classifiers on several datasets, including KDD Cup 99, NSL-KDD, UNSW-NB15 and CICIDS2017, and proposed a scalable hybrid framework for monitoring network traffic and host events. Ferrag et al. [@K25] surveyed deep-learning approaches to intrusion detection, described the datasets used in the field, and compared seven deep-learning models experimentally on two recent datasets.

Javaid et al. [@K39] applied self-taught learning, in which a sparse autoencoder learns a representation from unlabelled data before a classifier is trained on it, to the NSL-KDD dataset. Kim et al. [@K32] were among the first to apply a long short-term memory network to intrusion detection, evaluating it on KDD Cup 99. These works established recurrent and representation-learning models for intrusion detection, but on the KDD-family datasets, whose limitations are discussed in Section 2.1.2.
### 2.1.5 Hybrid CNN-LSTM Models

Wang et al. [@K33] proposed HAST-IDS, which learns the spatial features of network traffic with a convolutional network and their temporal features with an LSTM, so that features no longer have to be engineered by hand, and evaluated it on the DARPA 1998 and ISCX 2012 datasets.

Halbouni et al. [@K8] proposed a hybrid CNN-LSTM network for network intrusion detection: convolutional layers extract spatial features from the flow features and LSTM layers model their temporal dependencies, with batch normalisation and dropout layers added to the network. The model was evaluated in binary and multi-class settings on CICIDS2017, UNSW-NB15 and WSN-DS. Their work is the closest to this project's model. The present project uses a comparable architecture but differs in what it asks of it: the input is a window of ten consecutive flows rather than one flow, the evaluation uses a chronological split and a baseline on identical examples, a second, IoT dataset with held-out recordings tests generalisation, and the model is taken to live traffic.

### 2.1.6 Explainable AI for Intrusion Detection

**SHAP and LIME.** Lundberg and Lee [@K16] unified several explanation methods as additive feature attribution methods and showed that Shapley values are the only attribution that satisfies three desirable properties: local accuracy (the attributions sum to the model's output), missingness and consistency. They proposed efficient estimators, among them Kernel SHAP, which is model-agnostic. Ribeiro et al. [@K17] introduced LIME, which explains an individual prediction by fitting a simple interpretable model to the classifier's behaviour in the neighbourhood of that input.

**XAI applied to intrusion detection.** Arreche et al. [@K18] proposed E-XAI, a framework for evaluating black-box explanation methods such as SHAP and LIME for network intrusion detection on several datasets and models, using criteria such as descriptive accuracy, sparsity, stability, efficiency, robustness and completeness. Their work shows that explanations must themselves be evaluated, which motivated the measurements behind the dashboard's choice of explainer (Section 5.3.3). Gaspar et al. [@K19] applied LIME and SHAP to a multi-layer perceptron intrusion detector and studied how useful the explanations are for understanding its decisions. Nascita et al. [@K20] surveyed explainable AI for network traffic classification, traffic prediction and intrusion detection, and Manivannan [@K21] analysed explainable-AI-driven machine-learning techniques for network intrusion detection systems. These surveys agree that explanations are needed for analysts to trust and act on detector output, and that most works use explanations to justify correct predictions rather than to diagnose wrong ones.

**Explainers for specific model types.** Lundberg et al. [@K35] extended SHAP with an exact and fast algorithm for tree ensembles and showed how many local explanations combine into a global understanding of a model; such an explainer would suit the random-forest baseline of this project. For differentiable models, Erion et al. [@K36] introduced expected gradients, which average integrated gradients over a distribution of reference inputs; this is the estimator used in this project's error analysis of the MU-IoT model (Section 3.5.5).

### 2.1.7 Classical Baselines

The random forest of Breiman [@K29] trains many decision trees on bootstrap samples of the data, each split choosing from a random subset of features, and predicts by majority vote. Random forests train quickly, handle imbalanced tabular data well and need little tuning, which makes them a strong baseline for flow-based detection. In this project the same 20 features and the same split are given to a random forest so that the CNN-LSTM is judged against a capable classical model, as Arp et al. [@K28] recommend.

### 2.1.8 Online Detection and Practical Assessment

Most of the works above classify a recorded dataset offline. Mirsky et al. [@K31] designed Kitsune, an online network intrusion detector that learns normal traffic without labels through an ensemble of small autoencoders, processes packets as they arrive and is light enough to run on a network gateway. Kitsune shows that detection on live traffic is practical, although, as an anomaly detector, it reports that traffic is unusual rather than which attack it is.

Two recent studies question how machine-learning detectors are evaluated. Jacobs et al. [@K42] showed that models for network security can reach high accuracy by learning shortcuts that do not carry over to other networks, and used explanations of the models to expose these shortcuts. Apruzzese et al. [@K43] reviewed machine learning for network intrusion detection from the point of view of practical deployment and argued that evaluations should reflect the conditions under which detectors are actually operated. Both studies support the emphasis of this project on baselines, held-out recordings, explanations of errors and measurement on a real network.

## 2.2 Summary of the Literature Survey

Table 2.1 summarises the surveyed works and what each contributes to this project.

::table 2.1 | Summary of the surveyed literature
| Ref. | Work (year) | Method or contribution | Data or scope | Use in this project |
|:---|:---|:---|:---|:---|
| [@K1] | Buczak and Guven (2016) | Survey of ML and data-mining methods for intrusion detection | Broad IDS literature | Background, taxonomy |
| [@K3] | Khraisat et al. (2019) | Survey and taxonomy of IDS, datasets and evasion | Broad IDS literature | Background |
| [@K4] | García-Teodoro et al. (2009) | Survey of anomaly-based NIDS | Anomaly detection | Background, open problems |
| [@K2] | Sommer and Paxson (2010) | Why ML struggles in operational NIDS | Operational networks | Evaluation on real traffic |
| [@K28] | Arp et al. (2022) | Ten pitfalls of ML in security | Security ML papers | Split design, baseline, metrics |
| [@K15] | Tavallaee et al. (2009) | Analysis of KDD Cup 99, NSL-KDD | KDD Cup 99 | Benchmark flaws |
| [@K10] | Moustafa and Slay (2015) | UNSW-NB15 dataset | Cyber-range traffic | Dataset context |
| [@K9] | Sharafaldin et al. (2018) | CICIDS2017 dataset | Five-day testbed capture | Main benchmark |
| [@K27] | Lashkari et al. (2017) | CICFlowMeter time-based flow features | Tor traffic | Feature definitions |
| [@K26] | Engelen et al. (2021) | Errors in CICIDS2017 and CICFlowMeter | CICIDS2017 | Extractor reproduces artefacts |
| [@K14] | Ring et al. (2019) | Survey of NIDS datasets | 34 datasets compared | Use of two datasets |
| [@K11] | Meidan et al. (2018) | Deep autoencoders for IoT botnets | N-BaIoT | IoT context |
| [@K12] | Koroniotis et al. (2019) | Bot-IoT dataset | IoT testbed | IoT context |
| [@K13] | Alsaedi et al. (2020) | TON_IoT telemetry dataset | IoT and IIoT | IoT context |
| [@K30] | Clinton and Hoque (2024) | MU-IoT dataset | IoT testbed, Manipur University | Second, Indian dataset |
| [@K24] | Diro and Chilamkurti (2018) | Distributed deep learning for IoT attacks | IoT | IoT deep learning |
| [@K23] | LeCun et al. (1998) | Convolutional networks | Document recognition | CNN component |
| [@K22] | Hochreiter and Schmidhuber (1997) | Long short-term memory | Sequence learning | LSTM component |
| [@K5] | Shone et al. (2018) | Non-symmetric deep autoencoder with RF | KDD Cup 99, NSL-KDD | Deep IDS context |
| [@K6] | Yin et al. (2017) | Recurrent neural network IDS | NSL-KDD | Sequence models |
| [@K7] | Vinayakumar et al. (2019) | Deep networks vs classical ML | Several incl. CICIDS2017 | Deep IDS context |
| [@K25] | Ferrag et al. (2020) | Survey and comparison of deep IDS | 35 datasets surveyed | Deep IDS context |
| [@K8] | Halbouni et al. (2022) | Hybrid CNN-LSTM IDS | CICIDS2017, UNSW-NB15, WSN-DS | Closest prior model |
| [@K29] | Breiman (2001) | Random forests | General | Baseline model |
| [@K16] | Lundberg and Lee (2017) | SHAP, Kernel SHAP | General | Explanations |
| [@K17] | Ribeiro et al. (2016) | LIME | General | Alternative explainer |
| [@K18] | Arreche et al. (2024) | Evaluating XAI for NIDS (E-XAI) | Three NIDS datasets | Explainer evaluation |
| [@K19] | Gaspar et al. (2024) | LIME and SHAP on an MLP IDS | IDS | XAI for IDS |
| [@K20] | Nascita et al. (2025) | Survey of XAI for traffic analysis and IDS | Traffic, IDS | XAI context |
| [@K21] | Manivannan (2026) | Analysis of XAI-driven ML for NIDS | NIDS | XAI context |
| [@K34] | Liu and Lang (2019) | Survey of ML and DL methods for IDS by data source | Packets, flows, sessions, logs | Places this work among flow-based methods |
| [@K37] | Ahmad et al. (2021) | Systematic study of ML and DL NIDS | Several NIDS datasets | Open problems |
| [@K40] | Rosay et al. (2022) | Analysis of CIC-IDS2017 | CIC-IDS2017 | Dataset problems |
| [@K41] | Lanvin et al. (2023) | Errors in CICIDS2017 and their effect | CICIDS2017 | Dataset problems |
| [@K38] | Sarhan et al. (2022) | Standard feature set for NIDS datasets | Several NIDS datasets | Cross-dataset comparison |
| [@K39] | Javaid et al. (2016) | Self-taught learning (sparse autoencoder) | NSL-KDD | Deep IDS context |
| [@K32] | Kim et al. (2016) | LSTM network IDS | KDD Cup 99 | Sequence models |
| [@K33] | Wang et al. (2018) | HAST-IDS: CNN spatial and LSTM temporal features | DARPA 1998, ISCX 2012 | Hybrid CNN-LSTM |
| [@K35] | Lundberg et al. (2020) | Exact SHAP for tree models | General | Explainer for trees |
| [@K36] | Erion et al. (2021) | Expected gradients | General | Error-analysis method |
| [@K31] | Mirsky et al. (2018) | Kitsune: online ensemble of autoencoders | Live network traffic | Online detection |
| [@K42] | Jacobs et al. (2022) | Shortcut learning in ML for network security | Several network tasks | Generalisation |
| [@K43] | Apruzzese et al. (2023) | Pragmatic assessment of ML for NIDS | NIDS literature | Evaluation practice |

## 2.3 Research Gap

The surveyed literature establishes that machine-learning and deep-learning models can detect intrusions in benchmark datasets, that hybrid CNN-LSTM architectures are a reasonable choice for flow data, and that explanation methods such as SHAP can make their decisions interpretable. It also shows four gaps that this project addresses.

1. **Evaluation.** Most deep-learning studies report accuracy on random splits of one dataset. Few use a chronological split, compare against a classical model on identical examples, or test on whole recordings never seen in training, although the pitfalls this causes are well documented [@K2, K28].
2. **Explanations of errors.** Explainable AI for intrusion detection mostly explains correct predictions. Using explanations to diagnose why a model fails, and to decide which classes should not be trusted, is rarely done.
3. **From detection to safe prevention.** Few works connect a detector's measured reliability to the decision to act automatically, or describe the safety limits that automatic blocking on a real network requires.
4. **From benchmark to live traffic.** Models trained on CICIDS2017 are rarely run on live traffic, and when they are, the flow features are not checked against the tool that produced the training data, even though the dataset's own flow construction is known to contain artefacts [@K26].

This project builds and measures each of these steps. Table 2.2 compares it with the closest works on the points that matter here; "not reported" means that the point is not part of the published work, not that the work is weaker.

::table 2.2 | Comparison of this project with the closest related works
| Aspect | Halbouni [@K8] | Vinayakumar [@K7] | Kitsune [@K31] | E-XAI [@K18] | This project |
|:---|:---|:---|:---|:---|:---|
| Model | CNN-LSTM | Deep neural networks | Ensemble of autoencoders | Several, explained | CNN-LSTM over 10-flow windows |
| Datasets | CICIDS2017, UNSW-NB15, WSN-DS | Several incl. CICIDS2017 | Own network captures | Three NIDS datasets | CICIDS2017 and MU-IoT (India) |
| Classical baseline | Not reported | Classical models compared | Not reported | Not applicable | Random forest on identical examples |
| Unseen recordings held out | Not reported | Not reported | Not reported | Not applicable | Four MU-IoT recordings |
| Explanations | Not reported | Not reported | Not reported | SHAP and LIME evaluated | SHAP per prediction and for errors |
| Automatic prevention | Not reported | Not reported | Not reported | Not reported | Firewall blocking with safety limits |
| Live traffic | Not reported | Not reported | Online packet stream | Not reported | Live capture with validated extractor |