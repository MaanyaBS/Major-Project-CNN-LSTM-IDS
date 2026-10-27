# Literature Survey: Explainable Hybrid CNN–LSTM Intrusion Detection

**Project context:** ThreatLens — an intrusion-detection workflow combining a hybrid CNN–LSTM classifier, SHAP-based explanations, network-flow feature extraction, and a dashboard for reviewing predictions and response recommendations.

**Status:** Working literature-survey draft. Verify the full text and final bibliographic metadata of every source before submission. Do not copy performance numbers from papers unless they have been checked in the original paper.

## 1. Scope and review approach

This survey groups relevant research into five themes: (1) intrusion-detection foundations and machine learning, (2) deep-learning and CNN–LSTM methods, (3) datasets and IoT security, (4) explainable AI, especially SHAP and LIME, and (5) evaluation and deployment considerations. The sources include original research papers, dataset papers, and surveys. These categories are complementary but should not be treated as interchangeable: a dataset paper documents a benchmark, a primary study proposes or evaluates a method, and a survey synthesizes prior work.

## 2. Thematic review

### 2.1 Machine learning and deep learning for intrusion detection

Network intrusion detection has traditionally used signatures, statistical analysis, and machine-learning classifiers to identify malicious activity. Surveys such as Buczak and Guven (2016) and Khraisat et al. (2019) describe the range of approaches and recurring challenges, including changing attack behaviour, false alarms, feature engineering, and evaluation quality. Sommer and Paxson (2010) caution that machine-learning-based detection must be evaluated in the context of real operational networks rather than assuming that benchmark results automatically transfer to deployment.

Deep-learning research investigates whether neural networks can learn useful representations from network traffic. Shone et al. (2018) proposed a non-symmetric deep autoencoder approach for network intrusion detection, while Yin et al. (2017) investigated recurrent neural networks. Vinayakumar et al. (2019) studied deep-learning approaches for intelligent intrusion detection. These works provide a basis for comparing learned representations and sequence modelling with conventional machine-learning methods.

### 2.2 CNN–LSTM and sequence-based detection

CNNs can learn local patterns from structured input features, whereas LSTMs are designed to model dependencies across sequences. The CNN–LSTM study by Kim et al. (2022) directly combines these components for intrusion detection and evaluates binary and multiclass settings on several datasets. It is therefore especially relevant to the architecture explored in ThreatLens.

A hybrid architecture alone does not guarantee robust detection. Its performance depends on the feature representation, sequence construction, split strategy, label distribution, and evaluation procedure. For imbalanced multiclass data, accuracy should be reported alongside macro-F1, weighted-F1, per-class precision/recall, and a confusion matrix. A high overall accuracy can coexist with weak performance on rare classes.

### 2.3 Datasets and generalization

Sharafaldin et al. (2018) introduced CICIDS2017 and documented its traffic generation and labelled flow features. Moustafa and Slay (2015) introduced UNSW-NB15 as a benchmark containing a range of normal and malicious activities. Meidan et al. (2018) presented N-BaIoT for network-based IoT botnet detection. Koroniotis et al. (2019) introduced Bot-IoT, and Moustafa et al. (2020) presented the ToN-IoT telemetry dataset for IoT/IIoT security research.

These datasets support repeatable comparisons, but differences in collection environment, attack types, feature engineering, and label distribution affect how results should be interpreted. Training and testing on a single prepared dataset is not the same as validating on independently captured traffic. A live-capture integration test without independent ground-truth labels can demonstrate that a pipeline runs, but cannot establish an accurate detection rate.

### 2.4 Explainable AI and SHAP

Lundberg and Lee (2017) introduced SHAP, a framework that assigns feature-attribution values to individual model predictions. Ribeiro et al. (2016) introduced LIME, which explains a prediction using a locally interpretable approximation. Both methods are relevant when a security analyst needs more than a predicted attack label.

Recent work has examined explainability specifically for network intrusion detection. The E-XAI framework evaluates black-box explanation methods using criteria such as descriptive accuracy, sparsity, stability, efficiency, robustness, and completeness. Other work has applied SHAP and LIME to intrusion-detection classifiers. These studies suggest that explanation quality itself should be evaluated rather than assumed.

Feature attributions are not proof that an attack occurred, that a feature caused the attack, or that a classifier is correct. Prediction quality and explanation quality are separate questions. For ThreatLens, SHAP is intended to help interpret model outputs and support analyst review.

### 2.5 Feature selection, deployment, and practical evaluation

Network-flow datasets can contain many attributes, including redundant or correlated features. Feature-selection research investigates whether a smaller set of attributes can preserve useful predictive information and reduce computation. This is relevant to data preparation, model input consistency, and the performance of an end-to-end inference pipeline.

Deployment also introduces requirements that are not captured by a static dataset score: traffic capture, protocol support, flow construction, preprocessing consistency, inference latency, explanation overhead, logging, and the response policy. A dashboard can make results easier to inspect, but it should not be described as a production prevention system unless actual blocking has been implemented and validated.

## 3. Literature comparison matrix

The following matrix is a reading and comparison guide. “Relevance” describes how a source can inform ThreatLens; it is not a claim that the source evaluated ThreatLens. Check each paper before recording exact findings or limitations.

