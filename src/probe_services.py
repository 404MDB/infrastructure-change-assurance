import argparse
import json
import subprocess
import sys

if __package__:
    from .requirements import validate_requirements
else:
    from requirements import validate_requirements


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "phase", choices=["baseline", "impact", "recovery"]
    )
    args = parser.parse_args()

    try:
        config = validate_requirements(json.load(sys.stdin))
    except (OSError, ValueError, TypeError) as error:
        print(f"REQUIREMENTS ERROR: {error}", file=sys.stderr)
        return 2

    failed = False

    for service in config["services"]:
        url = (
            f'http://{config["target_host"]}:{service["port"]}'
            f'{service["path"]}'
        )

        command = [
            "ip", "netns", "exec", config["source_namespace"],
            "curl", "--silent", "--show-error",
            "--globoff", "--path-as-is", "--noproxy", "*",
            "--head", "--output", "/dev/null",
            "--write-out", "%{http_code}",
            "--connect-timeout",
            str(config["connect_timeout_seconds"]),
            "--max-time", str(config["max_time_seconds"]),
            "--url", url,
        ]

        try:
            result = subprocess.run(
                command, capture_output=True, text=True
            )
        except OSError as error:
            print(f"PROBE ERROR: {error}", file=sys.stderr)
            return 2

        print(result.stderr, end="", file=sys.stderr)

        http_status = None
        raw_status = result.stdout.strip()
        if (
            result.returncode == 0
            and len(raw_status) == 3
            and raw_status.isascii()
            and raw_status.isdigit()
            and 100 <= int(raw_status) <= 599
        ):
            http_status = int(raw_status)

        passed = (
            result.returncode == 0
            and http_status == service["expected_status"]
        )
        failed = failed or not passed

        event = {
            "phase": args.phase,
            "name": service["name"],
            "port": service["port"],
            "path": service["path"],
            "expected_status": service["expected_status"],
            "status": "passed" if passed else "failed",
            "http_status": http_status,
            "curl_exit_code": result.returncode,
        }
        print("ICA_SERVICE " + json.dumps(event), flush=True)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
