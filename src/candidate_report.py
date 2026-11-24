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
    parser.add_argument("candidate", choices=["allow-http", "block-http"])
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

    lines = result.stdout.splitlines()
    passed = "CANDIDATE PASSED: required lab HTTP check preserved."
    blocked = "CANDIDATE BLOCKED: required lab HTTP check failed; recovery verified."

    decision = "error"
    if result.returncode == 0 and passed in lines:
        decision = "passed"
    elif result.returncode == 1 and blocked in lines:
        decision = "blocked"

    report = {
        "schema_version": 1,
        "check_type": "candidate_experiment",
        "candidate": args.candidate,
        "candidate_sha256": fingerprint,
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "runner_exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
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
