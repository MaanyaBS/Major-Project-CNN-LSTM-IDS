"""Draws the report's block, architecture, use case, data flow, sequence and flow diagrams.

    python docs/report_assets/diagrams/make_diagrams.py [name ...]

Writes PNGs (300 dpi) to docs/report_assets/figures/. With no names, every
figure is drawn. The facts in each figure come from the code named in the
caption (backend/app.py, backend/live_capture.py, model/*.py).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from draw import AMBER, BLUE, GREY, NAVY, PALE, ROSE, TEAL, WHITE, Canvas, sequence  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")


def fig_3_1_block():
    c = Canvas(3.7)
    c.text(1.5, 53.5, "Offline development", fs=7.5, ha="left", bold=True, color=NAVY)
    row1 = ["CICIDS2017 and\nMU-IoT datasets", "Cleaning, 20-feature\nselection,\nchronological split",
            "Windows of flows\nand scaling", "CNN-LSTM training\n(class weights,\nearly stopping)",
            "Evaluation against\nrandom forest,\nheld-out recordings"]
    xs = [1.5 + i * 19.7 for i in range(5)]
    for x, t in zip(xs, row1):
        c.box(x, 39, 17, 12, t, fs=6.6)
    for a, b in zip(xs, xs[1:]):
        c.arrow((a + 17, 45), (b, 45))
    c.text(1.5, 33, "Online operation", fs=7.5, ha="left", bold=True, color=NAVY)
    row2 = ["Live interface\n(Npcap) or\nWireshark capture", "Packet-to-flow\nextractor\n(20 features)",
            "CNN-LSTM\ninference", "Prevention policy\nand target\nselection",
            "Windows Firewall\nrule (block, drop,\nrate-limit)"]
    for i, (x, t) in enumerate(zip(xs, row2)):
        c.box(x, 17, 17, 12, t, fc=TEAL if i < 4 else AMBER, fs=6.6)
    for a, b in zip(xs, xs[1:]):
        c.arrow((a + 17, 23), (b, 23))
    c.poly([(xs[3] + 8.5, 39), (xs[3] + 8.5, 33), (xs[2] + 8.5, 33), (xs[2] + 8.5, 29)], "trained model\nand scaler",
           lab=(xs[2] + 19, 33), fs=6)
    c.box(xs[2], 2, xs[4] + 17 - xs[2], 9.2,
          "ThreatLens AI dashboard: verdicts, SHAP explanations,\nblocked devices and revoke", fc=PALE, fs=6.8,
          bold=True)
    for i in (2, 3, 4):
        c.arrow((xs[i] + 8.5, 17), (xs[i] + 8.5, 11.2))
    c.save(os.path.join(OUT, "fig_3_1_block_diagram.png"))


def fig_4_1_architecture():
    c = Canvas(6.5)
    t = c.top
    c.box(2, t - 17, 96, 15.5, fc=PALE)
    c.text(4, t - 4, "PRESENTATION LAYER  |  ThreatLens AI dashboard (React, TypeScript)", fs=7, ha="left", bold=True,
           color=NAVY)
    for i, s in enumerate(["Batch analysis\n(CSV, pcap upload)", "Live feed\n(replay, live capture)",
                           "SHAP explanation\n(per window)", "Blocked devices\nand revoke"]):
        c.box(4.5 + i * 23.2, t - 15, 21, 8, s, fc=BLUE, fs=6.6)
    c.arrow((50, t - 17), (50, t - 21.5), both=True, label="REST / JSON", lab=(61, t - 19.3))

    top2, bot2 = t - 21.5, 27
    c.box(2, bot2, 96, top2 - bot2, fc=PALE)
    c.text(4, top2 - 2.7, "APPLICATION LAYER  |  Flask backend (Python 3.13): app.py, live_capture.py", fs=7,
           ha="left", bold=True, color=NAVY)
    ys = top2 - 25
    for i, s in enumerate(["Live interface\n(Npcap)", "Wireshark\n.pcap / .pcapng", "Flow CSV\n(20 features)"]):
        c.box(4, ys + 14.5 - i * 7.6, 15, 6, s, fc=WHITE, fs=6.4)
    c.box(23, ys + 6, 16, 15, "Packet-to-flow\nextractor\n\nflow_features.py\nIPv4 + IPv6\nCICFlowMeter-V3\nrules",
          fc=TEAL, fs=6.4)
    c.box(42, ys, 15, 21, "Window builder\n\n10 flows per\nwindow, stride 1\n\nStandardScaler", fc=TEAL, fs=6.4)
    c.box(60, ys, 15, 21, "CNN-LSTM\nclassifier\n\n15 classes\n(BENIGN + 14\nattacks)", fc=TEAL, fs=6.4)
    c.box(78, ys, 17.5, 21, "Prevention policy\n\nclass_action_\nmapping.py:\nthresholds,\nreview locks", fc=TEAL,
          fs=6.4)
    for a, b in ((19, 23), (39, 42), (57, 60), (75, 78)):
        c.arrow((a, ys + 14), (b, ys + 14))
    c.poly([(19, ys + 3.2), (41.9, ys + 3.2)], "CSV skips extraction", lab=(31, ys + 1.0), fs=5.8)

    y2 = bot2 + 2.5
    c.box(42, y2, 15, 11.5, "SHAP service\n\nKernelExplainer\n20 grouped features", fc=BLUE, fs=6.4)
    c.arrow((55, y2 + 11.5), (62, ys), both=True)
    c.arrow((49.5, y2 + 11.5), (49.5, ys), "window", lab=(51.5, ys - 2.2), fs=5.8)
    c.box(60, y2, 15, 11.5, "Prevention engine\n\nprevention_executor.py\nsafety checks", fc=AMBER, fs=6.2)
    c.box(78, y2, 17.5, 11.5, "Target selection\n\nprivate IPv4 source\nthat sent to this host", fc=TEAL,
          fs=6.2)
    c.arrow((86.7, ys), (86.7, y2 + 11.5))
    c.arrow((78, y2 + 5.7), (75, y2 + 5.7))

    c.box(2, 2, 96, 21.5, fc=WHITE, ls="--", ec=GREY)
    c.text(4, 20.5, "HOST AND DATA LAYER", fs=7, ha="left", bold=True, color=NAVY)
    c.box(5, 5.5, 29, 11, "Trained artifacts\ncnn_lstm_best_v2.keras, scaler_v2.pkl,\nlabel_mapping_v2.json,\n"
          "SHAP background (real traffic)", fc=PALE, fs=6.2)
    c.box(37, 5.5, 26, 11, "Prevention log (JSONL)\nand rule registry\nIDS_DEMO_block_ip_<ip>_in / _out", fc=PALE,
          fs=6.2)
    c.box(66, 5.5, 29, 11, "Windows Firewall\nnetsh advfirewall rules\n(kill switch, demo targets)", fc=AMBER,
          fs=6.4)
    c.arrow((67.5, y2), (67.5, 16.5), "add / delete rule", lab=(77, 25.2), fs=5.8)
    c.arrow((63, 11), (66, 11), both=True)
    c.save(os.path.join(OUT, "fig_4_1_system_architecture.png"))


def fig_4_2_use_case():
    c = Canvas(6.3)
    t = c.top
    c.box(19, 1.5, 63, t - 3, fc=WHITE, ec=NAVY, rounding=1.4)
    c.text(50.5, t - 3.6, "ThreatLens AI: CNN-LSTM IDS / IPS-lite", fs=7.5, bold=True, color=NAVY)
    analyst_uc = ["UC1  Start or stop live capture", "UC2  Upload a Wireshark capture", "UC3  Upload a flow CSV",
                  "UC4  View detection log and\nconfidence stream", "UC5  View batch verdict\nand statistics",
                  "UC6  Request SHAP explanation", "UC7  Review alerts held\nfor human review",
                  "UC8  View blocked devices", "UC9  Revoke a firewall block", "UC10  Export report"]
    ys = [t - 11 - i * 8.0 for i in range(10)]
    for y, s in zip(ys, analyst_uc):
        c.ellipse(37, y, 31, 6.6, s, fs=6.4, fc=BLUE)
    c.actor(8, t / 2 - 3, "Security analyst")
    for y in ys:
        c.arrow((13, t / 2 + 2), (21.6, y), color=GREY, lw=0.6)
    sys_uc = [("UC11  Extract flows\nfrom packets", t - 15), ("UC12  Classify windows\n(CNN-LSTM)", t - 31),
              ("UC13  Apply prevention\npolicy", t - 47), ("UC14  Add or remove\nfirewall rule", t - 63)]
    for s, y in sys_uc:
        c.ellipse(68, y, 22, 8.4, s, fs=6.3, fc=TEAL)
    for (a, ya), (b, yb) in zip(sys_uc, sys_uc[1:]):
        c.arrow((68, ya - 4.2), (68, yb + 4.2), "«include»", ls="--", lab=(75.5, (ya + yb) / 2), fs=5.8)
    c.arrow((52, ys[0] - 0.6), (59, sys_uc[0][1] + 2.2), ls="--", color=GREY, lw=0.6)
    c.arrow((52, ys[1] + 0.4), (58.4, sys_uc[0][1] - 1.6), ls="--", color=GREY, lw=0.6)
    c.arrow((51, ys[2] - 0.8), (58.8, sys_uc[1][1] + 1.0), ls="--", color=GREY, lw=0.6)
    c.actor(91, t - 28, "Network\ntraffic source")
    c.arrow((87.5, t - 25), (79, sys_uc[0][1] - 1), color=GREY, lw=0.6)
    c.box(85, 14.5, 13.5, 9, "Windows\nFirewall", fc=AMBER, fs=6.8, bold=True)
    c.text(91.7, 26.3, "«system»", fs=6, italic=True, color=GREY)
    c.arrow((85, 19), (79, sys_uc[3][1] - 1.2), color=GREY, lw=0.6)
    c.arrow((85, 17), (52.4, ys[8] + 0.4), color=GREY, lw=0.6)
    c.save(os.path.join(OUT, "fig_4_2_use_case.png"))


def fig_4_3a_dfd0():
    c = Canvas(3.7)
    c.box(2, 36, 22, 12, "Network interface\n(live traffic)", fc=WHITE, fs=7)
    c.box(2, 6, 22, 12, "Wireshark capture\nor flow CSV file", fc=WHITE, fs=7)
    c.box(76, 36, 22, 12, "Security analyst", fc=WHITE, fs=7)
    c.box(76, 6, 22, 12, "Windows Firewall", fc=WHITE, fs=7)
    c.circle(50, 27, 14, "0\nThreatLens\nIDS / IPS", fs=7.5)
    c.arrow((24, 44), (40.5, 33.5), "live packets", lab=(25, 47), fs=6.3, ha="left")
    c.arrow((24, 12), (40.5, 20.5), "capture file (.pcap,\n.pcapng) or CSV", lab=(25, 7.4), fs=6.3, ha="left")
    c.arrow((76, 45), (59.3, 37.5), "start / stop, upload,\nexplain, revoke requests", lab=(75, 50.5), fs=6.3, ha="right")
    c.arrow((61.8, 34.5), (76, 40), "verdicts, SHAP values,\nblocked devices", lab=(75, 31), fs=6.3, ha="right")
    c.arrow((61.8, 19.5), (76, 14), "block / unblock rules", lab=(75, 21.6), fs=6.3, ha="right")
    c.arrow((76, 9), (59.3, 16.5), "rule status", lab=(75, 5.4), fs=6.3, ha="right")
    c.save(os.path.join(OUT, "fig_4_3a_dfd_level0.png"))


def fig_4_3b_dfd1():
    c = Canvas(6.0)
    t = c.top
    r = 8.0
    c.store(29, t - 6, 44, 4.4, "D1  Model artifacts (model, scaler, labels)", fs=6.5)
    ya, yb, yc = t - 22, t - 49, t - 77
    c.box(1.5, ya - 6, 14, 12, "Network or\ncapture file\n(Wireshark, CSV)", fc=WHITE, fs=6.2)
    P = {1: (29, ya, "1.0\nExtract\nflows"), 2: (51, ya, "2.0\nBuild and\nscale windows"),
         3: (73, ya, "3.0\nClassify\n(CNN-LSTM)"), 4: (73, yb, "4.0\nDecide action\nand target"),
         5: (73, yc, "5.0\nExecute\nprevention"), 6: (51, yb, "6.0\nExplain\n(SHAP)"),
         7: (29, yc, "7.0\nPresent\nresults")}
    for x, y, s in P.values():
        c.circle(x, y, r, s, fs=6.2, fc=TEAL)
    c.arrow((15.5, ya), (21, ya), "packets", lab=(18.2, ya + 3), fs=5.8)
    c.arrow((37, ya), (43, ya), "flows", lab=(40, ya + 3), fs=5.8)
    c.arrow((59, ya), (65, ya), "windows", lab=(62, ya + 3), fs=5.8)
    c.arrow((73, ya - r), (73, yb + r), "class,\nconfidence", lab=(75, (ya + yb) / 2), fs=5.8, ha="left")
    c.arrow((73, yb - r), (73, yc + r), "action, target", lab=(75, (yb + yc) / 2), fs=5.8, ha="left")
    c.arrow((51, ya - r), (51, yb + r), "window", lab=(53, (ya + yb) / 2), fs=5.8, ha="left")
    c.arrow((44, t - 6), (47, ya + r - 0.5), color=GREY)
    c.arrow((66, t - 6), (69, ya + r - 0.5), color=GREY)
    d3y = (yb + yc) / 2 - 2.5
    c.store(45, d3y, 20, 5, "D3  SHAP background", fs=5.8)
    c.arrow((55, d3y + 5), (55, yb - r + 0.8), color=GREY)
    c.store(85.5, yb - 3.5, 13, 7, "D2  Policy\ntable", fs=5.8)
    c.arrow((85.5, yb), (81, yb), "thresholds", lab=(83.2, yb + 5.2), fs=5.8, color=GREY)
    c.store(43, yc - 3, 18, 6, "D4  Prevention log\nand rule registry", fs=5.8)
    c.arrow((65, yc), (61, yc), "log entry", lab=(63, yc + 3.4), fs=5.8)
    c.arrow((43, yc), (37, yc), "active rules", lab=(40, yc + 3.4), fs=5.8)
    c.arrow((46, yb - 7), (36, yc + 6), both=True, label="request /\nSHAP values", lab=(38, yb - 12), fs=5.6, ha="right")
    c.box(86, yc - 6, 12.5, 12, "Windows\nFirewall", fc=WHITE, fs=6.4)
    c.arrow((81, yc), (86, yc), "netsh\nrule", lab=(83.5, yc + 5.6), fs=5.8)
    c.box(1.5, yc - 6, 14, 12, "Security\nanalyst", fc=WHITE, fs=6.4)
    c.arrow((15.5, yc + 2.4), (21, yc + 2.4), "requests", lab=(18.2, yc + 6), fs=5.8)
    c.arrow((21, yc - 2.4), (15.5, yc - 2.4), "results", lab=(18.2, yc - 6), fs=5.8)
    c.poly([(26, yc + r), (26, ya - r)], "start / stop,\nupload", ls="--", lab=(24.4, (ya + yc) / 2), fs=5.8,
           ha="right")
    c.save(os.path.join(OUT, "fig_4_3b_dfd_level1.png"))


def fig_4_4a_live():
    parties = ["Analyst /\nDashboard", "Flask\nAPI", "Live\nengine", "CNN-LSTM\nmodel", "Policy\n(mapping)",
               "Prevention\nengine", "Windows\nFirewall"]
    steps = [(0, 1, "POST /api/live/start\n(interface)", "call"), (1, 2, "start(interface)", "call"),
             (2, 2, "capture packets (Npcap), build flows;\nflow ends on FIN, RST or 120 s", "self"),
             (2, 3, "predict last 10 flows\n(once per second)", "call"), (3, 2, "class, confidence", "ret"),
             (2, 4, "get_action(class,\nconfidence)", "call"), (4, 2, "action, threshold met?", "ret"),
             (2, 2, "select target: private IPv4 source\nthat sent to this host", "self"),
             (2, 5, "execute_for_result\n(block_ip, target)", "call"),
             (5, 5, "checks: kill switch, scope,\ndeny-list, administrator", "self"),
             (5, 6, "netsh advfirewall:\nadd rule (in, out)", "call"), (6, 5, "rule added", "ret"),
             (5, 2, "execution result", "ret"), (0, 1, "GET /api/live/poll (every 1 s)", "call"),
             (1, 0, "window results with\nexecution status", "ret")]
    sequence(os.path.join(OUT, "fig_4_4a_sequence_live_block.png"), parties, steps)


def fig_4_4b_upload():
    parties = ["Analyst /\nDashboard", "Flask API", "Flow\nextractor", "CNN-LSTM\nmodel", "Policy\n(mapping)",
               "Prevention\nengine"]
    steps = [(0, 1, "POST /api/predict_pcap (file)", "call"),
             (1, 1, "check file type and size limit (200 MB)", "self"),
             (1, 2, "flows_from_pcap(file)", "call"), (2, 1, "flows with 20 features", "ret"),
             (1, 1, "scale features, build windows of 10", "self"),
             (1, 3, "predict(windows)", "call"), (3, 1, "class, confidence\nper window", "ret"),
             (1, 4, "get_action(class,\nconfidence)", "call"), (4, 1, "action, severity,\nheld for review?", "ret"),
             (1, 5, "execute_for_result (in scope,\nkill switch on)", "call"),
             (5, 1, "executed, refused or\nrecommended", "ret"),
             (1, 0, "JSON: batch verdict, statistics,\nper-window results", "ret")]
    sequence(os.path.join(OUT, "fig_4_4b_sequence_upload.png"), parties, steps,
             note="A flow CSV (POST /api/predict_csv) skips steps 2 to 4.")


def fig_4_4c_shap():
    parties = ["Analyst /\nDashboard", "Flask API", "SHAP service", "CNN-LSTM\nmodel"]
    steps = [(0, 1, "POST /api/explain_window\n(window index)", "call"),
             (1, 1, "load cached window (10 x 20)\nfrom the last upload", "self"),
             (1, 2, "explain(window)", "call"),
             (2, 2, "group the inputs into\n20 features", "self"),
             (2, 3, "predict on 1000 perturbed samples\n(real-traffic background)", "call"),
             (3, 2, "class probabilities", "ret"),
             (2, 2, "KernelExplainer: weighted regression\nto SHAP values; check additivity", "self"),
             (2, 1, "SHAP values and\ntop features", "ret"), (1, 0, "JSON explanation", "ret"),
             (0, 0, "draw SHAP bar chart", "self")]
    sequence(os.path.join(OUT, "fig_4_4c_sequence_shap.png"), parties, steps)


def fig_4_4d_revoke():
    parties = ["Analyst /\nDashboard", "Flask API", "Prevention\nengine", "Windows\nFirewall"]
    steps = [(0, 1, "GET /api/prevention/active", "call"), (1, 2, "active_rules()", "call"),
             (2, 1, "rules in force", "ret"), (1, 0, "Blocked devices panel", "ret"),
             (0, 1, "POST /api/prevention/revoke\n(action, target_ip)", "call"),
             (1, 2, "revoke_action(action,\ntarget_ip)", "call"),
             (2, 2, "check scope and administrator\n(kill switch not required)", "self"),
             (2, 3, "netsh advfirewall:\ndelete rule (in, out)", "call"), (3, 2, "rule removed", "ret"),
             (2, 2, "write log, update registry", "self"), (2, 1, "revoked: true", "ret"),
             (1, 0, "OK, panel refreshes", "ret")]
    sequence(os.path.join(OUT, "fig_4_4d_sequence_revoke.png"), parties, steps)


def fig_4_5_model():
    c = Canvas(3.5)
    t = c.top
    blocks1 = [("Input", "10 x 20", WHITE), ("Conv1D 64\nkernel 3, ReLU", "8 x 64", BLUE),
               ("Batch\nnormalisation", "8 x 64", PALE), ("MaxPool\nsize 2", "4 x 64", PALE),
               ("Conv1D 128\nkernel 3, same", "4 x 128", BLUE)]
    blocks2 = [("Batch\nnormalisation", "4 x 128", PALE), ("MaxPool\nsize 2", "2 x 128", PALE),
               ("LSTM\n64 units", "64", TEAL), ("Dense 64\nReLU", "64", AMBER), ("Dense\nsoftmax", "15", ROSE)]
    xs = [1.5 + i * 19.7 for i in range(5)]
    for blocks, y in ((blocks1, t - 20), (blocks2, t - 44)):
        for x, (name, shape, fc) in zip(xs, blocks):
            c.box(x, y, 17, 11, name, fc=fc, fs=6.6)
            c.text(x + 8.5, y - 2.4, ("shape " if name == "Input" else "output ") + shape, fs=6.2, color=GREY,
                   italic=True)
        for a, b in zip(xs, xs[1:]):
            c.arrow((a + 17, y + 5.5), (b, y + 5.5))
    c.poly([(xs[4] + 8.5, t - 24.8), (xs[4] + 8.5, t - 31), (xs[0] + 8.5, t - 31), (xs[0] + 8.5, t - 33)])
    c.text(50, t - 4, "Convolutional feature extractor  >  LSTM sequence model  >  classifier", fs=7, bold=True,
           color=NAVY)
    c.text(50, 2.5, "Total parameters: 83,919 (CICIDS2017 model); optimiser Adam; loss: sparse categorical "
           "cross-entropy", fs=6.4, italic=True, color=GREY)
    c.save(os.path.join(OUT, "fig_4_5_cnn_lstm_architecture.png"))


def fig_4_6_policy():
    c = Canvas(7.4)
    t = c.top
    cx = 36

    def stage(y, text, fc=BLUE, w=34, h=7.4):
        c.box(cx - w / 2, y - h / 2, w, h, text, fc=fc, fs=6.6)

    y0 = t - 5
    stage(y0, "Window prediction:\nclass and confidence", fc=TEAL)
    ys = [y0 - 12.5 * i for i in range(1, 8)]
    c.diamond(cx, ys[0], 30, 8.6, "Class is BENIGN?")
    c.diamond(cx, ys[1], 36, 9.4, "Class locked to\nhuman review?")
    c.diamond(cx, ys[2], 36, 9.4, "Confidence at or above\nthe class threshold?")
    stage(ys[3], "Select target: most frequent private IPv4\nsource that sent to this host\n(not this host, not the gateway)")
    c.diamond(cx, ys[4], 28, 8.6, "Target found?")
    c.diamond(cx, ys[5], 40, 9.8, "Safety checks pass? kill switch on,\nin demo scope, not denied, administrator")
    c.diamond(cx, ys[6], 36, 9.4, "Rule already active\nfor this target?")
    yend = ys[6] - 12.5
    stage(yend, "Add Windows Firewall rule\nblock_ip: until revoked  |  drop_connection: 60 s\n"
          "rate_limit: 120 s (temporary full block)", fc=AMBER, w=40, h=8.4)
    c.arrow((cx, y0 - 3.7), (cx, ys[0] + 4.3))
    for a, b, ha_, hb in ((ys[0], ys[1], 4.3, 4.7), (ys[1], ys[2], 4.7, 4.7)):
        c.arrow((cx, a - ha_), (cx, b + hb), "no", lab=(cx + 1.6, (a + b) / 2 + 0.4), fs=6, ha="left")
    c.arrow((cx, ys[2] - 4.7), (cx, ys[3] + 3.7), "yes", lab=(cx + 1.6, (ys[2] + ys[3]) / 2 + 0.6), fs=6, ha="left")
    c.arrow((cx, ys[3] - 3.7), (cx, ys[4] + 4.3))
    c.arrow((cx, ys[4] - 4.3), (cx, ys[5] + 4.9), "yes", lab=(cx + 1.6, (ys[4] + ys[5]) / 2 + 0.4), fs=6, ha="left")
    c.arrow((cx, ys[5] - 4.9), (cx, ys[6] + 4.7), "yes", lab=(cx + 1.6, (ys[5] + ys[6]) / 2 + 0.4), fs=6, ha="left")
    c.arrow((cx, ys[6] - 4.7), (cx, yend + 4.2), "no", lab=(cx + 1.6, (ys[6] + yend) / 2 + 0.6), fs=6, ha="left")
    outs = [(ys[0], 15, "BENIGN: no action", WHITE, "yes"),
            (ys[1], 18, "Held for human review\n(Bot, Web Brute Force, XSS,\nSQL Injection, Heartbleed,\n"
             "Infiltration)", ROSE, "yes"),
            (ys[2], 18, "Recommendation only:\nbelow threshold", PALE, "no"),
            (ys[4], 14, "Recommendation only:\nno target", PALE, "no"),
            (ys[5], 20, "Refused and logged", ROSE, "no"),
            (ys[6], 18, "Already blocked:\ntraffic dropped", PALE, "yes")]
    for y, reach, text, fc, lab in outs:
        x = cx + reach + 5
        c.box(x, y - 5.2, 98.5 - x, 10.4, text, fc=fc, fs=6.2)
        c.arrow((cx + reach, y), (x, y), lab, lab=(cx + reach + 2.5, y + 2.1), fs=6)
    c.save(os.path.join(OUT, "fig_4_6_prevention_flowchart.png"))


FIGURES = {f.__name__[4:]: f for f in (fig_3_1_block, fig_4_1_architecture, fig_4_2_use_case, fig_4_3a_dfd0,
                                      fig_4_3b_dfd1, fig_4_4a_live, fig_4_4b_upload, fig_4_4c_shap, fig_4_4d_revoke,
                                      fig_4_5_model, fig_4_6_policy)}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name in sys.argv[1:] or FIGURES:
        FIGURES[name]()
        print("drew", name)
