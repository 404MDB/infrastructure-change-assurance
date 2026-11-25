import json
import unittest

from src.candidate_report import evaluate_events


STAGES = [
    "baseline", "validation", "apply",
    "impact", "cleanup", "recovery",
]


def make_events(statuses=None):
    statuses = statuses or {}
    return "\n".join(
        "ICA_EVENT " + json.dumps({
            "stage": name,
            "status": statuses.get(name, "passed"),
        })
        for name in STAGES
    )


class CandidateReportTests(unittest.TestCase):
    def test_successful_candidate(self):
        decision, _, errors = evaluate_events(make_events(), 0)
        self.assertEqual(decision, "passed")
        self.assertEqual(errors, [])

    def test_disruptive_candidate(self):
        output = make_events({"impact": "failed"})
        decision, _, errors = evaluate_events(output, 1)
        self.assertEqual(decision, "blocked")
        self.assertEqual(errors, [])

    def test_missing_evidence(self):
        decision, stages, _ = evaluate_events("", 0)
        self.assertEqual(decision, "error")
        self.assertTrue(all(
            status == "not_run" for status in stages.values()
        ))

    def test_missing_recovery(self):
        output = "\n".join(make_events().splitlines()[:-1])
        decision, stages, _ = evaluate_events(output, 0)
        self.assertEqual(decision, "error")
        self.assertEqual(stages["recovery"], "not_run")

    def test_failed_cleanup_or_recovery(self):
        for stage in ("cleanup", "recovery"):
            with self.subTest(stage=stage):
                output = make_events({stage: "failed"})
                decision, _, _ = evaluate_events(output, 0)
                self.assertEqual(decision, "error")

    def test_exit_code_mismatch(self):
        for output, code in (
            (make_events(), 1),
            (make_events({"impact": "failed"}), 0),
        ):
            with self.subTest(code=code):
                decision, _, _ = evaluate_events(output, code)
                self.assertEqual(decision, "error")

    def test_duplicate_event(self):
        output = make_events()
        output += "\n" + output.splitlines()[0]
        decision, _, errors = evaluate_events(output, 0)
        self.assertEqual(decision, "error")
        self.assertTrue(errors)

    def test_out_of_order_events(self):
        lines = make_events().splitlines()
        lines[0], lines[1] = lines[1], lines[0]
        decision, _, errors = evaluate_events("\n".join(lines), 0)
        self.assertEqual(decision, "error")
        self.assertTrue(errors)

    def test_malformed_event(self):
        output = make_events() + "\nICA_EVENT {broken"
        decision, _, errors = evaluate_events(output, 0)
        self.assertEqual(decision, "error")
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
