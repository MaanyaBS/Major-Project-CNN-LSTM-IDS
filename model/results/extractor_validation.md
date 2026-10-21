# Extractor Check Against the Original CICIDS2017 Flows

Our extractor (`model/flow_features.py`, commit 976fe8f) on UNB's original packets, compared flow by flow with CICFlowMeter-V3's official rows.

| | |
|---|---|
| Packets | `Friday-WorkingHours.pcap`, flows starting 2017-07-07 17:00 UTC to 2017-07-07 17:10 UTC |
| Official rows | `GeneratedLabelledFlows.zip` (TrafficLabelling) |
| Timestamp formats seen | minutes, no AM/PM: 286,467 (date order tried: md, dm) |
| Time-zone offset found | UTC-3 (most matches of all whole-hour offsets) |

## Matching

| end_on_rst | Our flows | Official rows in slice | One-to-one matches | Left out (2+ candidates) | Matched only reversed | All 20 features agree (as printed) | Strictly |
|---|---|---|---|---|---|---|---|
| False | 8,000 | 7,332 | 5,957 (81.2%) | 1,352 | 204 | 99.82% | 86.27% |
| True | 8,239 | 7,332 | 5,828 (79.5%) | 1,481 | 249 | 98.94% | 85.35% |

Details below use end_on_rst=False (the better agreement).

## Per Feature

| Feature | Agree (as printed) | Strictly | Median abs. difference where they differ | Median rel. difference where they differ |
|---|---|---|---|---|
| Destination Port | 100.00% | 100.00% | - | - |
| Total Length of Fwd Packets | 99.88% | 99.88% | 806 | 9.54% |
| Total Length of Bwd Packets | 99.88% | 99.88% | 144 | 10.00% |
| Fwd Packet Length Max | 99.98% | 99.98% | 591 | 273.61% |
| Fwd Packet Length Mean | 99.95% | 99.95% | 8.5 | 4.34% |
| Bwd Packet Length Max | 99.98% | 99.98% | 46 | 100.00% |
| Bwd Packet Length Mean | 99.95% | 99.95% | 34.4444 | 10.90% |
| Bwd Packet Length Std | 99.97% | 99.97% | 50.9177 | 5012402917420.24% |
| Flow IAT Max | 99.95% | 86.54% | 317050 | 0.54% |
| Fwd IAT Std | 99.83% | 96.93% | 222875 | 3.86% |
| Max Packet Length | 99.98% | 99.98% | 591 | 273.61% |
| Packet Length Mean | 99.88% | 99.88% | 0.300143 | 0.19% |
| Packet Length Std | 99.90% | 99.90% | 0.253206 | 0.14% |
| Packet Length Variance | 99.90% | 99.90% | 90.2452 | 0.28% |
| Average Packet Size | 99.88% | 99.88% | 0.746296 | 0.45% |
| Avg Fwd Segment Size | 99.95% | 99.95% | 8.5 | 4.34% |
| Avg Bwd Segment Size | 99.95% | 99.95% | 34.4444 | 10.90% |
| Subflow Fwd Packets | 99.88% | 99.88% | 4 | 9.09% |
| Subflow Fwd Bytes | 99.88% | 99.88% | 806 | 9.54% |
| Subflow Bwd Bytes | 99.88% | 99.88% | 144 | 10.00% |
| Total Fwd Packets *(diagnostic, not a model feature)* | 99.88% | 99.88% | 4 | 9.09% |
| Total Backward Packets *(diagnostic, not a model feature)* | 99.90% | 99.90% | 2 | 9.55% |
| Flow Duration *(diagnostic, not a model feature)* | 99.83% | 99.83% | 907224 | 0.79% |

## By Official Label

| Label | Matched flows | All 20 features agree |
|---|---|---|
| BENIGN | 5,908 | 99.81% |
| PortScan | 49 | 100.00% |

## Examples of Disagreement (three least-agreeing features)

**Fwd IAT Std**

| Flow | Label | Ours | Official (as printed) | Fwd/Bwd packets (ours / official) |
|---|---|---|---|---|
| 192.168.10.16:56484 -> 185.167.164.39:443 | BENIGN | 12788 | 2051955.653 | 3/0 / 5/1 |
| 192.168.10.16:38960 -> 172.217.10.130:443 | BENIGN | 2.13112e+07 | 3.03E+07 | 11/14 / 7/7 |
| 192.168.10.50:56410 -> 192.168.10.3:3268 | BENIGN | 4.77834e+06 | 5213121.058 | 48/24 / 44/22 |
| 192.168.10.50:56410 -> 192.168.10.3:3268 | BENIGN | 5.1356e+06 | 5486590.942 | 48/24 / 44/22 |
| 192.168.10.50:56410 -> 192.168.10.3:3268 | BENIGN | 6.27541e+06 | 5940806.167 | 36/18 / 40/20 |

**Total Length of Fwd Packets**

| Flow | Label | Ours | Official (as printed) | Fwd/Bwd packets (ours / official) |
|---|---|---|---|---|
| 192.168.10.16:38960 -> 172.217.10.130:443 | BENIGN | 1422 | 354 | 11/14 / 7/7 |
| 192.168.10.16:56484 -> 185.167.164.39:443 | BENIGN | 77 | 123 | 3/0 / 5/1 |
| 192.168.10.50:56410 -> 192.168.10.3:3268 | BENIGN | 7254 | 8060 | 36/18 / 40/20 |
| 192.168.10.50:42446 -> 192.168.10.3:389 | BENIGN | 6562 | 7254 | 34/18 / 36/18 |
| 192.168.10.50:56410 -> 192.168.10.3:3268 | BENIGN | 9672 | 8866 | 48/24 / 44/22 |

**Total Length of Bwd Packets**

| Flow | Label | Ours | Official (as printed) | Fwd/Bwd packets (ours / official) |
|---|---|---|---|---|
| 192.168.10.16:56484 -> 185.167.164.39:443 | BENIGN | 0 | 46 | 3/0 / 5/1 |
| 192.168.10.16:38960 -> 172.217.10.130:443 | BENIGN | 400 | 210 | 11/14 / 7/7 |
| 192.168.10.50:42446 -> 192.168.10.3:389 | BENIGN | 5068 | 5688 | 34/18 / 36/18 |
| 192.168.10.50:56410 -> 192.168.10.3:3268 | BENIGN | 1296 | 1440 | 36/18 / 40/20 |
| 192.168.10.50:56410 -> 192.168.10.3:3268 | BENIGN | 1728 | 1584 | 48/24 / 44/22 |

Agreement: equal at the precision the official CSV printed (it writes large values with three significant digits, e.g. 1.02E+07); 'Strictly': within 1e-4 relative (1e-6 absolute). Rows left out (2+ candidate flows in the same minute, mostly reused nmap source ports) are not evidence either way.