| No. | Source | Type / method focus | Dataset or scope | Relevance to ThreatLens |
|---:|---|---|---|---|
| 1 | Buczak & Guven (2016) | Survey of data-mining and machine-learning methods for cyber intrusion detection | Broad IDS literature | Background on conventional ML methods and evaluation issues |
| 2 | Sommer & Paxson (2010) | Critical analysis of ML for network intrusion detection | Operational network detection | Motivation for careful claims about real-world generalization |
| 3 | Khraisat et al. (2019) | Survey of intrusion-detection systems | IDS methods and challenges | Background for detection approaches and common limitations |
| 4 | García-Teodoro et al. (2009) | Survey of anomaly-based network IDS | Anomaly detection | Historical foundation for anomaly-based approaches |
| 5 | Shone et al. (2018) | Non-symmetric deep autoencoder approach | Network intrusion detection | Alternative deep-learning architecture to compare with CNN–LSTM |
| 6 | Yin et al. (2017) | Recurrent neural network | Intrusion detection | Supports discussion of sequence modelling |
| 7 | Vinayakumar et al. (2019) | Deep-learning approaches for intelligent IDS | Multiple IDS settings/datasets | Broad comparison of deep models |
| 8 | Kim et al. (2022) | Hybrid CNN–LSTM | CICIDS2017, UNSW-NB15, WSN-DS | Directly related hybrid architecture |
| 9 | Sharafaldin et al. (2018) | Dataset design and traffic characterization | CICIDS2017 | Primary source for the project’s benchmark dataset |
| 10 | Moustafa & Slay (2015) | Dataset introduction | UNSW-NB15 | Alternative benchmark and generalization context |
| 11 | Meidan et al. (2018) | Network-based IoT botnet detection using deep autoencoders | N-BaIoT | IoT-focused detection comparison |
| 12 | Koroniotis et al. (2019) | Dataset design for IoT botnet traffic | Bot-IoT | IoT attack-data context |
| 13 | Moustafa et al. (2020) | IoT/IIoT telemetry dataset | ToN-IoT | Additional IoT/IIoT evaluation context |
| 14 | Ring et al. (2019) | Survey of network-based IDS datasets | Network IDS datasets | Dataset selection and reproducibility |
| 15 | Tavallaee et al. (2009) | Statistical analysis of KDD Cup 99 | KDD Cup 99 | Historical example of benchmark-data limitations |
| 16 | Lundberg & Lee (2017) | SHAP framework | Model prediction explanations | Theoretical basis of SHAP used by ThreatLens |
| 17 | Ribeiro et al. (2016) | LIME local explanation method | Classifier-agnostic explanations | Useful contrast with SHAP |
| 18 | “E-XAI: Evaluating Black-Box Explainable AI Frameworks for Network Intrusion Detection” (2024) | Evaluation framework for SHAP/LIME explanations | Three network intrusion datasets; multiple models | Shows why explanation quality needs its own evaluation |
| 19 | “Explainable AI for Intrusion Detection Systems: LIME and SHAP Applicability on Multi-Layer Perceptron” (2024) | Comparison/application of LIME and SHAP | IDS classification | Directly relevant XAI-for-IDS study |
| 20 | “A Survey on Explainable AI for Internet Traffic Classification and Prediction, and Intrusion Detection” (published in IEEE Communications Surveys & Tutorials, 2025 issue) | Survey of XAI for network traffic analysis | Traffic classification, prediction, IDS | Closely aligned survey of explainability needs |
| 21 | “A Comprehensive Analysis of Explainable AI-Driven Machine Learning Techniques for Network Intrusion Detection Systems” (2026) | Recent XAI-IDS survey | XAI-enabled IDS methods | Recent discussion of evaluation, deployment, and research gaps; verify publication status at submission |
| 22 | Hochreiter & Schmidhuber (1997) | Original LSTM architecture paper | Sequence learning | Foundational source for the LSTM component |
| 23 | LeCun et al. (1998) | Gradient-based learning applied to document recognition / CNNs | Convolutional neural networks | Foundational context for CNN feature learning; not an IDS paper |
| 24 | Diro & Chilamkurti (2018) | Distributed deep-learning-based attack detection | IoT networks | Supports IoT IDS discussion |
| 25 | Ferrag et al. (2020) | Deep-learning cybersecurity IDS survey/comparative study | Deep-learning methods and datasets | Broad review of models and benchmarks |

## 4. Research gap and project motivation

Prior work establishes the value of machine learning and deep learning for intrusion detection, explores CNN–LSTM architectures, introduces widely used benchmark datasets, and develops explanation methods such as SHAP and LIME. However, a research prototype still needs to show how classification, explanation, traffic feature extraction, dashboard presentation, and response recommendations fit together in one workflow.

ThreatLens focuses on this integration: a hybrid CNN–LSTM model produces traffic-class predictions, SHAP provides feature-attribution explanations, and the dashboard presents predictions and recommended responses. The current response component is recommendation-based/simulated; it should not be described as blocking live traffic. Live-capture experiments without reliable ground-truth labels should be presented as exploratory integration tests, not as independently measured detection accuracy.

## 5. Suggested evaluation dimensions

For a defensible study, report the following only when supported by actual experiment outputs:

- Accuracy, macro-F1, weighted-F1, per-class precision and recall, and confusion matrix.
- Dataset source, label distribution, preprocessing, feature-selection method, and split strategy.
- Whether sequence windows or sessions can overlap across train and test splits.
- SHAP configuration, background data, explanation examples, runtime, and any explanation-quality checks performed.
- Live-capture source and protocol coverage, number of flows/windows processed, truncation, ground-truth availability, and the distinction between recommendations and executed prevention.
- Limitations, including dataset shift and the inability to infer true live detection accuracy without ground truth.

## 6. Notes before submission

1. Read the original paper or at least its abstract, methods, dataset, results, and limitations before making a paper-specific claim.
2. Confirm exact author names, title, year, venue, volume/pages, and DOI from the publisher or proceedings.
3. Cite sources in the paper body using IEEE numeric citations, such as [1], [2], and ensure each citation maps to a reference entry.
4. Do not invent metrics or copy results from secondary summaries without checking the primary source.
5. Replace this draft matrix with concise, verified summaries after the papers have been reviewed.
