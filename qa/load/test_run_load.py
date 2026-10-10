from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))

from run_load import (
    ApiClient,
    Metrics,
    _metric_summary,
    percentile,
    prepare_state,
    threshold_result,
)


class SetupHandler(BaseHTTPRequestHandler):
    profile_id = "candidate-profile"

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def _write(self, status: int, body: object) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_PATCH(self) -> None:
        if self.path == "/api/v1/candidate/privacy":
            self._write(200, {})
        elif self.path == "/api/v1/candidate/profile":
            self._write(200, {"id": self.profile_id})
        elif self.path in {"/api/v1/employer/company", "/api/v1/employer/hiring-need"}:
            self._write(200, {})
        else:
            self._write(404, {})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        responses = {
            "/api/v1/employer/hiring-need": (200, None),
            "/api/v1/employer/talent-radar": (200, {"candidates": [{"id": self.profile_id, "eligibility": "verified"}]}),
            "/api/v1/employer/invitations": (200, []),
            "/api/v1/chat/conversations": (200, [{"id": "conversation"}]),
        }
        status, body = responses.get(path, (404, {}))
        self._write(status, body)

    def do_POST(self) -> None:
        if self.path == "/api/v1/employer/hiring-need":
            self._write(201, {})
        elif self.path == "/api/v1/employer/invitations":
            self._write(201, {"id": "invitation", "status": "pending"})
        elif self.path.endswith("/respond"):
            self._write(200, {"status": "accepted"})
        else:
            self._write(404, {})


class LoadRunnerTests(unittest.TestCase):
    def test_percentile_uses_nearest_rank_and_empty_is_zero(self) -> None:
        self.assertEqual(percentile([], 0.95), 0.0)
        self.assertEqual(percentile([0.3, 0.1, 0.2], 0.50), 0.2)
        self.assertEqual(percentile([0.3, 0.1, 0.2], 0.95), 0.3)

    def test_metric_summary_and_thresholds_are_auditable(self) -> None:
        metrics = Metrics()
        from run_load import HttpResult

        metrics.add(HttpResult("GET", "/api/v1/candidate/profile", 200, 0.2))
        metrics.add(HttpResult("GET", "/api/v1/employer/talent-radar", 200, 0.3))
        metrics.add(HttpResult("POST", "/api/v1/chat/conversations/id/messages", 500, 0.4))
        summary = _metric_summary(metrics.rows())
        self.assertEqual(summary["request_count"], 3)
        self.assertEqual(summary["error_count"], 1)
        self.assertEqual(summary["endpoints"]["GET /api/v1/employer/talent-radar"]["request_count"], 1)
        result = threshold_result(summary)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["error_rate_lt_1_percent"])

    def test_authenticated_setup_resolves_profile_and_conversation(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), SetupHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            state = prepare_state(ApiClient(f"http://127.0.0.1:{server.server_port}"), "candidate-token", "employer-token")
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
        self.assertEqual(state.candidate_profile_id, "candidate-profile")
        self.assertEqual(state.conversation_id, "conversation")


if __name__ == "__main__":
    unittest.main()
