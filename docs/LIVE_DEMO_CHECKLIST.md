# Live Demo Checklist — Detect and Block a Real Scan

Step-by-step script for running the live demo (and the test run before it):
the laptop runs the IDS, a second device scans it, the dashboard shows the
detection and the firewall blocks that device, then the block is revoked.
About 30 minutes the first time. Commands are for PowerShell on the laptop.

**Never scan anything except your own laptop. Never list the hotspot or
router as a target. Ask the network owner first if it is not your network.**

---

## A. What you need

| | |
|---|---|
| Laptop | Windows, Wireshark + Npcap installed, this project, dashboard folder ready (B1) |
| Second device | The Android tablet with Termux + nmap (`pkg install nmap`) |
| Network | A phone hotspot or router that **both** devices join. The second device must **not** be the hotspot itself (the gateway is never a target, so it could never be blocked) |
| Off | ExpressVPN (or any VPN) on the laptop |

---

## B. Before the day

1. **Dashboard folder.** The dashboard branch must contain the live engine
   (`backend/live_capture.py`). Once the dashboard teammate has merged
   `person-b-model`, check it out into its own folder, e.g.
   `D:\Data\Ruthwik\Desktop\ids-demo` (ask Claude to prepare it).
2. **Dashboard dependencies, once:** in `ids-demo\frontend` run `npm install`.
3. **Stealth mode is off** (already done; check, Administrator PowerShell):
   ```powershell
   foreach ($p in 'DomainProfile','PrivateProfile','PublicProfile') { "{0}: {1}" -f $p, (Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\WindowsFirewall\$p" -Name DisableStealthMode -ErrorAction SilentlyContinue).DisableStealthMode }
   ```
   All three must print `1`. (Why: a model trained on 2017 traffic only
   recognises a scan when the victim answers it; stealth mode answers nothing.)

---

## C. On the day: set up (15 min)

1. **Connect** the laptop and the tablet to the same hotspot / router. VPN off.
2. **Laptop addresses** (normal PowerShell): `ipconfig` -> under *Wireless LAN
   adapter Wi-Fi* note **IPv4 Address** (LAPTOP_IP) and **Default Gateway**.
3. **Tablet address:** Settings -> Connections -> Wi-Fi -> gear next to the
   network -> **IP address** (TABLET_IP). It must differ from the Default
   Gateway of step 2.
4. **Open PowerShell as Administrator** (Start -> type PowerShell -> Run as
   administrator). Use this window for steps 5-7 and D1.
5. **Clear old demo rules** (from earlier tests):
   ```powershell
   Get-NetFirewallRule -DisplayName 'IDS_DEMO_*' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
   Get-NetFirewallRule -DisplayName 'IDS_*' -ErrorAction SilentlyContinue | Select DisplayName
   ```
   The second command must print nothing.
6. **Let the tablet reach the laptop** (temporary; replace TABLET_IP):
   ```powershell
   netsh advfirewall firewall add rule name=IDS_TEST_allow_scanner dir=in action=allow protocol=TCP remoteip=TABLET_IP
   ```
   Prints `Ok.` A block rule from the IDS overrides this allow rule.
7. **Test page** (a second, normal PowerShell window; leave it running):
   ```powershell
   mkdir D:\httptest -Force; Set-Content D:\httptest\index.html "hello from laptop"
   & "D:\Data\Ruthwik\Desktop\MAJOR-PROJECT-CNN-LSTM-IDS\venv\Scripts\python.exe" -m http.server 8000 --directory D:\httptest
   ```
   It must print `Serving HTTP on :: port 8000` and keep running (a bare
   `python` on this laptop resolves to a file that does nothing).
8. **Check the path:** on the tablet open `http://LAPTOP_IP:8000` (Samsung
   Internet, or Chrome with *Always use secure connections* off). It must show
   *hello from laptop*. If not: wrong IP, VPN on, or the router isolates
   devices (use its main network, not a guest network).

---

## D. Start the IDS

1. **Backend**, in the Administrator window (replace TABLET_IP):
   ```powershell
   cd D:\Data\Ruthwik\Desktop\ids-demo\backend
   $env:IDS_PREVENTION_EXECUTION_ENABLED = "1"
   $env:IDS_PREVENTION_DEMO_TARGETS = "TABLET_IP"
   $env:OPENBLAS_NUM_THREADS = "1"
   D:\Data\Ruthwik\Desktop\MAJOR-PROJECT-CNN-LSTM-IDS\venv\Scripts\python.exe app.py
   ```
   Wait until it serves on `http://127.0.0.1:5000`. Leave it running.
   (Optional: `$env:IDS_LIVE_IPV6 = "0"` before starting analyses IPv4 only:
   fewer recommendation-only alarms, but most hotspot traffic is then ignored.)
