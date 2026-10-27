# - | Conclusion and Future Enhancements

## Conclusion

This project built a hybrid CNN-LSTM intrusion detection and prevention system and took it from benchmark data to live traffic on a real network. The model classifies windows of consecutive network flows into benign traffic and fourteen attack classes, the dashboard explains every prediction with SHAP, and a prevention layer blocks attacking devices through the host firewall.

Evaluated with leakage-controlled splits against a random forest on identical examples, the CNN-LSTM turned out to have specific strengths: the forest is better on CICIDS2017 (macro F1 0.780 against 0.586), while the CNN-LSTM is clearly better on the Indian MU-IoT dataset (0.676 against 0.404 on recordings never seen), because MU-IoT flow records are ambiguous on their own and sequences resolve them. SHAP separated the model's main errors on unseen IoT recordings into three different causes, one of which no confidence threshold can fix.

The prevention policy connects these measurements to action: thresholds follow each class's measured F1, unreliable classes are locked to human review, and on the CICIDS2017 test set the policy handles 96.6% of attack windows automatically while acting on 0.33% of benign windows. Execution is bounded by a kill switch, an allow-list, one rule per device and revocation that always works, verified by 35 automated tests, a mutation check (19 of 19 breakages caught) and an end-to-end check on the real firewall.

A packet-to-flow extractor reproduces the CICFlowMeter-V3 features on 99.8% of flows of the original CICIDS2017 capture, so live traffic and Wireshark captures are analysed with the training features. In a live run on a shared Wi-Fi network, a real port scan was detected about two seconds after its first probes and blocked automatically, while another user's device, flagged wrongly with high confidence, was refused by the safety checks.

The project's conclusion is therefore not that a deep model is always better, but that a deep model can be deployed responsibly when its evaluation is honest, its errors are explained, and its authority to act is limited to what its measured reliability supports.

## Future Enhancements

1. **Retraining on present-day traffic.** Fine-tuning the model on current benign traffic, including IPv6 and QUIC, would address the main source of false alarms found in the live tests.
2. **Further live attacks on an isolated laboratory network.** Floods, brute-force and web attacks need victim servers and several attacking machines; an isolated laboratory network would allow every class to be tested live, safely.
3. **A separate calibration set** for the prevention thresholds, so that the policy can be validated independently of the test set it was derived from.
4. **Repeated training runs** with different random seeds, to report the variance of every score.
5. **Recovering the web-attack signal.** The random forest detects web brute force from single flows (F1 0.69) where the CNN-LSTM does not; a model that combines the current flow's features with the window's sequence could keep both strengths.
6. **The MU-IoT model in the dashboard,** with its own extractor for the MU-IoT features, so that IoT traffic can be analysed live as well.
7. **True rate limiting** through Windows quality-of-service policies instead of a temporary full block.
