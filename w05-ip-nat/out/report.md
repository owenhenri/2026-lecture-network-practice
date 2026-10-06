# Task 2: Network analysis

Student-entered analysis; raw collection evidence is in addresses.json.
Blank answers are marked TODO and must be completed before submission.

VPN/proxy status: I did not use a VPN or proxy during collection on either network.


## Network 1: mobile hotspot
Collected: 2026-10-06T04:26:40.868600+00:00
- **A1 Interface / IPv4 / mask:** Intel(R) Wi-Fi 6 AX201 160MHz, IPv4 10.188.69.162, subnet mask 255.255.255.0 (/24).
- **A2 Manual calculation:** The /24 mask reserves the first 24 bits for the network and the last 8 bits for hosts. IP AND mask gives network 10.188.69.0. Setting all host bits to 1 gives broadcast 10.188.69.255. Excluding the network and broadcast addresses, the usable range is 10.188.69.1 through 10.188.69.254, containing 254 addresses.
- **A2 Task 1 check:** `10.188.69.0/24` -> `('10.188.69.1', '10.188.69.254', '10.188.69.255')`
- **A2 Comparison:** Yes. The Task 1 result agrees with the manual calculation: first usable 10.188.69.1, last usable 10.188.69.254, and broadcast 10.188.69.255.
- **A3 Gateway:** The default gateway is 10.188.69.73, which is inside 10.188.69.0/24. The client must reach the gateway directly on the local link so that the gateway can forward packets to other networks.
- **A4 Externally observed IPv4:** 163.152.233.30
- **A5 NAT analysis:** 10.188.69.162 is an RFC 1918 private address, while 163.152.233.30 is public. I did not use a VPN or proxy during collection, so this difference indicates at least one NAT layer, but the exact number cannot be established from these addresses alone. Comparing the hotspot's cellular-side address with the externally observed address would help identify additional upstream NAT.

## Network 2: campus wifi
Collected: 2026-10-06T04:31:43.087345+00:00
- **A1 Interface / IPv4 / mask:** Intel(R) Wi-Fi 6 AX201 160MHz, IPv4 172.16.23.248, subnet mask 255.255.255.0 (/24).
- **A2 Manual calculation:** The /24 mask reserves the first 24 bits for the network and the last 8 bits for hosts. IP AND mask gives network 172.16.23.0. Setting all host bits to 1 gives broadcast 172.16.23.255. Excluding the network and broadcast addresses, the usable range is 172.16.23.1 through 172.16.23.254, containing 254 addresses.
- **A2 Task 1 check:** `172.16.23.0/24` -> `('172.16.23.1', '172.16.23.254', '172.16.23.255')`
- **A2 Comparison:** Yes. The Task 1 result agrees with the manual calculation: first usable 172.16.23.1, last usable 172.16.23.254, and broadcast 172.16.23.255.
- **A3 Gateway:** The default gateway is 172.16.23.1, which is inside 172.16.23.0/24. The client must reach the gateway directly on the local link so that the gateway can forward packets to other networks.
- **A4 Externally observed IPv4:** 163.152.233.23
- **A5 NAT analysis:** 172.16.23.248 is an RFC 1918 private address, while 163.152.233.23 is public. I did not use a VPN or proxy during collection, so this difference indicates at least one NAT layer, but the exact number cannot be established from these addresses alone. Comparing the gateway's external interface address with the externally observed address and examining the upstream network would help distinguish one layer from multiple layers.

## Part B: Two networks
The hotspot and campus local IPs were 10.188.69.162 and 172.16.23.248, their gateways were 10.188.69.73 and 172.16.23.1, and their public IPs were 163.152.233.30 and 163.152.233.23. Both masks were 255.255.255.0. Different DHCP configurations explain the different local IPs and gateways, while separate networks can use the same subnet size. The public IP also changed, indicating a different externally observed outgoing address. I did not use a VPN or proxy on either network. The reason the hotspot's public address was close to the campus address remains unexplained by the collected evidence; numerical similarity alone does not establish a shared network or gateway.

## Part C: DHCP
Capture file: out/dhcp.pcapng exists (contents not verified by this report generator).
- **C1 Evidence:** I captured out/dhcp.pcapng while connected to my mobile hotspot. Discover, Offer, Request, and ACK appear in frames 2, 3, 4, and 5, respectively, with transaction ID 0x550b4a98. The client is 10.188.69.162 and the DHCP server is 10.188.69.73, matching the hotspot records. Frame 1 is a separate DHCP Release. The capture contains a complete DORA exchange.
- **C2 Discover:** The Discover in frame 2 uses source IPv4 0.0.0.0 and destination 255.255.255.255. The client has no assigned IPv4 address yet, so it uses 0.0.0.0 as its source. It broadcasts to discover available DHCP servers without knowing their addresses.
- **C3 Lease:** The Offer in frame 3 contains DHCP option 51, IP Address Lease Time, with a value of 3600 seconds, or one hour. The ACK in frame 5 contains 3599 seconds.
- **C4 Ack:** The ACK in frame 5 is unicast from 10.188.69.73 to 10.188.69.162. The server now knows the selected client IP and its hardware address, allowing unicast delivery when the client can receive it before completing configuration. ACK messages may also be broadcast depending on the client and exchange.
- **Fallback renewal:** N/A

## Task 2 observations
I used no VPN or proxy on either network. Both networks used private local IPs that differed from their public IPs, indicating at least one NAT layer, but the exact number of layers is unknown. / The local IP, gateway, and public IP changed between networks, while the /24 mask stayed the same. / In the mobile hotspot capture, Discover used source 0.0.0.0 because the client had no assigned IP and broadcast to 255.255.255.255 to discover DHCP servers.
