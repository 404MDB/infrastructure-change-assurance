# Infrastructure Change Assurance

A project developing dependency-aware configuration validation
and safe deployment.

## Current implementation

- Configurable TCP port and HTTP baseline checks.
- Timestamped JSON baseline reports.
- Reusable isolated network lab.
- Candidate validation against required HTTP services on ports 80 and 8080.
- Three HTTP behavior fixtures and one invalid-syntax fixture.
- Candidate cleanup and service recovery verification after applied changes.
- JSON reports with structured stage and per-service results.
- Validation of service evidence against stage outcomes.
- Seventeen unit tests.
- GitHub Actions CI on pushes and pull requests.

## Environment

### Hosted service

- debian-control: 192.168.56.10 — runs the checker.
- debian-server: 192.168.56.20 — hosts Nginx.

### Isolated test network

Both namespaces run on debian-control:

- ica-client: 10.200.1.1
- ica-lab: 10.200.1.2

The namespaces connect through a veth pair.

Two HTTP listeners on ica-lab model required service connections:

| Service | Address | Expected response |
|---|---|---|
| Website fixture | 10.200.1.2:80 | HTTP 200 |
| Simulated internal API fixture | 10.200.1.2:8080 | HTTP 200 |

Both listeners serve static test content.
An actual application-to-API dependency is not implemented yet.

## Baseline checks

Run from the repository root:

```bash
python3 src/baseline.py
```

Edit `config/target.json` to configure the target IPv4 address,
ports, HTTP path, expected status and timeout.

This configuration controls the standalone baseline checker.
The isolated candidate runner currently uses fixed lab addresses
and required ports.

### Baseline exit codes

- 0: Both checks passed.
- 1: A service check failed.
- 2: Configuration error.
- 3: Report could not be written.

Baseline reports use schema version 1.

## Isolated lab setup

Run on debian-control after reboot:

```bash
sudo bash scripts/lab-setup.sh
```

The script refuses to overwrite existing lab namespaces or links.
Namespaces must be recreated after reboot.

Start each HTTP listener in a separate terminal.
Run both commands from the repository root.

### Terminal 1: port 80

```bash
sudo ip netns exec ica-lab python3 -m http.server 80 --bind 10.200.1.2 --directory "$PWD/tests/fixtures/web"
```

### Terminal 2: port 8080

```bash
sudo ip netns exec ica-lab python3 -m http.server 8080 --bind 10.200.1.2 --directory "$PWD/tests/fixtures/web"
```

Leave both listeners running while testing from a third terminal.

## Candidate testing

Run from the repository root as the regular user:

```bash
python3 src/candidate_report.py allow-http
python3 src/candidate_report.py allow-required-services
python3 src/candidate_report.py block-http
python3 src/candidate_report.py invalid-syntax
```

Run one experiment at a time.
Only the child firewall runner uses sudo.

### Candidate fixtures

| Candidate | Behavior |
|---|---|
| allow-http | Allows port 80 but blocks required port 8080 |
| allow-required-services | Allows both required ports: 80 and 8080 |
| block-http | Drops connections to port 80 |
| invalid-syntax | Contains an incomplete table declaration |

These are reviewed lab fixtures, not production firewall configurations.

The allow-http fixture passed the earlier port-80-only check.
With both services required, it is correctly blocked.

### Experiment stages

1. Check baseline HTTP access to both required services.
2. Validate candidate syntax.
3. Apply candidate inside ica-lab.
4. Check both required services while the candidate is active.
5. Remove the candidate table.
6. Verify HTTP recovery for both services.

An unhealthy baseline or invalid syntax stops the experiment before
candidate application.

### Candidate report exit codes

- 0: Both required services preserved; recovery verified.
- 1: At least one required service failed; recovery verified.
- 2: Execution, baseline, syntax or evidence-validation error.
- 3: Report could not be written.

The report also preserves the raw runner exit code.
Runner cleanup or recovery failures produce an error decision;
their raw exit code is retained in the report.

## Candidate reports

Candidate reports use schema version 3 and contain:

- Candidate name and SHA-256 fingerprint.
- UTC start and finish timestamps.
- Decision and runner exit code.
- Structured stage results.
- Per-service probe results.
- Stage-event and service-validation errors.
- Captured standard output and errors.

### Stage results

Stage statuses are `passed`, `failed` or `not_run`.
`not_run` means no valid event was observed for that stage.

### Service results

Each service result records:

- Phase: baseline, impact or recovery.
- Destination port.
- Passed or failed status.
- HTTP response status.
- curl exit code.

When curl fails, the HTTP status is recorded as `null`.
For example, a connection timeout produces curl exit code 28.

The parser checks required results, duplicate entries, field values
and agreement between service results and stage outcomes.

A complete experiment contains six service results:
two ports across baseline, impact and recovery.

An early stop can contain fewer results.
For example, syntax rejection after a healthy baseline records only
the two baseline service results.

Reports are saved in `reports/` and excluded from Git.
The candidate fingerprint supports correlation; it is not an
authenticity guarantee.

## Verified experiments

| Scenario | Outcome | Wrapper exit |
|---|---|---|
| allow-http | Port 80 preserved; port 8080 blocked; both recovered | 1 |
| allow-required-services | Both ports preserved; recovery verified | 0 |
| invalid-syntax | Syntax rejected before application | 2 |
| Unhealthy baseline safeguard | Candidate not applied | 2 |

The block-http fixture was verified during the earlier
port-80-only experiment: HTTP failed during application,
recovered after cleanup, and the wrapper returned exit 1.

Additional standalone baseline checks were verified by stopping
and restarting Nginx on debian-server.

See `docs/firewall-impact-experiment.md` for experiment details
and historical results.

## Automated tests

Run all 17 unit tests from the repository root:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The tests cover:

- Successful and disruptive candidates.
- Missing stage evidence and missing recovery.
- Failed cleanup or recovery.
- Exit codes that contradict stage results.
- Duplicate, out-of-order and malformed stage events.
- Complete service results and connection timeouts.
- Missing or duplicate service results.
- Contradictions between service evidence and stage outcomes.
- Malformed service JSON.
- Early termination after baseline checks.

These tests require no sudo, running HTTP server or network namespaces.

### Continuous integration

The workflow in `.github/workflows/test.yml` discovers both test files
on pushes and pull requests using Python 3.13.

All 17 tests passed locally and in GitHub Actions.

CI tests the Python reporting logic.
Actual firewall experiments run separately in the Debian lab.

## Current limitations

- TCP port 22 reachability does not verify SSH authentication.
- HTTP checks do not verify page content or database health.
- Service requirements are fixed in the runner.
- The two HTTP listeners simulate required connections; they do not form an actual application dependency.
- Candidate selection is limited to four reviewed fixtures.
- Network namespaces share the host kernel and filesystem; they are not a complete security sandbox.
- Results apply to the isolated model, not production equivalence.
- Dependency discovery and live deployment rollback are not implemented.
- Preflight errors and emergency cleanup are not fully structured.
- Cleanup traps cannot handle power loss or SIGKILL.
- Concurrent experiment runs are not supported.
