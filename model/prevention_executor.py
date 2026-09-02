"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Prevention Execution Engine - Safety Boundary
Author  : Person B (Model Development)
==========================================================
Defines the safety boundary for REAL automated prevention actions.
This module does not execute anything by itself (that's the OS-level
execution engine built on top of it) - it defines the rules that
govern what execution is allowed to touch, checked independently of
and before any OS-level command is ever run.

Three independent layers, all of which must pass:

1. Global kill switch (PREVENTION_EXECUTION_ENABLED). Defaults to
   False - real execution is opt-in, never on by default.
2. Scope allow-list. The target IP must fall within one of the
   RFC 5737 "TEST-NET" ranges (192.0.2.0/24, 198.51.100.0/24,
   203.0.113.0/24) - ranges permanently reserved for documentation
   and testing, guaranteed to never route on the real internet. This
   means real execution can never reach a real destination, by
   construction, regardless of what a demo happens to feed it.
3. Explicit deny-list. Defense in depth: loopback and broadcast
   addresses are always refused even if a bug somehow got them past
   the allow-list.
"""

import ipaddress

# Layer 1: global kill switch. Must be flipped explicitly - never
# defaults to executing.
PREVENTION_EXECUTION_ENABLED = False

# Layer 2: only these ranges are ever eligible for real execution.
# RFC 5737 TEST-NET-1/2/3 - reserved for documentation/testing,
# never assigned to real hosts on the real internet.
ALLOWED_DEMO_RANGES = [
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
]

# Layer 3: always refused, regardless of the allow-list result.
NEVER_BLOCK = {
    "0.0.0.0",
    "127.0.0.1",
    "255.255.255.255",
}


class ExecutionNotPermitted(Exception):
    """Raised when a target/action fails the safety boundary check."""


def check_safe_to_execute(target_ip: str) -> None:
    """
    Raises ExecutionNotPermitted if target_ip is not safe to act on
    for real. Call this before any real OS-level action is attempted.
    Returns None (silently passes) only if the target is within the
    allowed demo scope and execution is enabled.
    """
    if not PREVENTION_EXECUTION_ENABLED:
        raise ExecutionNotPermitted(
            "Real execution is disabled (PREVENTION_EXECUTION_ENABLED=False). "
            "This is the default - flip it explicitly to enable real actions."
        )

    if target_ip in NEVER_BLOCK:
        raise ExecutionNotPermitted(f"{target_ip} is on the permanent deny-list.")

    try:
        addr = ipaddress.ip_address(target_ip)
    except ValueError:
        raise ExecutionNotPermitted(f"{target_ip} is not a valid IP address.")

    if not any(addr in net for net in ALLOWED_DEMO_RANGES):
        raise ExecutionNotPermitted(
            f"{target_ip} is outside the allowed demo scope "
            f"(RFC 5737 TEST-NET ranges only: 192.0.2.0/24, 198.51.100.0/24, "
            f"203.0.113.0/24). Refusing to act on real, routable addresses."
        )
