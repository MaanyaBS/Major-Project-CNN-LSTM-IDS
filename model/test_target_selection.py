"""
Tests for model/target_selection.py.

Run:  python model/test_target_selection.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from target_selection import is_candidate, select_target  # noqa: E402

LAPTOP, GATEWAY, ATTACKER, OTHER = "192.168.43.10", "192.168.43.1", "192.168.43.57", "192.168.43.80"


def test_picks_the_most_frequent_valid_source():
    window = [LAPTOP] * 4 + [ATTACKER] * 5 + [OTHER]
    assert select_target(window, [LAPTOP], [GATEWAY]) == ATTACKER


def test_never_the_laptop_or_the_gateway():
    assert select_target([LAPTOP] * 10, [LAPTOP], [GATEWAY]) is None
    assert select_target([GATEWAY] * 9 + [OTHER], [LAPTOP], [GATEWAY]) == OTHER


def test_multicast_link_local_and_broadcast_chatter_ignored():
    chatter = ["224.0.0.251", "239.255.255.250", "169.254.12.7", "255.255.255.255",
               "192.168.43.255", "0.0.0.0", "127.0.0.1"]
    assert select_target(chatter * 3, [LAPTOP], [GATEWAY]) is None
    assert select_target(chatter * 3 + [ATTACKER], [LAPTOP], [GATEWAY]) == ATTACKER


def test_public_ipv6_and_garbage_are_not_candidates():
    for ip in ("8.8.8.8", "142.250.183.14", "fe80::1", "fd00::5", "", None, "not-an-ip", 3232235777):
        assert not is_candidate(ip), ip
    assert select_target(["8.8.8.8"] * 10, [LAPTOP], [GATEWAY]) is None, "public servers are never targets"


def test_test_net_addresses_are_not_private_lan_devices():
    # TEST-NET ranges are documentation addresses, not private: the demo CSV path targets them
    # through its own Source IP column, not through this selector.
    assert not is_candidate("192.0.2.66")


def test_tie_goes_to_the_most_recent_source():
    assert select_target([ATTACKER, OTHER, ATTACKER, OTHER], [LAPTOP]) == OTHER


def test_only_devices_that_address_this_machine_count():
    # Seen on a shared router: a phone's SSDP broadcasts (private source, multicast destination).
    ssdp = "239.255.255.250"
    srcs, dsts = [OTHER] * 9 + [ATTACKER], [ssdp] * 9 + [LAPTOP]
    assert select_target(srcs, [LAPTOP], [GATEWAY]) == OTHER, "without destinations: the old behaviour"
    assert select_target(srcs, [LAPTOP], [GATEWAY], dsts) == ATTACKER
    assert select_target([OTHER] * 10, [LAPTOP], [GATEWAY], [ssdp] * 10) is None
    assert select_target([OTHER] * 10, [LAPTOP], [GATEWAY], ["192.168.43.255"] * 10) is None


def test_no_candidate_gives_none_not_a_random_address():
    assert select_target([], [LAPTOP]) is None
    assert select_target([LAPTOP, "8.8.8.8", "224.0.0.251"], [LAPTOP], [GATEWAY]) is None


if __name__ == "__main__":
    tests = [fn for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
