# Task 2 DNS measurement

Networks: default, local.

## Rule and classification

The rule compares the final CNAME target's simplified zone with the original site's zone. A changed zone is classified as third party. The audited third-party column corrects known ownership exceptions. DNS suffixes alone cannot prove ownership or identify an exact service.

| Site | Chain length | Final zone | Third party? | Rule's verdict | CDN-hosted? | Different A set? |
|---|---:|---|---|---|---|---|
| www.microsoft.com | 2 | akamaiedge.net | yes | third party | yes | yes |
| www.netflix.com | 1 | netflix.com | no | same zone | yes | no |
| www.adobe.com | 2 | akamai.net | yes | third party | yes | yes |
| www.cnn.com | 1 | fastly.net | yes | third party | yes | yes |
| www.apple.com | 3 | akamaiedge.net | yes | third party | yes | yes |
| www.korea.ac.kr | 0 | korea.ac.kr | no | same zone | no | no |
| www.stanford.edu | 1 | netlifyglobalcdn.com | yes | third party | yes | no |
| www.bbc.co.uk | 2 | fastly.net | yes | third party | yes | yes |
| www.spotify.com | 1 | fastly.net | yes | third party | yes | yes |
| www.github.com | 1 | github.com | no | same zone | no | yes |
| www.wikipedia.org | 1 | wikimedia.org | no | third party | yes | no |
| www.nytimes.com | 3 | fastly.net | yes | third party | yes | yes |

## Steering

7 of 10 sites answered differently to a different resolver or network.
Only successful A answers are compared as sets. A difference demonstrates resolver-dependent answers, but does not by itself prove that an address is geographically nearer.

## Rule failures

The rule misses Netflix's own CDN because the chain remains under netflix.com. It also calls Wikipedia→Wikimedia third party because the zones differ, although both belong to the Wikimedia organization. These are false conclusions from suffix comparison alone.

## Raw address sets

### default (2026-09-19T07:19:12.636328+00:00)

- www.microsoft.com: system=[104.94.218.45]; google=[104.94.218.45]; quad9=[184.28.10.89]
- www.netflix.com: system=[207.45.72.1, 207.45.73.1]; google=[207.45.72.1, 207.45.73.1]; quad9=[207.45.72.1, 207.45.73.1]
- www.adobe.com: system=[23.32.4.146, 23.32.4.187, 23.32.4.209]; google=[23.32.4.105, 23.32.4.107, 23.32.4.136, 23.32.4.9, 23.32.4.99]; quad9=[2.22.234.137, 2.22.234.155]
- www.cnn.com: system=[146.75.51.5]; google=[151.101.131.5, 151.101.195.5, 151.101.3.5, 151.101.67.5]; quad9=[151.101.131.5, 151.101.195.5, 151.101.3.5, 151.101.67.5]
- www.apple.com: system=[104.94.216.37]; google=[104.94.216.37]; quad9=[184.28.3.43]
- www.korea.ac.kr: system=[163.152.6.10]; google=[163.152.6.10]; quad9=[163.152.6.10]
- www.stanford.edu: system=[15.197.167.90, 3.33.186.135]; google=[15.197.167.90, 3.33.186.135]; quad9=[15.197.167.90, 3.33.186.135]
- www.bbc.co.uk: system=[146.75.48.81]; google=[151.101.0.81, 151.101.128.81, 151.101.192.81, 151.101.64.81]; quad9=[151.101.0.81, 151.101.128.81, 151.101.192.81, 151.101.64.81]
- www.spotify.com: system=[146.75.51.42]; google=[151.101.131.42, 151.101.195.42, 151.101.3.42, 151.101.67.42]; quad9=[151.101.131.42, 151.101.195.42, 151.101.3.42, 151.101.67.42]
- www.github.com: system=[20.200.245.247]; google=[20.200.245.247]; quad9=[20.27.177.113]
- www.wikipedia.org: system=[103.102.166.224]; google=[103.102.166.224]; quad9=[103.102.166.224]
- www.nytimes.com: system=[146.75.49.164]; google=[151.101.1.164, 151.101.129.164, 151.101.193.164, 151.101.65.164]; quad9=[151.101.1.164, 151.101.129.164, 151.101.193.164, 151.101.65.164]

### local (2026-09-19T08:08:44.914807+00:00)

- www.microsoft.com: system=[104.94.218.45]; google=[104.94.218.45]; quad9=[23.0.206.100]
- www.netflix.com: system=[207.45.72.1, 207.45.73.1]; google=[207.45.72.1, 207.45.73.1]; quad9=[207.45.72.1, 207.45.73.1]
- www.adobe.com: system=[114.108.166.34, 114.108.166.72, 23.32.4.104, 23.32.4.105, 23.32.4.107, 23.32.4.113, 23.32.4.115, 23.32.4.75, 23.32.4.80, 23.32.4.83, 23.32.4.88, 23.32.4.89, 23.32.4.90, 23.32.4.91, 23.32.4.96, 23.32.4.99]; google=[23.59.72.32, 23.59.72.58]; quad9=[2.22.234.100, 2.22.234.102, 2.22.234.103, 2.22.234.108, 2.22.234.113, 2.22.234.120]
- www.cnn.com: system=[146.75.51.5]; google=[151.101.131.5, 151.101.195.5, 151.101.3.5, 151.101.67.5]; quad9=[151.101.131.5, 151.101.195.5, 151.101.3.5, 151.101.67.5]
- www.apple.com: system=[104.94.216.37]; google=[184.28.183.49]; quad9=[184.31.228.249]
- www.korea.ac.kr: system=[163.152.6.10]; google=[163.152.6.10]; quad9=[163.152.6.10]
- www.stanford.edu: system=[15.197.167.90, 3.33.186.135]; google=[15.197.167.90, 3.33.186.135]; quad9=[15.197.167.90, 3.33.186.135]
- www.bbc.co.uk: system=[146.75.48.81]; google=[151.101.0.81, 151.101.128.81, 151.101.192.81, 151.101.64.81]; quad9=[151.101.0.81, 151.101.128.81, 151.101.192.81, 151.101.64.81]
- www.spotify.com: system=[146.75.51.42]; google=[151.101.131.42, 151.101.195.42, 151.101.3.42, 151.101.67.42]; quad9=[151.101.131.42, 151.101.195.42, 151.101.3.42, 151.101.67.42]
- www.github.com: system=[20.200.245.247]; google=[20.200.245.247]; quad9=[20.27.177.113]
- www.wikipedia.org: system=[103.102.166.224]; google=[103.102.166.224]; quad9=[103.102.166.224]
- www.nytimes.com: system=[146.75.49.164]; google=[151.101.1.164, 151.101.129.164, 151.101.193.164, 151.101.65.164]; quad9=[151.101.1.164, 151.101.129.164, 151.101.193.164, 151.101.65.164]

## Lookup errors

None.
