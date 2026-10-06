#!/usr/bin/env python3
"""Week 5 · Task 1 — Subnets and longest-prefix match.

Textbook §4.3.2 (IPv4 addressing, CIDR) and §4.3.3 (forwarding).

Two things a router does with every packet: work out which prefixes the
destination falls inside, and pick the longest one. The second is the whole
of "longest prefix match", and it is the reason the internet's routing table
can hold a million entries and still be answerable.

You build both, from integers up. No `ipaddress` module - that library is
exactly the thing you are supposed to understand this week.

    python3 task1_forward.py --verify
"""
import argparse


def _address_to_int(address):
    """Pack four decimal octets into one 32-bit integer."""
    octets = address.split(".")
    if len(octets) != 4:
        raise ValueError("an IPv4 address must have four octets")
    value = 0
    for octet in octets:
        if not octet or not octet.isascii() or not octet.isdecimal():
            raise ValueError("each IPv4 octet must be a decimal number")
        number = int(octet)
        if not 0 <= number <= 255:
            raise ValueError("each IPv4 octet must be between 0 and 255")
        value = (value << 8) | number
    return value


def _int_to_address(value):
    """Extract the four octets, from most significant to least significant."""
    return ".".join(str((value >> shift) & 255) for shift in (24, 16, 8, 0))


def _prefix_mask(prefix_len):
    # Python integers are unbounded; keep only the low 32 bits.
    return (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF


def parse_cidr(cidr):
    """'163.152.6.0/24' -> (network as int, prefix length).

    Requirements: reject a prefix length outside 0-32, and reject an address
    whose host bits are set when they should not be (163.152.6.5/24 is a
    common way to write a host, but it is not a network).
    """
    address, prefix = cidr.split("/")
    if not prefix or not prefix.isascii() or not prefix.isdecimal():
        raise ValueError("prefix length must be a decimal number from 0 to 32")
    prefix_len = int(prefix)
    if not 0 <= prefix_len <= 32:
        raise ValueError("prefix length must be between 0 and 32")
    network = _address_to_int(address)
    mask = _prefix_mask(prefix_len)
    if network & mask != network:
        raise ValueError("network address must have all host bits set to zero")
    return network, prefix_len


def network_range(cidr):
    """'163.152.6.0/24' -> (first usable, last usable, broadcast) as strings.

    Careful at the edges. /31 and /32 do not have a usable host range in the
    ordinary sense - decide what you return and say so in observation.md.
    """
    network, prefix_len = parse_cidr(cidr)
    host_mask = 0xFFFFFFFF ^ _prefix_mask(prefix_len)
    broadcast = network | host_mask
    if prefix_len >= 31:
        # Convention: both /31 endpoints are usable; /32 is a single host.
        # The third field remains the all-host-bits-one address, even though
        # these cases do not have a separate directed broadcast address.
        first, last = network, broadcast
    else:
        first, last = network + 1, broadcast - 1
    return tuple(_int_to_address(value) for value in (first, last, broadcast))


class ForwardingTable:
    """Longest-prefix-match forwarding.

    add(cidr, next_hop)  ·  lookup(address) -> next_hop or None

    The default route 0.0.0.0/0 matches everything and is the shortest prefix,
    so it must lose to any other match. Repeated identical prefixes keep the
    first next hop. Different networks with the same prefix length are valid.
    """

    def __init__(self):
        self.entries = []

    def add(self, cidr, next_hop):
        network, prefix_len = parse_cidr(cidr)
        self.entries.append((network, prefix_len, _prefix_mask(prefix_len), next_hop))

    def lookup(self, address):
        destination = _address_to_int(address)
        best_length = -1  # Allows even a /0 route to become the first match.
        best_hop = None
        for network, prefix_len, mask, next_hop in self.entries:
            if destination & mask == network and prefix_len > best_length:
                best_length = prefix_len
                best_hop = next_hop
        return best_hop


# ------------------------------------------------------------------- harness
RANGE_CASES = [
    ("192.168.0.0/24",  "192.168.0.1",   "192.168.0.254",  "192.168.0.255"),
    ("10.0.0.0/8",      "10.0.0.1",      "10.255.255.254", "10.255.255.255"),
    ("172.16.32.0/20",  "172.16.32.1",   "172.16.47.254",  "172.16.47.255"),
    ("203.0.113.64/26", "203.0.113.65",  "203.0.113.126",  "203.0.113.127"),
]

TABLE = [
    ("0.0.0.0/0",       "default-gw"),
    ("10.0.0.0/8",      "campus"),
    ("10.20.0.0/16",    "eng-building"),
    ("10.20.30.0/24",   "lab-floor"),
    ("10.20.30.64/26",  "lab-rack-2"),
    ("192.168.1.0/24",  "home"),
]

LOOKUP_CASES = [
    ("10.20.30.70",   "lab-rack-2"),     # inside all four 10.x entries
    ("10.20.30.10",   "lab-floor"),
    ("10.20.99.1",    "eng-building"),
    ("10.99.0.1",     "campus"),
    ("8.8.8.8",       "default-gw"),
    ("192.168.1.77",  "home"),
]


def verify():
    fails = 0
    for cidr, first, last, bcast in RANGE_CASES:
        try:
            got = network_range(cidr)
        except NotImplementedError:
            print("  network_range is still a stub"); return 1
        except Exception as e:
            print(f"  FAIL  {cidr:<18} raised {e!r}"); fails += 1; continue
        ok = tuple(got) == (first, last, bcast)
        print(f"  {'ok  ' if ok else 'FAIL'}  {cidr:<18} {got}")
        fails += not ok

    t = ForwardingTable()
    try:
        for cidr, hop in TABLE:
            t.add(cidr, hop)
    except NotImplementedError:
        print("  ForwardingTable is still a stub"); return 1

    for addr, expect in LOOKUP_CASES:
        got = t.lookup(addr)
        ok = got == expect
        print(f"  {'ok  ' if ok else 'FAIL'}  {addr:<16} -> {got}  (want {expect})")
        fails += not ok

    print(f"\n  {len(RANGE_CASES) + len(LOOKUP_CASES) - fails}"
          f"/{len(RANGE_CASES) + len(LOOKUP_CASES)} ok")
    return 1 if fails else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    raise SystemExit(verify() if a.verify else p.print_help())
