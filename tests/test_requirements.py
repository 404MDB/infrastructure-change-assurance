import json
from pathlib import Path
import tempfile
import unittest

from src.requirements import load_requirements


class RequirementsTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "schema_version": 1,
            "source_namespace": "ica-client",
            "target_host": "10.200.1.2",
            "services": [
                {
                    "name": "website",
                    "port": 80,
                    "path": "/",
                    "expected_status": 200,
                },
                {
                    "name": "internal-api",
                    "port": 8080,
                    "path": "/",
                    "expected_status": 200,
                },
            ],
            "connect_timeout_seconds": 3,
            "max_time_seconds": 5,
        }

    def load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "requirements.json"
            path.write_text(json.dumps(self.config), encoding="utf-8")
            return load_requirements(path)

    def test_valid_configuration(self):
        self.assertEqual(self.load(), self.config)

    def test_invalid_port(self):
        for port in (0, 65536, True, "80"):
            with self.subTest(port=port):
                self.config["services"][0]["port"] = port
                with self.assertRaises(ValueError):
                    self.load()

    def test_duplicate_name(self):
        self.config["services"][1]["name"] = "website"
        with self.assertRaises(ValueError):
            self.load()

    def test_duplicate_endpoint(self):
        self.config["services"][1]["port"] = 80
        with self.assertRaises(ValueError):
            self.load()

    def test_empty_services(self):
        self.config["services"] = []
        with self.assertRaises(ValueError):
            self.load()

    def test_invalid_timeout_relationship(self):
        self.config["connect_timeout_seconds"] = 6
        with self.assertRaises(ValueError):
            self.load()

    def test_target_outside_lab(self):
        self.config["target_host"] = "192.168.56.20"
        with self.assertRaises(ValueError):
            self.load()

    def test_invalid_paths(self):
        for path in ("health", "/bad path", "/#fragment", "/\n"):
            with self.subTest(path=path):
                self.config["services"][0]["path"] = path
                with self.assertRaises(ValueError):
                    self.load()

    def test_invalid_expected_status(self):
        self.config["services"][0]["expected_status"] = True
        with self.assertRaises(ValueError):
            self.load()

    def test_unexpected_field(self):
        self.config["extra"] = "unexpected"
        with self.assertRaises(ValueError):
            self.load()


if __name__ == "__main__":
    unittest.main()
