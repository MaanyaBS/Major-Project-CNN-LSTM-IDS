"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Prevention Target Selection for Live / pcap Windows
Author  : Maanya B S, Ruthwik Sai Ganesh , Varshini D N
==========================================================
Picks the one address a window's prevention action should target: the
most frequent flow source in the window that could be an attacking device
on the local network.

A candidate must be a unicast private IPv4 address (RFC 1918: 10/8,
172.16/12, 192.168/16 - which includes phone hotspots such as Android's
192.168.43.x and iPhone's 172.20.10.x), and not:
  - one of this machine's own addresses,
  - the gateway (the hotspot / router),
  - loopback, link-local, multicast, broadcast or unspecified.
With the flows' destinations given (the live engine always gives them),
only flows sent TO this machine count. Another device's discovery chatter
(SSDP, mDNS: a private source, but sent to a multicast group every device
receives) never addresses this machine, so blocking it here would mean
nothing; found on a shared router, where a phone's SSDP broadcasts were
classified as an attack with 99.6% confidence.

No valid candidate -> None, and the window's action stays a recommendation
with no target. This only chooses; whether the address may really be
blocked is still decided by prevention_executor.check_in_scope()
(TEST-NET or an address listed in IDS_PREVENTION_DEMO_TARGETS).
"""

import ipaddress
from collections import Counter

# Python's is_private also covers documentation ranges (TEST-NET) and more;
# a LAN device is RFC 1918 only.
RFC1918 = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]


def is_candidate(ip, excluded=()):
    """True for a unicast RFC 1918 IPv4 address not in `excluded` (x.x.x.255 treated as broadcast)."""
    if not isinstance(ip, str) or ip in excluded:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.version == 4 and any(addr in net for net in RFC1918) and not ip.endswith(".255")


def select_target(source_ips, local_ips=(), gateway_ips=(), dest_ips=None):
    """
    source_ips: the Source IP of each flow in the window, oldest first.
    dest_ips: their Destination IPs; when given, only flows addressed to one
    of local_ips count.
    Returns the most frequent candidate; ties go to the one seen most recently.
    """
    excluded = set(local_ips) | set(gateway_ips)
    if dest_ips is not None:
        local = set(local_ips)
        source_ips = [s if d in local else None for s, d in zip(source_ips, dest_ips)]
    counts = Counter(ip for ip in source_ips if is_candidate(ip, excluded))
    if not counts:
        return None
    last_seen = {ip: i for i, ip in enumerate(source_ips)}
    return max(counts, key=lambda ip: (counts[ip], last_seen[ip]))
