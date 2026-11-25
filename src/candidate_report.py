import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
import uuid

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", choices=["allow-http", "block-http", "invalid-syntax"])
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

    stage_names = ["baseline", "validation", "apply",
                   "impact", "cleanup", "recovery"]
    stages = {name: "not_run" for name in stage_names}
    event_errors = []
    seen = []

    for line in result.stdout.splitlines():
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
            if stages["impact"] == "passed" and result.returncode == 0:
                decision = "passed"
            elif stages["impact"] == "failed" and result.returncode == 1:
                decision = "blocked"

    report = {
        "schema_version": 2,
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
