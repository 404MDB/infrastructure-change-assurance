# Isolated Firewall Impact Experiment

## Topology
ica-client: 10.200.1.1/24
ica-lab: 10.200.1.2/24
Connected through a veth pair on debian-control.

## Observed results
1. HTTP was accessible before applying the candidate.
2. A valid nftables rule dropping TCP port 80 caused a curl timeout.
3. The drop counter recorded 6 packets and 360 bytes.
4. Removing the candidate table restored HTTP 200.

## Scope
This verifies behavior in an isolated lab.
It does not prove that a configuration is safe for production.

## Automated verification
| Candidate | Baseline | After change | Recovery | Exit |
|---|---|---|---|---|
| allow-http | 200 | 200 | 200 | 0 |
| block-http | 200 | Timeout | 200 | 1 |