2. **Dashboard**, in a third, normal PowerShell window:
   ```powershell
   cd D:\Data\Ruthwik\Desktop\ids-demo\frontend
   npm run dev
   ```
   Open the address it prints in the browser.
3. In the dashboard: **Live Feed -> Live capture**. The banner must **not** say
   "stub"; execution must show as **enabled**. Choose **Wi-Fi** -> **Start**.
   The packet and flow counters start moving.

---

## E. The demo (5 min)

| # | Do | Expect |
|---|---|---|
| 1 | Browse a few sites on the laptop for a minute | Mostly BENIGN. Some "recommended, no target" items can appear (IPv6/QUIC); nothing is executed |
| 2 | Tablet: reload `http://LAPTOP_IP:8000` a few times | Page loads. Windows from the tablet may say Bot, **held for review**; nothing is executed |
| 3 | Tablet, in Termux: `nmap -sT LAPTOP_IP`. Note the time nmap prints | Within about 2 s: **PortScan**, *executed: firewall rule added* for TABLET_IP; **Blocked devices** lists it. nmap still lists most ports *closed* (probed before the block); services it reached afterwards show *filtered* |
| 4 | Administrator window: `Get-NetFirewallRule -DisplayName 'IDS_DEMO_*' \| Select DisplayName` | `IDS_DEMO_block_ip_<tablet>_in` and `_out` |
| 5 | Tablet: reload the page; optionally run `nmap -sT LAPTOP_IP` again | Page fails. In nmap the laptop's services (8000, 8080, ...) show *filtered*; ports with no service still show *closed* while stealth mode is off. Dashboard: *already blocked — dropped* |
| 6 | Dashboard: **Revoke** on the tablet in Blocked devices | Panel empties; step 4's command prints nothing; the page loads again |
| 7 | **Stop** the capture | Counters stop |

Take screenshots at 3, 5 and 6, and note the times of step 3 (nmap start and
the PortScan window) for the report.

---

## F. Clean up (same day)

1. Ctrl+C in the backend, dashboard and test-page windows.
2. Administrator window:
   ```powershell
   Get-NetFirewallRule -DisplayName 'IDS_DEMO_*' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
   netsh advfirewall firewall delete rule name=IDS_TEST_allow_scanner
   ```
   The second prints `Deleted 1 rule(s). Ok.`
3. Close the Administrator window (this clears the environment variables).

**After the project** (not before the final demo): turn stealth mode back
on, then restart the laptop:
```powershell
foreach ($p in 'DomainProfile','PrivateProfile','PublicProfile') { Remove-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\WindowsFirewall\$p" -Name DisableStealthMode -ErrorAction SilentlyContinue }
```

---

## G. If something goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| Banner says **stub** | The dashboard folder has no `backend/live_capture.py`, or it failed to import (the banner shows the error) | Use a folder with the merge (B1); read the import error |
| "Npcap was not found" | Npcap missing | Install Npcap (from Wireshark's installer or npcap.com), restart the backend |
| Scan shows only **BENIGN** | The laptop is not answering the scan | nmap must show ports as *closed*, not *filtered*: check B3 and the allow rule's IP (C6) |
| PortScan but *Real execution is disabled* | Kill switch off | Set `IDS_PREVENTION_EXECUTION_ENABLED` in the **same** window before `python app.py` (D1) |
| *outside the allowed demo scope* | `IDS_PREVENTION_DEMO_TARGETS` does not match the tablet | Re-check TABLET_IP (C3), restart the backend |
| *Administrator privileges required* | Backend not elevated | Start it from the Administrator window |
| PortScan but **no target** | The scanner is the gateway (hotspot), or traffic comes through a VPN | Use a separate hotspot / router; VPN off |
| Tablet cannot open the page | Test page not running, wrong IP, VPN, or client isolation on the router | C7 must say *Serving HTTP*; C2, C3, C8 |
| A stranger's device is flagged | Its broadcasts reach the laptop | Expected: it is never listed, so the engine refuses; it is not even a target unless it sends traffic to the laptop |
