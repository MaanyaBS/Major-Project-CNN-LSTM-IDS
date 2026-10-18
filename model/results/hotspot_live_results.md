# Real Captures on a Phone Hotspot: Scan, Browsing, Device Use (2026-10-17)

Three Wireshark captures recorded on our own devices, run through the same
pipeline the live engine uses: packets -> flows (`model/flow_features.py`)
-> CNN-LSTM (`cnn_lstm_best_v2`) -> policy (`class_action_mapping.get_action`)
-> target (`target_selection.select_target`). The captures are not committed:
they contain personal traffic (`captures/` is git-ignored).

## Setup

| | |
|---|---|
| Victim / IDS | Windows 11 laptop, Wi-Fi, Wireshark + Npcap, 10.66.33.4 |
| Second device | Android tablet, Termux, nmap 7.99 (`nmap -sT`, unprivileged), 10.66.33.57 |
| Network | A phone's mobile hotspot (gateway 10.66.33.227) |
| Firewall | Windows stealth mode off and a temporary allow rule for the tablet only (see finding 1) |

Settings: live termination (flows end at FIN or RST, or 120 s after they
start), Ethernet padding on, sliding windows of 10 flows. "Auto-action" =
`get_action()` status `auto_action`; it can only become a firewall rule if
the window has a LAN target (a private IPv4 address that is neither the laptop
nor the gateway) listed in `IDS_PREVENTION_DEMO_TARGETS`.

## Results

| Capture (about 3 min each) | Measure | IPv4 only | IPv4 + IPv6 |
|---|---|---|---|
| **Scan** (`nmap -sT` from the tablet, 1,051 SYNs in 7 s) | windows targeting the tablet: PortScan | 98.1% | 98.0% |
| | ... auto-action (block) | 97.5% | 97.4% |
| **Browsing** (laptop, ordinary websites) | windows not BENIGN | 3.3% | 10.0% |
| | windows auto-action | 0% | 7.4% |
| | auto-actions with a LAN target | 0 | **0** |
| **Device use** (tablet reloads a page on the laptop every few seconds) | windows not BENIGN | 61.4% (Bot) | 38.4% (Bot) |
| | auto-actions against the tablet | **0** | **0** |

Traffic mix: IPv6 (HTTPS and QUIC) was 98% of the packets while browsing,
97% during device use and 74% during the scan; the scan itself was IPv4.

**Live engine, end to end** (`backend/live_capture.py`, saved captures
replayed at 4x through the real model and backend modules, kill switch off):

- Scan: first PortScan window **1.56 s after the tablet's first SYN**; all 7
  auto-actions targeted 10.66.33.57 (refused only because execution was off).
  No packets dropped.
- Device use: 0 firewall attempts.

## Findings

1. **The model only recognises a scan when the victim answers.** CICIDS2017's
   victims replied to every probe with RST. Windows' default stealth mode
   answers nothing, and the scan then looks benign (offline simulation: 100%
   PortScan with replies, 0% without). The demo therefore turns stealth mode
   off and allows the tablet in, so the laptop answers like the 2017 servers.
   A real limitation of a model trained on that dataset.
2. **Repeated polling of one web server looks like Bot.** CICIDS2017's Bot
   (Ares) is a machine fetching the same small HTTP page every few seconds;
   reloading a page does the same. All 127 such windows were held for review
   because Bot is locked out of automatic action (after its test-set actions
   all hit benign traffic). The lock, not the model, kept the tablet safe.
3. **IPv6 browsing raises false alarms, none of them actionable.** With IPv6
   included, 7.4% of browsing windows say DoS GoldenEye or FTP-Patator with
   enough confidence for automatic action. Their sources are the laptop
   itself and internet servers, so there is no LAN target and nothing is
   executed; the dashboard shows "recommended, no target". IPv4-only analysis
   (`IDS_LIVE_IPV6=0`) gives 3.3% / 0%, but ignores 98% of the browsing packets.
4. **The laptop sees only its own traffic** (promiscuous mode off; Wi-Fi does
   not show other devices' unicast). Another device appears only when it
   talks to the laptop, which is also the only case where blocking it on the
   laptop's firewall means anything.

## Go / No-Go

| Criterion (set before recording) | Result | |
|---|---|---|
| Scan: >= 80% PortScan at >= 0.60 | 98% | met |
| Device use: 0 auto-actions against the listed device | 0 | met |
| Browsing: <= 10% not BENIGN | 3.3% (IPv4) / 10.0% (with IPv6) | met / at the limit |
| Browsing: <= 2% auto-action | 0% (IPv4) / 7.4% (with IPv6) | met / **not met**, but 0 executable |

Go for the live demo, with finding 3 stated: with IPv6 analysed, the
false-alarm criterion fails on recommendations, while the safety criterion
(nothing executable against benign traffic) holds in every capture.

Not yet measured: agreement of the extractor with CICFlowMeter-V3 on the
original CICIDS2017 pcap (`model/validate_against_cicids.py`, pending), and a
live run on the network rather than a replay.
