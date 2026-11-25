import ipaddress
import json


def load_requirements(path):
    with path.open(encoding="utf-8") as file:
        config = json.load(file)
    return validate_requirements(config)


def validate_requirements(config):
    fields = {
        "schema_version",
        "source_namespace",
        "target_host",
        "services",
        "connect_timeout_seconds",
        "max_time_seconds",
    }

    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError("Unexpected requirements fields")

    if type(config["schema_version"]) is not int:
        raise ValueError("Schema version must be an integer")
    if config["schema_version"] != 1:
        raise ValueError("Unsupported requirements schema")

    if config["source_namespace"] != "ica-client":
        raise ValueError("Source namespace must be ica-client")

    host = config["target_host"]
    if not isinstance(host, str):
        raise ValueError("Target host must be a string")
    ipaddress.IPv4Address(host)
    if host != "10.200.1.2":
        raise ValueError("Target host must be 10.200.1.2")

    connect_timeout = config["connect_timeout_seconds"]
    max_time = config["max_time_seconds"]

    for value in (connect_timeout, max_time):
        if type(value) is not int or not 1 <= value <= 30:
            raise ValueError("Timeouts must be integers from 1 to 30")

    if connect_timeout > max_time:
        raise ValueError("Connect timeout cannot exceed maximum time")

    services = config["services"]
    if not isinstance(services, list) or not 1 <= len(services) <= 10:
        raise ValueError("Define between 1 and 10 services")

    names = set()
    endpoints = set()

    for service in services:
        service_fields = {"name", "port", "path", "expected_status"}
        if not isinstance(service, dict) or set(service) != service_fields:
            raise ValueError("Unexpected service fields")

        name = service["name"]
        if not isinstance(name, str) or not 1 <= len(name) <= 64:
            raise ValueError("Service name must contain 1 to 64 characters")
        if any(
            char not in "abcdefghijklmnopqrstuvwxyz0123456789-_"
            for char in name
        ):
            raise ValueError("Use lowercase letters, digits, - or _ in names")
        if name in names:
            raise ValueError("Duplicate service name")
        names.add(name)

        port = service["port"]
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Port must be an integer from 1 to 65535")

        http_path = service["path"]
        if not isinstance(http_path, str) or not http_path.startswith("/"):
            raise ValueError("HTTP path must start with /")
        if any(ord(char) <= 32 or ord(char) >= 127 for char in http_path):
            raise ValueError("HTTP path must use ASCII without spaces or controls")
        if "#" in http_path:
            raise ValueError("HTTP path must not contain a URL fragment")

        endpoint = (port, http_path)
        if endpoint in endpoints:
            raise ValueError("Duplicate service endpoint")
        endpoints.add(endpoint)

        status = service["expected_status"]
        if type(status) is not int or not 100 <= status <= 599:
            raise ValueError("Expected status must be an integer from 100 to 599")

    return config
