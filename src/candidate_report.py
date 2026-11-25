import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
import uuid

ROOT = Path(__file__).resolve().parent.parent

def evaluate_events(stdout, returncode):
    stage_names = ["baseline", "validation", "apply",
                   "impact", "cleanup", "recovery"]
    stages = {name: "not_run" for name in stage_names}
    event_errors = []
    seen = []

    for line in stdout.splitlines():
        if not line.startswith("ICA_EVENT "):
            continue
        try:
            event = json.loads(line[len("ICA_EVENT "):])
            if not isinstance(event, dict):
                raise ValueError("Event must be an object")
            if set(event) != {"stage", "status"}:
                raise ValueError("Unexpected event fields")

            name = event["stage"]
            status = event["status"]
            if not isinstance(name, str) or name not in stages:
                raise ValueError("Unknown stage")
            if status not in ("passed", "failed"):
                raise ValueError("Invalid stage status")
            if name in seen:
                raise ValueError("Duplicate stage")
            if name != stage_names[len(seen)]:
                raise ValueError("Stages out of order")

            seen.append(name)
            stages[name] = status
        except (ValueError, TypeError, IndexError) as error:
            event_errors.append(str(error))

    decision = "error"
    if not event_errors and seen == stage_names:
        infrastructure_ok = all(
            stages[name] == "passed"
            for name in stage_names if name != "impact"
        )
        if infrastructure_ok:
            if stages["impact"] == "passed" and returncode == 0:
                decision = "passed"
            elif stages["impact"] == "failed" and returncode == 1:
                decision = "blocked"

    return decision, stages, event_errors

def parse_service_results(stdout, stages):
    results = []
    errors = []
    seen = set()
    phases = ("baseline", "impact", "recovery")
    ports = (80, 8080)

    for line in stdout.splitlines():
        if not line.startswith("ICA_SERVICE "):
            continue

        try:
            event = json.loads(line[len("ICA_SERVICE "):])
            fields = {
                "phase", "port", "status",
                "http_status", "curl_exit_code",
            }
            if not isinstance(event, dict) or set(event) != fields:
                raise ValueError("Unexpected service event fields")

            phase = event["phase"]
            port = event["port"]
            status = event["status"]
            http_status = event["http_status"]
            curl_code = event["curl_exit_code"]

            if phase not in phases:
                raise ValueError("Unknown service phase")
            if type(port) is not int or port not in ports:
                raise ValueError("Unknown service port")
            if status not in ("passed", "failed"):
                raise ValueError("Invalid service status")
            if type(curl_code) is not int or not 0 <= curl_code <= 255:
                raise ValueError("Invalid curl exit code")

            if curl_code == 0:
                if type(http_status) is not int or not 100 <= http_status <= 599:
                    raise ValueError("Invalid HTTP status")
            elif http_status is not None:
                raise ValueError("Failed curl must have null HTTP status")

            expected = (
                "passed"
                if curl_code == 0 and http_status == 200
                else "failed"
            )
            if status != expected:
                raise ValueError("Service status contradicts probe result")

            key = (phase, port)
            if key in seen:
                raise ValueError("Duplicate service result")

            seen.add(key)
            results.append(event)
        except (ValueError, TypeError) as error:
            errors.append(str(error))

    for phase in phases:
        phase_results = [
            item for item in results if item["phase"] == phase
        ]

        if stages[phase] == "not_run":
            if phase_results:
                errors.append(f"{phase}: results without a stage event")
            continue

        if len(phase_results) != len(ports):
            errors.append(f"{phase}: missing required service results")
            continue

        expected = (
            "passed"
            if all(item["status"] == "passed" for item in phase_results)
            else "failed"
        )
        if stages[phase] != expected:
            errors.append(f"{phase}: stage contradicts service results")

    return results, errors

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", choices=["allow-http", "block-http", "allow-required-services", "invalid-syntax"])
    args = parser.parse_args()

    candidate = ROOT / "config" / "candidates" / f"{args.candidate}.nft"
    started = datetime.now(timezone.utc)

    try:
        fingerprint = hashlib.sha256(candidate.read_bytes()).hexdigest()
        result = subprocess.run(
            ["sudo", "bash", str(ROOT / "scripts" / "test-candidate.sh"),
             args.candidate],
            capture_output=True,
            text=True,
        )
    except OSError as error:
        print(f"RUN ERROR: {error}", file=sys.stderr)
        return 2

    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)

    decision, stages, event_errors = evaluate_events(
        result.stdout, result.returncode
    )

    service_results, service_errors = parse_service_results(
        result.stdout, stages
    )
    if service_errors:
        decision = "error"

    report = {
        "schema_version": 3,
        "check_type": "candidate_experiment",
        "candidate": args.candidate,
        "candidate_sha256": fingerprint,
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "runner_exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
	"stages": stages,
        "event_errors": event_errors,
        "service_results": service_results,
        "service_errors": service_errors,
    }

    path = ROOT / "reports" / (
        started.strftime("candidate-%Y%m%dT%H%M%S%fZ-")
        + uuid.uuid4().hex[:8] + ".json"
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2)
            file.write("\n")
    except OSError as error:
        print(f"REPORT ERROR: {error}", file=sys.stderr)
        return 3

    print(f"Report saved: {path}")
    return {"passed": 0, "blocked": 1, "error": 2}[decision]


if __name__ == "__main__":
    sys.exit(main())
