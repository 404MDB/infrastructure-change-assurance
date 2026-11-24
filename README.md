# Infrastructure Change Assurance

A project developing dependency-aware configuration validation
and safe deployment.

## Current implementation
- Configurable TCP port and HTTP baseline checks.
- Timestamped JSON baseline reports.
- Reusable isolated network lab.
- Automated testing of a known-bad firewall candidate.
- Candidate cleanup and HTTP recovery verification.

## Environment

### Hosted service
- debian-control: 192.168.56.10 — runs the checker.
- debian-server: 192.168.56.20 — hosts Nginx.

### Isolated test network
Both namespaces run on debian-control:
- ica-client: 10.200.1.1
- ica-lab: 10.200.1.2

## Baseline checker

Run from the project directory:

```bash
python3 src/baseline.py
```

Edit config/target.json to configure the target IP, ports,
HTTP path, expected status and timeout.

### Exit codes
- 0: Both checks passed.
- 1: A service check failed.
- 2: Configuration error.
- 3: Report could not be written.

## Reports
Each valid-config baseline run saves a timestamped JSON file
in reports/. Reports contain UTC timestamps, configuration,
check results and durations.

Generated reports are excluded from Git.

## Isolated firewall experiment

Create the lab after reboot:

```bash
sudo bash scripts/lab-setup.sh
```

The setup script refuses to overwrite an existing lab.

Start the HTTP fixture in one terminal:

```bash
sudo ip netns exec ica-lab python3 -m http.server 80 \
  --bind 10.200.1.2 --directory "$PWD/tests/fixtures/web"
```

Keep it running. In another terminal, from the project directory:

```bash
sudo bash scripts/test-candidate.sh
```

The runner:
1. Verifies baseline HTTP access.
2. Validates the candidate's syntax.
3. Applies the candidate inside ica-lab.
4. Checks HTTP access and displays rule counters.
5. Removes the candidate table.
6. Verifies HTTP recovery.

The known-bad block-http.nft candidate should produce
CANDIDATE BLOCKED and exit code 1 after successful recovery.

## Verified experiments
- Stopping Nginx produces a failed baseline check.
- Restoring Nginx restores a passing baseline.
- Blocking TCP port 80 inside the lab causes an HTTP timeout.
- Removing the candidate table restores HTTP 200.

## Current limitations
- TCP port 22 reachability does not verify SSH authentication.
- HTTP checks do not verify page content or database health.
- Candidate testing currently uses one reviewed firewall fixture.
- Results apply to the modeled lab, not full production equivalence.
- Dependency analysis and live deployment rollback are not implemented.
- Cleanup traps cannot handle power loss or SIGKILL.
