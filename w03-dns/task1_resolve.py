#!/usr/bin/env python3
"""Week 3 · Task 1 — Build your own iterative resolver.

Textbook §2.4.2 - §2.4.3.

`dig +trace` walks root -> TLD -> authoritative for you. In this task you do
that walk yourself: start at a root server, read the delegation it returns,
ask the next server, and keep going until somebody answers authoritatively.

You may shell out to `dig` for the transport, or use a DNS library
(`dnspython` is in the container). Either is fine - what matters is that
*you* follow the delegations rather than letting a tool do it.

    python3 task1_resolve.py www.korea.ac.kr
    python3 task1_resolve.py --verify        # check yourself against dig

Pass condition
--------------
`--verify` resolves five names with your resolver and with `dig`, and the
addresses must agree. A name behind a CDN may legitimately return a different
address each time; the harness compares the *set of authoritative nameservers*
you ended at for those, not the address.
"""
import argparse, subprocess, sys

# Root servers. Everything starts here; there is no earlier step.
ROOT_SERVERS = [
    "198.41.0.4",       # a.root-servers.net
    "199.9.14.201",     # b.root-servers.net
    "192.33.4.12",      # c.root-servers.net
]

# (name, kind).  "stable" names must match dig exactly.  "cdn" names are served
# from many replicas and may legitimately give you a different address than dig
# got a second earlier - for those we only require that you reached an answer.
VERIFY_NAMES = [
    ("www.korea.ac.kr", "stable"),
    ("dns.google", "stable"),
    ("en.wikipedia.org", "stable"),
    ("www.stanford.edu", "stable"),
    ("www.microsoft.com", "cdn"),
]


class Resolver:
    """Your iterative resolver.

    The whole point is that you never ask a server to recurse for you.
    You ask one server, it says "not mine, ask over there", and you go there.

    Suggested shape - but it is yours to design:

        resolve(name) -> (address, path)
            address : the A record you ended up with, as a string
            path    : the servers you asked, in order, so you can show your work

    Things you will hit, in roughly this order:

    1.  A delegation gives you NS *names*, sometimes with glue A records and
        sometimes without. No glue means you have to resolve that nameserver's
        name first - which is another walk. Decide what you do there.
    2.  A server may not answer. Try the next one rather than giving up.
    3.  CNAMEs. The answer you get back may be a different name than the one
        you asked for, and you have to start again with that name.
    4.  Loops. Cap your depth.

    If you shell out to dig, the flag you want is `+norecurse`, so that the
    server you ask replies with a delegation instead of doing the work:

        dig @198.41.0.4 www.korea.ac.kr +norecurse
    """

    def resolve(self, name):
        import dns.exception
        import dns.flags
        import dns.message
        import dns.query
        import dns.rcode
        import dns.rdatatype

        path = []
        active_names = set()
        max_queries = 100

        def walk(target):
            target = target.rstrip(".").lower() + "."
            if target in active_names:
                raise RuntimeError(f"DNS lookup loop at {target}")
            active_names.add(target)
            try:
                servers = list(ROOT_SERVERS)
                while servers:
                    next_servers = None
                    errors = []
                    for server in servers:
                        if len(path) >= max_queries:
                            raise RuntimeError("DNS query limit exceeded")
                        path.append(server)
                        query = dns.message.make_query(target, dns.rdatatype.A)
                        query.flags &= ~dns.flags.RD
                        try:
                            reply = dns.query.udp(query, server, timeout=2)
                            if reply.flags & dns.flags.TC:
                                reply = dns.query.tcp(query, server, timeout=2)
                        except (dns.exception.DNSException, OSError) as exc:
                            errors.append(f"{server}: {exc}")
                            continue

                        if reply.rcode() == dns.rcode.NXDOMAIN:
                            raise LookupError(f"{target} does not exist")
                        if reply.rcode() != dns.rcode.NOERROR:
                            errors.append(f"{server}: {dns.rcode.to_text(reply.rcode())}")
                            continue

                        cnames = {}
                        for rrset in reply.answer:
                            owner = rrset.name.to_text().lower()
                            if rrset.rdtype == dns.rdatatype.A and owner == target:
                                return rrset[0].address
                            if rrset.rdtype == dns.rdatatype.CNAME:
                                cnames[owner] = rrset[0].target.to_text().lower()

                        # A reply may contain the entire CNAME chain, or only its
                        # first link. Restart at the root for the final name.
                        if target in cnames:
                            alias = target
                            seen = set()
                            while alias in cnames:
                                if alias in seen:
                                    raise RuntimeError(f"CNAME loop at {alias}")
                                seen.add(alias)
                                alias = cnames[alias]
                            if alias in active_names:
                                raise RuntimeError(f"CNAME loop at {alias}")
                            return walk(alias)

                        ns_names = [r.target.to_text().lower()
                                    for rrset in reply.authority
                                    if rrset.rdtype == dns.rdatatype.NS
                                    for r in rrset]
                        if not ns_names:
                            errors.append(f"{server}: no A answer or NS referral")
                            continue

                        glue = {}
                        for rrset in reply.additional:
                            if rrset.rdtype == dns.rdatatype.A:
                                glue.setdefault(rrset.name.to_text().lower(), []).extend(
                                    r.address for r in rrset)
                        candidates = [addr for ns in ns_names
                                      for addr in glue.get(ns, [])]
                        # Missing glue requires a separate iterative lookup of
                        # the nameserver's own A record.
                        for ns in ns_names:
                            if ns not in glue:
                                try:
                                    candidates.append(walk(ns))
                                except (LookupError, RuntimeError):
                                    continue
                        if candidates:
                            next_servers = list(dict.fromkeys(candidates))
                            break
                        errors.append(f"{server}: nameservers have no reachable A record")

                    if next_servers is None:
                        raise LookupError(f"Cannot resolve {target}: {'; '.join(errors)}")
                    servers = next_servers
                raise LookupError(f"Cannot resolve {target}")
            finally:
                active_names.remove(target)

        return walk(name), path


# ------------------------------------------------------------------- harness
def dig_answer(name):
    """What the system resolver says, for comparison."""
    out = subprocess.run(["dig", "+short", name, "A"],
                         capture_output=True, text=True).stdout
    return [l for l in out.split() if l and l[0].isdigit()]


def verify():
    r, failures = Resolver(), 0
    for name, kind in VERIFY_NAMES:
        try:
            addr, path = r.resolve(name)
        except NotImplementedError:
            print("Nothing implemented yet - write Resolver.resolve first.")
            return 1
        except Exception as e:
            print(f"  FAIL  {name:<22} your resolver raised {e!r}")
            failures += 1
            continue
        expected = dig_answer(name)
        if addr in expected:
            note = ""
        elif kind == "cdn":
            note = "  <- differs, but this name is CDN-hosted. Explain it."
        else:
            note = "  <- should have matched"
            failures += 1
        print(f"  {'FAIL' if note.endswith('matched') else 'ok  '}  {name:<22} "
              f"you={addr:<16} dig={','.join(expected) or '-'}   "
              f"hops={len(path)}{note}")
    print(f"\n  {len(VERIFY_NAMES) - failures}/{len(VERIFY_NAMES)} ok")
    return 1 if failures else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name", nargs="?", default="www.korea.ac.kr")
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()

    if a.verify:
        sys.exit(verify())

    addr, path = Resolver().resolve(a.name)
    for i, server in enumerate(path, 1):
        print(f"  {i}. asked {server}")
    print(f"\n  {a.name} -> {addr}")


if __name__ == "__main__":
    main()
