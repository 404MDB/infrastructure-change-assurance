import contextlib
import io
import unittest
from unittest.mock import patch

from src import candidate_report


class RequirementsPreflightTests(unittest.TestCase):
    def test_invalid_requirements_prevent_runner_start(self):
        stderr = io.StringIO()

        with (
            patch(
                "sys.argv",
                ["candidate_report.py", "allow-required-services"],
            ),
            patch.object(
                candidate_report,
                "load_requirements",
                side_effect=ValueError("Invalid requirements"),
            ),
            patch.object(candidate_report.subprocess, "run") as runner,
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = candidate_report.main()

        self.assertEqual(exit_code, 2)
        runner.assert_not_called()
        self.assertIn("REQUIREMENTS ERROR", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
