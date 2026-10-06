#!/usr/bin/env python3
"""Week 5 · Task 2 — Where exactly are you on the internet?

Textbook §4.3.2 (addressing, DHCP) and §4.3.3 (NAT).

This is the hands-on task. It asks what address your machine has, what address
the rest of the world sees, and why those two are usually different.

    python3 task2_myaddr.py --collect "campus wifi"
    python3 task2_myaddr.py --report      # your analysis

Run it on **two networks**. Campus Wi-Fi and phone tethering behave differently
here, and the difference is the lesson.
"""
import argparse, json, os, platform, subprocess
from datetime import datetime, timezone
from ipaddress import IPv4Address

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def sh(*cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                errors="replace", timeout=15)
        if result.returncode:
            return f"<failed: exit {result.returncode}: {result.stderr.strip()}>"
        return result.stdout
    except Exception as e:
        return f"<failed: {e}>"


def local_facts():
    """Raw output only. Reading it is your job, not this script's."""
    osname = platform.system()
    if osname == "Darwin":
        return {"os": osname,
                "ifconfig": sh("ifconfig"),
                "route": sh("route", "-n", "get", "default"),
                "dns": sh("scutil", "--dns")}
    if osname == "Linux":
        return {"os": osname,
                "ip_addr": sh("ip", "addr"),
                "ip_route": sh("ip", "route"),
                "dns": sh("cat", "/etc/resolv.conf")}
    # ipconfig/route use Windows' display language. PowerShell's selected
    # property names provide English headings without changing system settings.
    def powershell(command):
        return sh("powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                  "[Console]::OutputEncoding = [System.Text.Encoding]::ASCII; "
                  + command)

    return {"os": osname,
            "ipconfig": powershell(
                "Get-CimInstance Win32_NetworkAdapterConfiguration "
                "-Filter 'IPEnabled=True' | "
                "Select-Object Description, IPAddress, IPSubnet, DefaultIPGateway, "
                "DHCPEnabled, DHCPServer, DHCPLeaseObtained, DHCPLeaseExpires, "
                "DNSServerSearchOrder | Format-List | Out-String -Width 240"),
            "route": powershell(
                "Get-NetRoute -AddressFamily IPv4 | "
                "Select-Object DestinationPrefix, NextHop, InterfaceIndex, RouteMetric | "
                "Format-Table -AutoSize | Out-String -Width 240")}


def public_address():
    """What a server on the outside says your address is."""
    out = sh("curl", "-4", "-f", "-sS", "--max-time", "10", "https://api.ipify.org")
    try:
        return str(IPv4Address(out.strip()))
    except ValueError:
        print(f"  Public IPv4 lookup failed: {out.strip() or 'empty response'}")
        return None


