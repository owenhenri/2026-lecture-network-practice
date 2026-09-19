#!/usr/bin/env python3
"""Measure CNAME chains and resolver-dependent DNS answers for Task 2."""
import argparse
import datetime as dt
import json
import os
import shutil
import subprocess

try:
    import dns.exception
    import dns.resolver
except ImportError:                         # The course Docker image provides dig.
    dns = None

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
DATA = os.path.join(OUT, "chains.json")
SITES = [
    "www.microsoft.com", "www.netflix.com", "www.adobe.com", "www.cnn.com",
    "www.apple.com", "www.korea.ac.kr", "www.stanford.edu", "www.bbc.co.uk",
    "www.spotify.com", "www.github.com", "www.wikipedia.org", "www.nytimes.com",
]
RESOLVERS = {"system": None, "google": "8.8.8.8", "quad9": "9.9.9.9"}
# Manual audit of facts that a suffix-only rule cannot discover.
KNOWN = {
    "www.netflix.com": {"third_party": False, "cdn": True,
                         "reason": "Netflix operates its own CDN."},
    "www.wikipedia.org": {"third_party": False, "cdn": True,
                           "reason": "Wikipedia and Wikimedia are operated by the same organization."},
    "www.korea.ac.kr": {"third_party": False, "cdn": False,
                         "reason": "This measurement shows no CNAME evidence of a CDN."},
}


def zone(name):
    """Return a deliberately simple registrable-zone approximation."""
    labels = name.rstrip(".").lower().split(".")
    if len(labels) >= 3 and labels[-2:] in (["co", "uk"], ["ac", "kr"]):
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def lookup(name, record_type, server=None):
    """Return sorted DNS values, using dnspython or the course image's dig."""
    if dns is not None:
        resolver = dns.resolver.Resolver(configure=server is None)
        if server:
            resolver.nameservers = [server]
        resolver.timeout, resolver.lifetime = 2, 4
        try:
            answer = resolver.resolve(name, record_type, raise_on_no_answer=False)
            return sorted({str(item).rstrip(".").lower() for item in (answer.rrset or [])})
        except (dns.exception.DNSException, OSError) as exc:
            raise RuntimeError(f"{type(exc).__name__}: {exc}") from exc

    if not shutil.which("dig"):
        raise RuntimeError("Neither dnspython nor dig is available")
    command = ["dig"]
    if server:
        command.append(f"@{server}")
    command += ["+short", "+time=2", "+tries=1", name, record_type]
    result = subprocess.run(command, capture_output=True, text=True, timeout=6)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"dig exited {result.returncode}")
    return sorted({line.strip().rstrip(".").lower()
                   for line in result.stdout.splitlines() if line.strip()})


def measure(site, server):
    chain, seen, error = [site], {site}, None
    for _ in range(20):
        try:
            targets = lookup(chain[-1], "CNAME", server)
        except RuntimeError as exc:
            error = str(exc)
            break
        if not targets:
            break
        target = targets[0]
        if target in seen:
            error = f"CNAME loop at {target}"
            break
        chain.append(target)
        seen.add(target)
    else:
        error = "CNAME chain exceeded 20 hops"
    try:
        addresses = lookup(site, "A", server)
    except RuntimeError as exc:
        addresses = []
        error = "; ".join(filter(None, [error, str(exc)]))
    return {"chain": chain, "addresses": addresses, "error": error}


def load_data():
    if not os.path.exists(DATA):
        return {site: {"networks": {}} for site in SITES}
    with open(DATA, encoding="utf-8") as handle:
        old = json.load(handle)
    # Migrate the earlier metadata-first format so the file has exactly 12
    # top-level site entries, as the task and harness output imply.
    if "networks" in old:
        converted = {site: {"networks": {}} for site in SITES}
        for network, batch in old["networks"].items():
            for site in SITES:
                converted[site]["networks"][network] = {
                    "collected_at_utc": batch["collected_at_utc"],
                    "resolvers": batch["sites"][site],
                }
        return converted
    return {site: old.get(site, {"networks": {}}) for site in SITES}


