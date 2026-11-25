# Infrastructure Change Assurance

A project developing dependency-aware configuration validation
and safe deployment.

## Current implementation
- Configurable TCP port and HTTP baseline checks.
- Timestamped JSON baseline reports.
- Reusable isolated network lab.
- Automated testing of two reviewed firewall candidates.
- Candidate cleanup and HTTP recovery verification.
- Candidate reports with validated, structured stage results.

## Environment

### Hosted service
- debian-control: 192.168.56.10 — runs the checker.
- debian-server: 192.168.56.20 — hosts Nginx.

### Isolated test network
Both namespaces run on debian-control:
- ica-client: 10.200.1.1
- ica-lab: 10.200.1.2

The namespaces connect through a veth pair.

## Baseline checks

```bash
python3 src/baseline.py
```

Edit config/target.json to configure the target IPv4 address,
ports, HTTP path, expected status and timeout.

### Baseline exit codes
- 0: Both checks passed.
- 1: A service check failed.
- 2: Configuration error.
- 3: Report could not be written.

Baseline reports use schema version 1.

## Isolated lab setup

Run after reboot:

```bash
sudo bash scripts/lab-setup.sh
```

The script refuses to overwrite existing lab namespaces or links.

Start the HTTP fixture from the project directory:

```bash
sudo ip netns exec ica-lab python3 -m http.server 80 \
  --bind 10.200.1.2 --directory "$PWD/tests/fixtures/web"
```

Leave this running while testing from a second terminal.

## Candidate testing

Run as the regular user:

```bash
python3 src/candidate_report.py allow-http
python3 src/candidate_report.py block-http
```

Only the child firewall runner uses sudo.

### Experiment stages
1. Check baseline HTTP access.
2. Validate candidate syntax.
3. Apply candidate inside ica-lab.
4. Check HTTP access.
5. Remove the candidate table.
6. Verify HTTP recovery.

### Candidate report exit codes
- 0: Required HTTP check preserved; recovery verified.
- 1: Required HTTP check failed; recovery verified.
- 2: Execution, baseline or event-validation error.
- 3: Report could not be written.

The report also preserves the raw runner exit code.

## Candidate reports

Candidate reports use schema version 2 and contain:
- Candidate name and SHA-256 fingerprint.
- UTC start and finish timestamps.
- Decision and runner exit code.
- Structured stage results.
- Event-validation errors.
- Captured standard output and errors.

Stage statuses are passed, failed or not_run.
not_run means no valid event was observed.

Decisions use validated stage events and the runner exit code.
Missing, malformed or inconsistent events produce an error decision.

Reports are saved in reports/ and excluded from Git.
The candidate fingerprint supports correlation; it is not an
authenticity guarantee.

## Verified experiments

| Scenario | Outcome | Wrapper exit |
|---|---|---|
| allow-http candidate | HTTP preserved; recovery verified | 0 |
| block-http candidate | HTTP blocked; recovery verified | 1 |
| HTTP unavailable before testing | Candidate not applied | 2 |

Additional baseline checks were verified by stopping and
restarting Nginx on debian-server.

## Current limitations
- TCP port 22 reachability does not verify SSH authentication.
- HTTP checks do not verify page content or database health.
- Candidate testing covers two reviewed HTTP-only fixtures.
- Results apply to the isolated model, not production equivalence.
- Dependency analysis and live deployment rollback are not implemented.
- Preflight errors and emergency cleanup are not fully structured.
- Cleanup traps cannot handle power loss or SIGKILL.
- Concurrent experiment runs are not supported.
