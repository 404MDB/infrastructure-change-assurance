import http.client
import socket
import sys

HOST = "192.168.56.20"
TIMEOUT = 5


def check_ssh_port():
    try:
        with socket.create_connection((HOST, 22), timeout=TIMEOUT):
            return True, "TCP port 22 accepts connections"
    except OSError as error:
        return False, str(error)


def check_http():
    connection = http.client.HTTPConnection(HOST, 80, timeout=TIMEOUT)
    try:
        connection.request("HEAD", "/")
        response = connection.getresponse()
        return response.status == 200, f"HTTP {response.status} {response.reason}"
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
