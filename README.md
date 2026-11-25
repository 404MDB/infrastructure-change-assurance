# Infrastructure Change Assurance

A project developing dependency-aware configuration validation
and safe deployment.

## Current implementation

- Configurable TCP port and HTTP baseline checks.
- Timestamped JSON baseline reports.
- Reusable isolated network lab.
- Automated testing of two HTTP behavior fixtures and one invalid-syntax fixture.
- Candidate cleanup and HTTP recovery verification after applied changes.
- Candidate reports with validated, structured stage results.
- Nine reporter unit tests.
- GitHub Actions CI for reporter tests on pushes and pull requests.

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

Run from the repository root:

```bash
python3 src/baseline.py
```

Edit `config/target.json` to configure the target IPv4 address,
ports, HTTP path, expected status and timeout.

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

Start the HTTP fixture from the repository root:

```bash
sudo ip netns exec ica-lab python3 -m http.server 80 \
  --bind 10.200.1.2 --directory "$PWD/tests/fixtures/web"
```

Leave this running while testing from a second terminal.

## Candidate testing

Run from the repository root as the regular user:

```bash
python3 src/candidate_report.py allow-http
python3 src/candidate_report.py block-http
python3 src/candidate_report.py invalid-syntax
```

Only the child firewall runner uses sudo.

### Candidate fixtures

| Candidate | Purpose |
|---|---|
| allow-http | Verify that a valid configuration preserves required HTTP access |
| block-http | Detect a syntactically valid configuration that blocks required HTTP access |
| invalid-syntax | Verify that an incomplete configuration is rejected before application |

These are reviewed lab fixtures, not production firewall configurations.

### Experiment stages

1. Check baseline HTTP access.
2. Validate candidate syntax.
3. Apply candidate inside ica-lab.
4. Check HTTP access.
5. Remove the candidate table.
6. Verify HTTP recovery.

An unhealthy baseline or invalid syntax stops the experiment before
candidate application.

### Candidate report exit codes

- 0: Required HTTP check preserved; recovery verified.
- 1: Required HTTP check failed; recovery verified.
- 2: Execution, baseline, syntax validation or event-validation error.
- 3: Report could not be written.

The report also preserves the raw runner exit code.
Runner cleanup or recovery failures produce an error decision;
their raw exit code is retained in the report.

## Candidate reports

Candidate reports use schema version 2 and contain:

- Candidate name and SHA-256 fingerprint.
- UTC start and finish timestamps.
- Decision and runner exit code.
- Structured stage results.
- Event-validation errors.
- Captured standard output and errors.

Stage statuses are `passed`, `failed` or `not_run`.
`not_run` means no valid event was observed for that stage.

Decisions use validated stage events and the runner exit code.
Missing, malformed or inconsistent evidence cannot produce a passed decision.

Reports are saved in `reports/` and excluded from Git.
The candidate fingerprint supports correlation; it is not an
authenticity guarantee.

## Verified experiments

| Scenario | Outcome | Wrapper exit |
|---|---|---|
| allow-http candidate | HTTP preserved; recovery verified | 0 |
| block-http candidate | HTTP blocked; recovery verified | 1 |
| invalid-syntax candidate | Syntax rejected before application | 2 |
| HTTP unavailable before testing | Candidate not applied | 2 |

Additional baseline checks were verified by stopping and
restarting Nginx on debian-server.

See `docs/firewall-impact-experiment.md` for experiment details.

## Automated tests

Run the nine reporter decision tests from the repository root:

```bash
python3 -m unittest discover -s tests -p 'test_candidate_report.py' -v
```

The tests cover:

- Successful and disruptive candidates.
- Missing evidence and missing recovery.
- Failed cleanup or recovery.
- Exit codes that contradict stage results.
- Duplicate, out-of-order and malformed events.

These tests require no sudo, running HTTP server or network namespaces.

### Continuous integration

The workflow in `.github/workflows/test.yml` runs the reporter tests
on pushes and pull requests using Python 3.13.

CI tests the reporter logic. Actual firewall experiments run separately
in the Debian lab.

## Current limitations

- TCP port 22 reachability does not verify SSH authentication.
- HTTP checks do not verify page content or database health.
- Candidate testing covers only two HTTP behavior fixtures and one invalid-syntax fixture.
- Network namespaces share the host kernel and filesystem; they are not a complete security sandbox.
- Results apply to the isolated model, not production equivalence.
- Dependency analysis and live deployment rollback are not implemented.
- Preflight errors and emergency cleanup are not fully structured.
- Cleanup traps cannot handle power loss or SIGKILL.
- Concurrent experiment runs are not supported.
