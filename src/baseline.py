import http.client
import socket
import sys

from pathlib import Path
import ipaddress
import json

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "target.json"

try:
    with CONFIG_FILE.open(encoding="utf-8") as file:
        config = json.load(file)

    if not isinstance(config, dict):
        raise ValueError("Configuration must be a JSON object")

    HOST = config["host"]
    ipaddress.IPv4Address(HOST)

    SSH_PORT = config["ssh_port"]
    HTTP_PORT = config["http_port"]
    TIMEOUT = config["timeout_seconds"]
    EXPECTED_STATUS = config["expected_status"]
    HTTP_PATH = config["http_path"]

    for port in (SSH_PORT, HTTP_PORT):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Ports must be integers between 1 and 65535")

    if type(TIMEOUT) is not int or not 1 <= TIMEOUT <= 30:
        raise ValueError("Timeout must be an integer between 1 and 30 seconds")

    if type(EXPECTED_STATUS) is not int or not 100 <= EXPECTED_STATUS <= 599:
        raise ValueError("Expected status must be an integer from 100 to 599")

    if not isinstance(HTTP_PATH, str) or not HTTP_PATH.startswith("/"):
        raise ValueError("HTTP path must be a string starting with /")
    if any(ord(char) <= 32 or ord(char) >= 127 for char in HTTP_PATH):
        raise ValueError("HTTP path must use ASCII without spaces or controls")

except (OSError, ValueError, KeyError, TypeError) as error:
    print(f"CONFIG ERROR: {error}", file=sys.stderr)
    sys.exit(2)

def check_ssh_port():
    try:
        with socket.create_connection((HOST, SSH_PORT), timeout=TIMEOUT):
            return True, f"TCP port {SSH_PORT} accepts connections"
    except OSError as error:
        return False, str(error)


def check_http():
    connection = http.client.HTTPConnection(HOST, HTTP_PORT, timeout=TIMEOUT)
    try:
        connection.request("HEAD", HTTP_PATH)
        response = connection.getresponse()
        return response.status == EXPECTED_STATUS, f"HTTP {response.status} {response.reason}"
    except (OSError, http.client.HTTPException) as error:
        return False, str(error)
    finally:
        connection.close()


def main():
    print(f"ChangeGuard baseline check: {HOST}")
    all_passed = True

    for name, check in [
        ("SSH port", check_ssh_port),
        ("Website", check_http),
    ]:
        passed, detail = check()
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
        all_passed = all_passed and passed

    if all_passed:
        print("BASELINE PASS: both checks passed.")
        return 0

    print("BASELINE FAIL: investigate before testing a change.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
