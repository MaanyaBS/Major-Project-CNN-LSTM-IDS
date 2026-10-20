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
| **Scan** (`nmap -sT` from the tablet, 1,051 SYNs in 7 s) | windows targeting the tablet: PortScan | 98.2% | 97.8% |
| | ... auto-action (block) | 97.6% | 97.5% |
| **Browsing** (laptop, ordinary websites) | windows not BENIGN | 3.6% | 11.1% |
| | windows auto-action | 0% | 7.6% |
| | auto-actions with a LAN target | 0 | **0** |
| **Device use** (tablet reloads a page on the laptop every few seconds) | windows not BENIGN | 61.7% (Bot) | 38.0% (Bot) |
| | auto-actions against the tablet | **0** | **0** |

Traffic mix: IPv6 (HTTPS and QUIC) was 98% of the packets while browsing,
97% during device use and 74% during the scan; the scan itself was IPv4.

**Live engine, end to end** (`backend/live_capture.py`, saved captures
replayed at 4x through the real model and backend modules, kill switch off):

- Scan: first PortScan window **1.6 s after the tablet's first SYN** (one
  prediction per second); all 7
  auto-actions targeted 10.66.33.57 (refused only because execution was off).
  No packets dropped.
- Device use: 0 firewall attempts.

## Live Run on a Shared Router (2026-10-18)

The same pipeline live, not replayed: `backend/live_capture.py` in the
dashboard (a local merge of `varshini-dashboard` with `person-b-model`),
kill switch on, only the tablet listed in `IDS_PREVENTION_DEMO_TARGETS`.
Network: a home Wi-Fi router used daily by 20-30 people, with the owner's
permission; laptop 192.168.29.132, tablet 192.168.29.73, router
192.168.29.1. Times are UTC (local time is UTC+5:30).

| Time | Window | What happened |
|---|---|---|
| 09:33:52-54 | #7-9 | The tablet reloads a page on the laptop: Bot (0.78-0.95), **held for review**, nothing executed |
| 09:35:13.0 | #14 | nmap's first probes (ports 80, 443) in the window; BENIGN |
| 09:35:14.0 | #15 | First scan ports (21, 22, 23, 25, 135, ...); BENIGN (0.55) |
| **09:35:15.1** | **#16** | **PortScan 0.991 -> tablet blocked** (rule written 09:35:15.45) |
| 09:35:16-27 | #17-28 | 12 more PortScan windows (0.985-0.998): "already blocked", no second rule |

- **Detection about 2 s after nmap's first probes**, as the replay predicted
  (1.6 s).
- **The block was effective:** nmap (14.1 s) listed the services it reached
  after the block - the test page (8000), the dashboard (8080), AnyDesk
  (7070) - as filtered, and the tablet could no longer load the test page.
  Most of the 1,000 ports had already been probed (990 "closed", 3 open:
  135, 139, 445): a block stops the attacker from then on, not probes
  already answered. Ports with no service still answer "closed" while stealth
  mode is off (the demo setting).
- **Revoke worked:** after it, the tablet loaded the page again.
- **Three full cycles** of scan -> block -> revoke (blocks at 09:35:15,
  09:52:09, 09:58:45; revokes at 09:51:35, 09:57:17, 09:59:57); 18 repeat
  detections answered "already blocked".
- **A bystander was flagged and refused.** Another person's device
  (192.168.29.91) was classified DoS Slowhttptest at 0.996 from its SSDP
  discovery broadcasts (UDP 1900 to 239.255.255.250); the engine refused all
  10 attempts (not listed). It never addressed the laptop, so since this run
  only devices that **sent traffic to this machine** can become targets
  (`select_target(..., dest_ips)`); the three captures above score
  identically under that rule.
- 3,707 packets, 1,193 flows, 32 windows in the first run; no packets
  dropped, no errors.

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
   included, 7.6% of browsing windows say DoS GoldenEye or FTP-Patator with
   enough confidence for automatic action. Their sources are the laptop
   itself and internet servers, so there is no LAN target and nothing is
   executed; the dashboard shows "recommended, no target". IPv4-only analysis
   (`IDS_LIVE_IPV6=0`) gives 3.6% / 0%, but ignores 98% of the browsing packets.
4. **The laptop sees its own traffic plus other devices' broadcasts and
   multicasts** (promiscuous mode off; Wi-Fi does not show other devices'
   unicast). Only a device that talks to the laptop can be a target: that is
   the only case where blocking it on the laptop's firewall means anything,
   and the live run showed why broadcasts must not count (see above).

## Go / No-Go

| Criterion (set before recording) | Result | |
|---|---|---|
| Scan: >= 80% PortScan at >= 0.60 | 98% | met |
| Device use: 0 auto-actions against the listed device | 0 | met |
| Browsing: <= 10% not BENIGN | 3.6% (IPv4) / 11.1% (with IPv6) | met / **not met** |
| Browsing: <= 2% auto-action | 0% (IPv4) / 7.6% (with IPv6) | met / **not met**, but 0 executable |

Go for the live demo, with finding 3 stated: with IPv6 analysed, both
false-alarm criteria fail on recommendations, while the safety criterion
(nothing executable against benign traffic) holds in every capture.

Numbers above use the extractor after the CICFlowMeter-V3 FIN rule found by
`model/validate_against_cicids.py` (a flow whose first packet carries FIN
stays open); before it, every figure was within 1.1 points of these. The
live run above confirms them on a real network.
