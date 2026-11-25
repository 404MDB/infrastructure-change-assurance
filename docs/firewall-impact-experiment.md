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

## Unhealthy baseline safeguard

With the HTTP fixture stopped:
- The runner reported an unhealthy baseline.
- The candidate was not applied.
- The namespace ruleset remained empty.
- The wrapper returned exit code 2 and saved a report.

After restarting the HTTP fixture:
- The allow-http candidate passed.
- Cleanup and recovery checks succeeded.
- The wrapper returned exit code 0.

This prevents an existing outage from being blamed on the candidate.

## Invalid configuration test
The invalid-syntax fixture deliberately contains an unclosed table.
The baseline passed, but nftables syntax validation failed.
Application, impact testing, cleanup and recovery were not reached.
The lab ruleset remained empty.

The JSON report recorded decision "error", runner exit code 2,
and no event parsing errors.

## Reporter decision tests
The event evaluation logic is tested independently of the firewall lab.

Nine automated tests cover:
- Successful and disruptive candidates.
- Missing evidence and missing recovery.
- Failed cleanup or recovery.
- Exit codes that contradict stage results.
- Duplicate, out-of-order and malformed events.

Run from the repository root:
```bash
python3 -m unittest discover -s tests -p 'test_candidate_report.py' -v
```

These tests require no sudo or network namespaces.
All nine tests passed.