def load_records():
    path = os.path.join(OUT, "addresses.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as source:
        records = json.load(source)
    if not isinstance(records, list) or any(
            not isinstance(r, dict) or not isinstance(r.get("label"), str)
            or not r["label"].strip() or not isinstance(r.get("local"), dict)
            for r in records):
        raise ValueError("addresses.json must contain labelled collection records")
    return records


def collect(label):
    label = label.strip()
    if not label:
        raise ValueError("network label cannot be empty")
    os.makedirs(OUT, exist_ok=True)
    all_records = load_records()
    record = {"label": label, "local": local_facts(), "public": public_address(),
              "collected_at": datetime.now(timezone.utc).isoformat()}
    path = os.path.join(OUT, "addresses.json")
    all_records.append(record)
    with open(path, "w", encoding="utf-8") as destination:
        # Escape non-ASCII text so readers using Windows' default encoding
        # can load the JSON too. json.load restores the original characters.
        json.dump(all_records, destination, indent=2, ensure_ascii=True)
    print(f"  public address seen from outside: {record['public']}")
    print(f"  -> out/addresses.json  ({len(all_records)} record(s))")
    print("\n  Now read the raw output yourself and answer the questions in task2.md.")
    print("  The script deliberately does not parse it for you.")


def report():
    """Guide the student's analysis without parsing the raw interface output."""
    from task1_forward import network_range

    records = load_records()
    if not records:
        raise ValueError('collect a network first: --collect "network label"')
    path = os.path.join(OUT, "report.md")
    if os.path.exists(path):
        raise FileExistsError("out/report.md already exists; edit it directly or rename it first")

    def ask(question):
        answer = input(question + "\n> ").strip()
        return answer or "TODO: not answered"

    # Answers are supplied by the student; blank answers stay visibly incomplete.
    lines = ["# Task 2: Network analysis", "",
             "Student-entered analysis; raw collection evidence is in addresses.json.",
             "Blank answers are marked TODO and must be completed before submission.", ""]
    if len({r["label"] for r in records}) < 2:
        lines.append("TODO: collect a second real network, or document the classmate fallback below.")
    for index, record in enumerate(records, 1):
        print(f"\nNetwork {index}: {record['label']}")
        print(json.dumps(record["local"], indent=2, ensure_ascii=False))
        lines.extend(["", f"## Network {index}: {record['label']}",
                      f"Collected: {record.get('collected_at', 'not recorded')}"])
        for title, question in [
            ("A1 Interface / IPv4 / mask", "Read the raw output: active interface, IPv4 address, and subnet mask?"),
            ("A2 Manual calculation", "Calculate by hand: network, first/last usable, broadcast, and calculation steps?"),
        ]:
            lines.append(f"- **{title}:** {ask(question)}")
        while True:
            cidr = input("Network CIDR from your manual calculation (blank to leave TODO):\n> ").strip()
            if not cidr:
                lines.append("- **A2 Task 1 check:** TODO: supply the network CIDR and check the range.")
                break
            try:
                computed = network_range(cidr)
            except ValueError as error:
                print(f"Invalid network: {error}")
                continue
            print(f"Task 1 (first usable, last usable, broadcast): {computed}")
            lines.append(f"- **A2 Task 1 check:** `{cidr}` -> `{computed}`")
            lines.append("- **A2 Comparison:** " + ask("Does this agree with your hand calculation? Explain any difference."))
            break
        lines.append("- **A3 Gateway:** " + ask("Default gateway? Is it within your subnet, and why must it be reachable on this link?"))
        public = record.get("public")
        lines.append(f"- **A4 Externally observed IPv4:** {public or 'TODO: lookup failed; collect again'}")
        print(f"Externally observed IPv4: {public}")
        lines.append("- **A5 NAT analysis:** " + ask(
            "Is the local address RFC 1918 private, and is the observed address public? "
            "Explain differences, evidence for NAT layers, and how you would distinguish one from two. "
            "Do not infer an exact count from address differences alone; record uncertainties or VPN/proxy use."))

    lines.extend(["", "## Part B: Two networks"])
    lines.append(ask("B1-B3: Compare local IP, mask, gateway, and public IP across two genuinely different networks. "
                     "What changed or stayed the same, and why? If using a classmate's data, give their name, "
                     "measurements, and why a second network was unavailable."))
    lines.extend(["", "## Part C: DHCP"])
    capture = os.path.join(OUT, "dhcp.pcapng")
    lines.append("Capture file: " + ("out/dhcp.pcapng exists (contents not verified by this report generator)."
                                    if os.path.exists(capture) else "TODO: out/dhcp.pcapng is missing."))
    for title, question in [
        ("C1 Evidence", "Own capture or official fallback trace? Give source/path and frame numbers for Discover, Offer, Request, Ack from one exchange. Explain any capture limitation."),
        ("C2 Discover", "Observed Discover source and destination IPv4 addresses? Explain why these addresses are used before the client has an address."),
        ("C3 Lease", "Lease time offered by the server (seconds), and the frame/option where you read it?"),
        ("C4 Ack", "Observed Ack destination and broadcast/unicast behavior? Explain what allows an Ack to be unicast; distinguish the observed behavior from what is possible."),
        ("Fallback renewal", "If using the official trace, how long is the lease and what happens halfway through it? Otherwise enter N/A."),
    ]:
        lines.append(f"- **{title}:** {ask(question)}")

    summary = ask("Write 2-3 lines of observations (separate with ' / '): NAT evidence; changes between networks; Discover source and why.")
    lines.extend(["", "## Task 2 observations", summary, ""])
    # Exclusive creation protects an existing report, including on interrupted reruns.
    with open(path, "x", encoding="utf-8") as destination:
        destination.write("\n".join(lines))
    observation_path = os.path.join(OUT, "observation.md")
    with open(observation_path, "a", encoding="utf-8") as destination:
        destination.write("\n\n# Task 2\n\n" + summary + "\n")
    print("  -> out/report.md and Task 2 observations appended to out/observation.md")
    print("  Review TODOs, verify capture evidence, then run: py test_tasks.py --task 2")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    actions = p.add_mutually_exclusive_group()
    actions.add_argument("--collect", metavar="LABEL",
                   help='where you are, e.g. "campus wifi"')
    actions.add_argument("--report", action="store_true",
                         help="interactively write your analysis from collected records")
    a = p.parse_args()
    try:
        if a.collect is not None:
            collect(a.collect)
        elif a.report:
            report()
        else:
            p.print_help()
    except (OSError, ValueError, EOFError, KeyboardInterrupt) as error:
        p.exit(1, f"Task 2: {error or 'input cancelled; report not completed'}\n")
