# ChangeGuard

A Linux configuration-impact testing project.

## Current implementation
Checks TCP connectivity to port 22 and HTTP status on debian-server.
Returns exit code 0 when both pass, or 1 when either fails.

## Lab
- debian-control: 192.168.56.10 — runs the checker
- debian-server: 192.168.56.20 — hosts Nginx

## Run
python3 src/baseline.py

## Verification exercise
Stop Nginx, run the checker, restore Nginx, and run again.
Expected: HTTP fails during the outage and passes after recovery.

## Current limitations
TCP port 22 reachability does not verify SSH authentication.
HTTP status does not verify page content or database health.
Candidate configuration testing and rollback are not implemented yet.

## Configuration
Edit config/target.json to set the target IP, ports,
HTTP path, expected status and timeout.

## Exit codes
- 0: All checks passed
- 1: A service check failed
- 2: Configuration error
