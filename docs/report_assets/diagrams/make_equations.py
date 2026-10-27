"""Renders the report's equations as 300 dpi PNGs (matplotlib mathtext, STIX = Times-like).

    python docs/report_assets/diagrams/make_equations.py

Writes docs/report_assets/equations/<name>.png; build_report.py places them
with their numbers. Each formula is the one the code uses (named per entry).
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"mathtext.fontset": "stix", "font.family": "STIXGeneral", "savefig.dpi": 300})
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "equations")

EQUATIONS = {
    # evaluation metrics (model/evaluate_model.py, sklearn.metrics)
    "precision": r"P_k = \frac{TP_k}{TP_k + FP_k}, \qquad R_k = \frac{TP_k}{TP_k + FN_k}",
    "f1": r"F1_k = \frac{2\,P_k\,R_k}{P_k + R_k}",
    "macro_weighted": r"F1_{macro} = \frac{1}{K}\sum_{k=1}^{K} F1_k, \qquad F1_{weighted} = \sum_{k=1}^{K}\frac{N_k}{N}\,F1_k",
    "accuracy": r"\mathrm{Accuracy} = \frac{1}{N}\sum_{n=1}^{N}\mathbf{1}\left[\hat{y}_n = y_n\right]",
    # flow features (model/flow_features.py, CICFlowMeter-V3 definitions)
    "pl_mean": r"\bar{L} = \frac{1}{n+1}\left(L_1 + \sum_{i=1}^{n} L_i\right)",
    "pl_std": r"s_L = \sqrt{\frac{1}{n}\left[(L_1-\bar{L})^2 + \sum_{i=1}^{n}(L_i - \bar{L})^2\right]}",
    "avg_size": r"\mathrm{AvgPacketSize} = \frac{1}{n}\left(L_1 + \sum_{i=1}^{n} L_i\right)",
    "iat": r"\mathrm{IAT}_i = t_{i+1} - t_i, \qquad \mathrm{FlowIATMax} = \max_i\ \mathrm{IAT}_i",
    # windows and scaling (model/MODEL_INTERFACE.md)
    "scaler": r"z_{i,j} = \frac{x_{i,j} - \mu_j}{\sigma_j}",
    "window": r"\mathbf{X}_t = \left[\,\mathbf{z}_{t-9},\ \mathbf{z}_{t-8},\ \ldots,\ \mathbf{z}_{t}\,\right] \in \mathbb{R}^{10 \times 20}",
    # CNN-LSTM (model/cnn_lstm_architecture.py)
    "conv": r"h_{t,k} = \mathrm{ReLU}\left(b_k + \sum_{m=0}^{2}\ \sum_{c=1}^{C} w_{k,m,c}\ x_{t+m,\,c}\right), \qquad \mathrm{ReLU}(a) = \max(0, a)",
    "bn": r"\hat{h} = \gamma\,\frac{h - \mu_B}{\sqrt{\sigma_B^2 + \epsilon}} + \beta",
    "pool": r"p_{t,k} = \max\left(h_{2t,\,k},\ h_{2t+1,\,k}\right)",
    "lstm_gates": r"f_t = \sigma(W_f x_t + U_f h_{t-1} + b_f), \quad i_t = \sigma(W_i x_t + U_i h_{t-1} + b_i), \quad o_t = \sigma(W_o x_t + U_o h_{t-1} + b_o)",
    "lstm_cell": r"\tilde{c}_t = \tanh(W_c x_t + U_c h_{t-1} + b_c), \qquad c_t = f_t \odot c_{t-1} + i_t \odot \tilde{c}_t",
    "lstm_out": r"h_t = o_t \odot \tanh(c_t)",
    "softmax": r"\hat{y}_k = \frac{e^{z_k}}{\sum_{j=1}^{K} e^{z_j}}, \qquad c = \max_k\ \hat{y}_k",
    "loss": r"\mathcal{L} = -\frac{1}{N}\sum_{n=1}^{N} w_{y_n}\,\log \hat{y}_{n,\,y_n}",
    "class_weights": r"w_k = \sqrt{\frac{N}{K\,N_k}}",
    # SHAP (backend/shap_service.py; model/explain_mu_iot.py)
    "shapley": r"\phi_i = \sum_{S \subseteq F \setminus \{i\}} \frac{|S|!\,(|F| - |S| - 1)!}{|F|!}\left[f(S \cup \{i\}) - f(S)\right]",
    "additivity": r"f(\mathbf{x}) = \phi_0 + \sum_{i=1}^{M} \phi_i",
    "kernel": r"\pi(\mathbf{z}) = \frac{M - 1}{\binom{M}{|\mathbf{z}|}\ |\mathbf{z}|\ (M - |\mathbf{z}|)}",
    "expected_gradients": r"\phi_i = \mathbb{E}_{\mathbf{x}' \sim D,\ \alpha \sim U(0,1)}\left[(x_i - x'_i)\ \frac{\partial f\left(\mathbf{x}' + \alpha(\mathbf{x} - \mathbf{x}')\right)}{\partial x_i}\right]",
    "cosine": r"\cos(\mathbf{a}, \mathbf{b}) = \frac{\mathbf{a} \cdot \mathbf{b}}{\Vert\mathbf{a}\Vert\ \Vert\mathbf{b}\Vert}",
    # prevention policy (model/class_action_mapping.py)
    "threshold": r"\theta(F1) = \theta_j + \frac{F1 - F1_j}{F1_{j+1} - F1_j}\,(\theta_{j+1} - \theta_j), \qquad F1_j \leq F1 \leq F1_{j+1}",
    "decision": r"\mathrm{auto}(\hat{y}, c) = \mathbf{1}[\hat{y} \neq \mathrm{benign}]\cdot\mathbf{1}[\hat{y} \notin \mathcal{R}]\cdot\mathbf{1}[c \geq \theta_{\hat{y}}]",
    # target selection (model/target_selection.py)
    "target": r"a^{*} = \arg\max_{a \in A}\ \left|\{\,f \in W : \mathrm{src}(f) = a\,\}\right|",
}


def render(name, tex):
    fig = plt.figure(figsize=(0.01, 0.01))
    tex = tex.replace(r"\frac{", r"\dfrac{")         # display-size fractions, as in a typeset equation
    fig.text(0, 0, f"${tex}$", fontsize=12)
    fig.savefig(os.path.join(OUT, name + ".png"), bbox_inches="tight", pad_inches=0.02, transparent=False,
                facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, tex in EQUATIONS.items():
        render(name, tex)
    print(f"rendered {len(EQUATIONS)} equations to {os.path.abspath(OUT)}")