def collect(network):
    os.makedirs(OUT, exist_ok=True)
    data = load_data()
    collected_at = dt.datetime.now(dt.timezone.utc).isoformat()
    for site in SITES:
        results = {label: measure(site, server) for label, server in RESOLVERS.items()}
        data[site].setdefault("networks", {})[network] = {
            "collected_at_utc": collected_at, "resolvers": results}
        print(f"{site}: " + ", ".join(
            f"{label}={len(value['addresses'])} A" for label, value in results.items()))
    with open(DATA, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    print(f"Saved {DATA} for network {network!r}")


def report():
    data = load_data()
    network_names = list(dict.fromkeys(
        network for site in SITES for network in data[site]["networks"]))
    if not network_names:
        raise RuntimeError("No measurements found; run --collect first")
    primary_network = network_names[0]
    rows, errors = [], []
    cdn_count = changed_count = 0
    for site in SITES:
        networks = data[site]["networks"]
        if primary_network not in networks:
            primary_network = next(iter(networks))
        primary = networks[primary_network]["resolvers"]["system"]
        chain, final_zone = primary["chain"], zone(primary["chain"][-1])
        rule_third = final_zone != zone(site)
        audit = KNOWN.get(site, {})
        third_party = audit.get("third_party", rule_third)
        cdn = audit.get("cdn", rule_third)
        samples = [result for batch in networks.values()
                   for result in batch["resolvers"].values()]
        sets = [set(result["addresses"]) for result in samples if result["addresses"]]
        differs = len(sets) >= 2 and any(value != sets[0] for value in sets[1:])
        if cdn:
            cdn_count += 1
            changed_count += int(differs)
        rows.append(f"| {site} | {len(chain) - 1} | {final_zone} | "
                    f"{'yes' if third_party else 'no'} | "
                    f"{'third party' if rule_third else 'same zone'} | "
                    f"{'yes' if cdn else 'no'} | "
                    f"{'yes' if differs else 'no' if len(sets) >= 2 else 'unknown'} |")
        for network, batch in networks.items():
            for resolver_name, result in batch["resolvers"].items():
                if result["error"]:
                    errors.append(f"- {site}, {network}/{resolver_name}: {result['error']}")

    lines = [
        "# Task 2 DNS measurement", "", f"Networks: {', '.join(network_names)}.", "",
        "## Rule and classification", "",
        "The rule compares the final CNAME target's simplified zone with the original site's zone. "
        "A changed zone is classified as third party. The audited third-party column corrects known "
        "ownership exceptions. DNS suffixes alone cannot prove ownership or identify an exact service.", "",
        "| Site | Chain length | Final zone | Third party? | Rule's verdict | CDN-hosted? | Different A set? |",
        "|---|---:|---|---|---|---|---|", *rows, "", "## Steering", "",
        f"{changed_count} of {cdn_count} sites answered differently to a different resolver or network.",
        "Only successful A answers are compared as sets. A difference demonstrates resolver-dependent "
        "answers, but does not by itself prove that an address is geographically nearer.", "",
        "## Rule failures", "",
        "The rule misses Netflix's own CDN because the chain remains under netflix.com. It also calls "
        "Wikipedia→Wikimedia third party because the zones differ, although both belong to the Wikimedia "
        "organization. These are false conclusions from suffix comparison alone.", "",
    ]
    if len(network_names) < 2:
        lines += ["Only one physical network is recorded. Run collection again with a new label on the "
                  "second network, for example `--collect --network phone`, to satisfy B3.", ""]
    lines += ["## Raw address sets", ""]
    for network in network_names:
        timestamps = [data[s]["networks"][network]["collected_at_utc"]
                      for s in SITES if network in data[s]["networks"]]
        lines += [f"### {network} ({timestamps[0]})", ""]
        for site in SITES:
            if network not in data[site]["networks"]:
                continue
            values = data[site]["networks"][network]["resolvers"]
            lines.append(f"- {site}: " + "; ".join(
                f"{name}=[{', '.join(result['addresses'])}]"
                for name, result in values.items()))
        lines.append("")
    lines += ["## Lookup errors", "", *(errors or ["None."]), ""]
    path = os.path.join(OUT, "report.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print(f"Saved {path}; {changed_count} of {cdn_count} CDN-hosted sites differed")


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--collect", action="store_true")
    mode.add_argument("--report", action="store_true")
    parser.add_argument("--network", default="local", help="label for the physical network")
    args = parser.parse_args()
    collect(args.network) if args.collect else report()


if __name__ == "__main__":
    main()
