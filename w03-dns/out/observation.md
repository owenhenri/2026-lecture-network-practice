# Week 3 DNS observations

Task 1: The capture confirms a normal iterative DNS resolution path from the root → .kr → korea.ac.kr. Since all required glue records were present, there were no additional queries to obtain nameserver addresses.

Task 2: The packet structure, transaction IDs, DNS sections, and response sizes were confirmed. Although different CDN addresses were observed depending on the resolver, this alone does not prove that the resolver selects the nearest replica.

Task 3: The baseline’s fixed 60-second cache creates two problems: stale responses and unnecessary re-queries. YourCache uses the actual TTL, resulting in zero stale responses, 275 upstream queries, a 72.5% hit rate, and a completion time of 5.5 seconds. The 275 upstream queries represent the minimum possible number of upstream queries for this workload.