import json
import unittest

from src.candidate_report import parse_service_results


def make_results():
    return [
        {
            "phase": phase,
            "port": port,
            "status": "passed",
            "http_status": 200,
            "curl_exit_code": 0,
        }
        for phase in ("baseline", "impact", "recovery")
        for port in (80, 8080)
    ]


def encode(results):
    return "\n".join(
        "ICA_SERVICE " + json.dumps(item)
        for item in results
    )


class ServiceResultTests(unittest.TestCase):
    def setUp(self):
        self.stages = {
            "baseline": "passed",
            "impact": "passed",
            "recovery": "passed",
        }

    def test_all_services_pass(self):
        results, errors = parse_service_results(
            encode(make_results()), self.stages
        )
        self.assertEqual(len(results), 6)
        self.assertEqual(errors, [])

    def test_timeout_matches_failed_impact(self):
        events = make_results()
        events[3].update(
            status="failed",
            http_status=None,
            curl_exit_code=28,
        )
        self.stages["impact"] = "failed"
        results, errors = parse_service_results(
            encode(events), self.stages
        )
        self.assertEqual(errors, [])
        self.assertEqual(results[3]["port"], 8080)
        self.assertEqual(results[3]["status"], "failed")

    def test_missing_service_result(self):
        _, errors = parse_service_results(
            encode(make_results()[:-1]), self.stages
        )
        self.assertTrue(errors)

    def test_duplicate_service_result(self):
        events = make_results()
        events.append(events[0].copy())
        _, errors = parse_service_results(
            encode(events), self.stages
        )
        self.assertTrue(errors)

    def test_stage_contradicts_service(self):
        events = make_results()
        events[3].update(
            status="failed",
            http_status=None,
            curl_exit_code=28,
        )
        _, errors = parse_service_results(
            encode(events), self.stages
        )
        self.assertTrue(errors)

    def test_status_contradicts_http_response(self):
        events = make_results()
        events[3]["http_status"] = 404
        _, errors = parse_service_results(
            encode(events), self.stages
        )
        self.assertTrue(errors)

    def test_malformed_json(self):
        output = encode(make_results()) + "\nICA_SERVICE {broken"
        _, errors = parse_service_results(output, self.stages)
        self.assertTrue(errors)

    def test_early_validation_failure(self):
        self.stages["impact"] = "not_run"
        self.stages["recovery"] = "not_run"
        results, errors = parse_service_results(
            encode(make_results()[:2]), self.stages
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
