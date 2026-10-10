#!/usr/bin/env python3
"""Run the authenticated core-profile target workload.

The runner deliberately uses only Python's standard library.  It is an
operator-facing measurement tool, not a test fixture: bearer tokens must be
provided explicitly and no token material is written to artifacts.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import random
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from datetime import UTC
except ImportError:  # Python 3.8–3.10 compatibility for the host-side runner.
    UTC = timezone.utc


DEFAULT_TARGET_USERS = 50
DEFAULT_TARGET_DURATION = 600
DEFAULT_RAMP = 60
DEFAULT_PAUSE = 1.0
COMMON_READ_ROUTES = {
    "/api/v1/candidate/profile",
    "/api/v1/candidate/dashboard",
    "/api/v1/candidate/invitations",
    "/api/v1/employer/company",
    "/api/v1/employer/hiring-need",
    "/api/v1/employer/invitations",
    "/api/v1/chat/conversations",
}
DOCKER_STAT_PHASES = ("before", "during", "after")
_DOCKER_SIZE_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)?)\s*([KMGTPE]?i?B)$", re.IGNORECASE)


@dataclass(frozen=True)
class HttpResult:
    method: str
    route: str
    status: int
    seconds: float


@dataclass(frozen=True)
class LoadState:
    candidate_profile_id: str
    conversation_id: str


class Metrics:
    """Thread-safe collection of timing rows for the timed workload."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: list[HttpResult] = []

    def add(self, result: HttpResult) -> None:
        with self._lock:
            self._rows.append(result)

    def rows(self) -> list[HttpResult]:
        with self._lock:
            return list(self._rows)


class ApiClient:
    def __init__(self, base_url: str, metrics: Metrics | None = None, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.metrics = metrics
        self.timeout = timeout

    def request(
        self,
        method: str,
        route: str,
        token: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[HttpResult, Any]:
        body = None
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.base_url}{route}", data=body, headers=headers, method=method
        )
        started = time.perf_counter()
        status = 0
        response_body: Any = None
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status = response.status
                raw = response.read()
                if raw:
                    try:
                        decoded = json.loads(raw)
                        if isinstance(decoded, (dict, list)):
                            response_body = decoded
                    except json.JSONDecodeError:
                        pass
        except urllib.error.HTTPError as error:
            status = error.code
        except (OSError, TimeoutError):
            status = 0
        result = HttpResult(method, route, status, time.perf_counter() - started)
        if self.metrics is not None:
            self.metrics.add(result)
        return result, response_body


class TokenPool:
    def __init__(self, tokens: Iterable[str]):
        self.tokens = [token.strip() for token in tokens if token.strip()]
        if not self.tokens:
            raise ValueError("at least one non-empty bearer token is required")

    def at(self, index: int) -> str:
        return self.tokens[index % len(self.tokens)]


def _tokens_from_file(path: str | None) -> list[str]:
    if not path:
        return []
    return [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def load_token_pool(
    *, file_path: str | None, values: list[str], environment_name: str, file_environment_name: str
) -> TokenPool:
    resolved_file = file_path or os.environ.get(file_environment_name)
    tokens = _tokens_from_file(resolved_file)
    tokens.extend(values)
    if not tokens:
        tokens.extend(value for value in os.environ.get(environment_name, "").split(",") if value.strip())
    if not tokens:
        raise ValueError(
            f"no tokens supplied; use the role token-file option, a repeated role token option, "
            f"or {environment_name}/{file_environment_name}"
        )
    return TokenPool(tokens)


def _expect(result: HttpResult, expected: set[int], route: str) -> None:
    if result.status not in expected:
        raise RuntimeError(f"authenticated setup failed for {route}: HTTP {result.status}")


def prepare_state(client: ApiClient, candidate_token: str, employer_token: str) -> LoadState:
    """Prepare a normal accepted invitation and resolve its chat conversation."""

    privacy, _ = client.request(
        "PATCH",
        "/api/v1/candidate/privacy",
        candidate_token,
        {"processing_consent": True, "publication_consent": True, "discoverable": True},
    )
    _expect(privacy, {200}, "/api/v1/candidate/privacy")
    profile, profile_body = client.request(
        "PATCH",
        "/api/v1/candidate/profile",
        candidate_token,
        {
            "display_name": "Load-test candidate",
            "headline": "Load-test backend engineer",
            "skills": ["Python", "REST APIs", "Docker"],
        },
    )
    _expect(profile, {200}, "/api/v1/candidate/profile")
    if not profile_body or not isinstance(profile_body.get("id"), str):
        raise RuntimeError("candidate profile setup did not return a profile id")
    profile_id = profile_body["id"]

    company, _ = client.request(
        "PATCH",
        "/api/v1/employer/company",
        employer_token,
        {"name": "FSP Load Test Labs", "public_contact_method": "load-test@fsp.ru"},
    )
    _expect(company, {200}, "/api/v1/employer/company")
    need, need_body = client.request("GET", "/api/v1/employer/hiring-need", employer_token)
    _expect(need, {200}, "/api/v1/employer/hiring-need")
    need_payload = {
        "team": "Load-test platform team",
        "role": "Backend engineer",
        "specialization": "backend-engineering",
        "grade": "middle",
        "required_skills": ["python", "rest-apis"],
        "preferred_skills": ["docker"],
    }
    if need_body is None:
        created_need, _ = client.request("POST", "/api/v1/employer/hiring-need", employer_token, need_payload)
        _expect(created_need, {201}, "/api/v1/employer/hiring-need")
    else:
        updated_need, _ = client.request("PATCH", "/api/v1/employer/hiring-need", employer_token, need_payload)
        _expect(updated_need, {200}, "/api/v1/employer/hiring-need")

    radar, radar_body = client.request("GET", "/api/v1/employer/talent-radar", employer_token)
    _expect(radar, {200}, "/api/v1/employer/talent-radar")
    eligible = {
        item.get("id")
        for item in (radar_body or {}).get("candidates", [])
        if isinstance(item, dict) and item.get("id") == profile_id and item.get("eligibility") == "verified"
    }
    if not eligible:
        raise RuntimeError(
            "candidate setup is not verified/searchable; seed a candidate with a completed base assessment "
            "before running the target load"
        )

    invitations, invitation_body = client.request("GET", "/api/v1/employer/invitations", employer_token)
    _expect(invitations, {200}, "/api/v1/employer/invitations")
    invitation_id = None
    invitation_status = None
    for item in invitation_body or []:
        if isinstance(item, dict) and item.get("candidate", {}).get("id") == profile_id:
            invitation_id = item.get("id")
            invitation_status = item.get("status")
            break
    if invitation_id is None:
        created, created_body = client.request(
            "POST",
            "/api/v1/employer/invitations",
            employer_token,
            {
                "candidate_profile_id": profile_id,
                "salary_min_rub": 180000,
                "salary_max_rub": 260000,
                "offer_description": "Load-test evidence-led platform services.",
            },
        )
        _expect(created, {201}, "/api/v1/employer/invitations")
        invitation_id = (created_body or {}).get("id")
        invitation_status = (created_body or {}).get("status")
    if not isinstance(invitation_id, str):
        raise TypeError("invitation setup did not return an invitation id")
    if invitation_status == "pending":
        accepted, _ = client.request(
            "POST",
            f"/api/v1/candidate/invitations/{invitation_id}/respond",
            candidate_token,
            {"action": "accepted"},
        )
        _expect(accepted, {200}, "/api/v1/candidate/invitations/{id}/respond")

    conversations, conversations_body = client.request(
        "GET", "/api/v1/chat/conversations", candidate_token
    )
    _expect(conversations, {200}, "/api/v1/chat/conversations")
    for item in conversations_body or []:
        if isinstance(item, dict) and item.get("id"):
            return LoadState(profile_id, item["id"])
    raise RuntimeError("accepted invitation did not create an accessible chat conversation")


def _candidate_iteration(client: ApiClient, token: str, state: LoadState, rng: random.Random, vu: int, iteration: int) -> None:
    client.request("GET", "/api/v1/candidate/profile", token)
    client.request("GET", "/api/v1/candidate/dashboard", token)
    client.request("GET", "/api/v1/candidate/invitations", token)
    client.request("GET", "/api/v1/chat/conversations", token)
    client.request("GET", f"/api/v1/chat/conversations/{state.conversation_id}?limit=50", token)
    if iteration % 5 == 0:
        client.request(
            "PATCH",
            "/api/v1/candidate/profile",
            token,
            {"headline": f"Load-test engineer {vu}"},
        )
    if rng.random() < 0.2:
        client.request(
            "POST",
            f"/api/v1/chat/conversations/{state.conversation_id}/messages",
            token,
            {"body": f"load-test candidate message {vu}-{iteration}"},
        )


def _employer_iteration(client: ApiClient, token: str, state: LoadState, rng: random.Random, vu: int, iteration: int) -> None:
    client.request("GET", "/api/v1/employer/company", token)
    client.request("GET", "/api/v1/employer/hiring-need", token)
    client.request("GET", "/api/v1/employer/talent-radar?limit=30", token)
    client.request("GET", "/api/v1/employer/invitations", token)
    client.request("GET", "/api/v1/chat/conversations", token)
    client.request("GET", f"/api/v1/chat/conversations/{state.conversation_id}?limit=50", token)
    if rng.random() < 0.2:
        client.request(
            "POST",
            f"/api/v1/chat/conversations/{state.conversation_id}/messages",
            token,
            {"body": f"load-test employer message {vu}-{iteration}"},
        )


def percentile(values: Iterable[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def _metric_summary(rows: list[HttpResult]) -> dict[str, Any]:
    errors = [row for row in rows if row.status < 200 or row.status >= 300]
    by_endpoint: dict[str, list[HttpResult]] = defaultdict(list)
    for row in rows:
        by_endpoint[f"{row.method} {row.route.split('?')[0]}"].append(row)
    endpoint_summary = {}
    for key, endpoint_rows in sorted(by_endpoint.items()):
        endpoint_summary[key] = {
            "request_count": len(endpoint_rows),
            "error_count": sum(row.status < 200 or row.status >= 300 for row in endpoint_rows),
            "p50_seconds": percentile((row.seconds for row in endpoint_rows), 0.50),
            "p95_seconds": percentile((row.seconds for row in endpoint_rows), 0.95),
            "p99_seconds": percentile((row.seconds for row in endpoint_rows), 0.99),
        }
    read_rows = [row for row in rows if row.method == "GET" and row.route.split("?")[0] in COMMON_READ_ROUTES]
    search_rows = [row for row in rows if row.route.split("?")[0] == "/api/v1/employer/talent-radar"]
    write_rows = [row for row in rows if row.method in {"POST", "PATCH", "PUT"}]
    return {
        "request_count": len(rows),
        "error_count": len(errors),
        "error_rate": len(errors) / len(rows) if rows else 1.0,
        "p50_seconds": percentile((row.seconds for row in rows), 0.50),
        "p95_seconds": percentile((row.seconds for row in rows), 0.95),
        "p99_seconds": percentile((row.seconds for row in rows), 0.99),
        "common_read_p95_seconds": percentile((row.seconds for row in read_rows), 0.95),
        "search_p95_seconds": percentile((row.seconds for row in search_rows), 0.95),
        "write_p95_seconds": percentile((row.seconds for row in write_rows), 0.95),
        "endpoints": endpoint_summary,
    }


def threshold_result(metrics: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "error_rate_lt_1_percent": metrics["error_rate"] < 0.01,
        "common_read_p95_lte_1_second": metrics["common_read_p95_seconds"] <= 1.0,
        "search_p95_lte_2_seconds": metrics["search_p95_seconds"] <= 2.0,
        "write_p95_lte_1_5_seconds": metrics["write_p95_seconds"] <= 1.5,
    }
    return {"passed": all(checks.values()), "checks": checks}


def _docker_size_bytes(value: str) -> float | None:
    """Convert Docker's display size (for example ``108.9MiB``) to bytes."""

    match = _DOCKER_SIZE_RE.match(value.strip())
    if match is None:
        return None
    magnitude = float(match.group(1))
    unit = match.group(2).upper()
    units = {
        "B": 1,
        "KB": 1000,
        "MB": 1000**2,
        "GB": 1000**3,
        "TB": 1000**4,
        "PB": 1000**5,
        "EB": 1000**6,
        "KIB": 1024,
        "MIB": 1024**2,
        "GIB": 1024**3,
        "TIB": 1024**4,
        "PIB": 1024**5,
        "EIB": 1024**6,
    }
    multiplier = units.get(unit)
    return magnitude * multiplier if multiplier is not None else None


def _parse_docker_stats(path: Path) -> list[dict[str, Any]]:
    """Parse one raw Docker stats TSV while retaining display values."""

    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        fields = line.split("\t")
        if len(fields) != 4:
            continue
        container, cpu_display, memory_display, memory_percent_display = fields
        try:
            cpu_percent = float(cpu_display.rstrip("%"))
        except ValueError:
            cpu_percent = None
        memory_parts = [part.strip() for part in memory_display.split("/", 1)]
        memory_used_bytes = _docker_size_bytes(memory_parts[0]) if memory_parts else None
        memory_limit_bytes = _docker_size_bytes(memory_parts[1]) if len(memory_parts) == 2 else None
        try:
            memory_percent = float(memory_percent_display.rstrip("%"))
        except ValueError:
            memory_percent = None
        rows.append(
            {
                "container": container,
                "cpu_percent": cpu_percent,
                "cpu_display": cpu_display,
                "memory_used_bytes": memory_used_bytes,
                "memory_limit_bytes": memory_limit_bytes,
                "memory_usage_display": memory_display,
                "memory_percent": memory_percent,
                "memory_percent_display": memory_percent_display,
            }
        )
    return rows


def _resource_summary(output_dir: Path) -> dict[str, Any]:
    """Build report-safe CPU/RAM evidence from before/during/after snapshots."""

    phases = {
        phase: _parse_docker_stats(output_dir / f"{phase}-docker-stats.tsv")
        for phase in DOCKER_STAT_PHASES
    }
    rows = [row for phase_rows in phases.values() for row in phase_rows]
    cpu_values = [row["cpu_percent"] for row in rows if row["cpu_percent"] is not None]
    memory_values = [row["memory_used_bytes"] for row in rows if row["memory_used_bytes"] is not None]
    return {
        "available": bool(rows),
        "snapshot_phases": {phase: bool(rows) for phase, rows in phases.items()},
        "snapshots": phases,
        "peak_cpu_percent": max(cpu_values) if cpu_values else None,
        "peak_memory_used_bytes": max(memory_values) if memory_values else None,
    }


def _docker_snapshot(output_dir: Path, phase: str) -> None:
    try:
        ps = subprocess.run(
            ["docker", "compose", "ps", "--all"], capture_output=True, text=True, timeout=15, check=False
        )
        (output_dir / f"compose-{phase}.txt").write_text(ps.stdout, encoding="utf-8")
        ids = subprocess.run(
            ["docker", "compose", "ps", "-q", "backend", "frontend", "app-db", "keycloak"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        ).stdout.split()
        if ids:
            stats = subprocess.run(
                ["docker", "stats", "--no-stream", "--no-trunc", "--format", "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}", *ids],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            (output_dir / f"{phase}-docker-stats.tsv").write_text(
                "container\tcpu_percent\tmemory_usage\tmemory_percent\n" + stats.stdout,
                encoding="utf-8",
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        (output_dir / f"docker-{phase}-unavailable.txt").write_text(
            f"Docker snapshot unavailable: {type(error).__name__}\n", encoding="utf-8"
        )


def _write_host_specs(output_dir: Path, args: argparse.Namespace) -> None:
    lines = {
        "run_id": args.run_id,
        "base_url": args.base_url,
        "users": args.users,
        "duration_seconds": args.duration_seconds,
        "ramp_seconds": args.ramp_seconds,
        "user_pause_seconds": args.user_pause_seconds,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count() or 0,
    }
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        memory = next((line for line in meminfo.read_text(encoding="utf-8").splitlines() if line.startswith("MemTotal:")), None)
        if memory:
            lines["mem_total"] = memory
    (output_dir / "host-specs.txt").write_text(
        "".join(f"{key}={value}\n" for key, value in lines.items()), encoding="utf-8"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("FSP_LOAD_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--users", type=int, default=DEFAULT_TARGET_USERS)
    parser.add_argument("--duration-seconds", type=float, default=DEFAULT_TARGET_DURATION)
    parser.add_argument("--ramp-seconds", type=float, default=DEFAULT_RAMP)
    parser.add_argument("--user-pause-seconds", type=float, default=DEFAULT_PAUSE)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--seed", default="fsp-target-load-2026-10-10")
    parser.add_argument("--run-id", default=datetime.now(UTC).strftime("%Y%m%d-%H%M%S-load"))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--candidate-token-file")
    parser.add_argument("--employer-token-file")
    parser.add_argument("--candidate-token", action="append", default=[])
    parser.add_argument("--employer-token", action="append", default=[])
    parser.add_argument("--setup", action="store_true", help="prepare/reuse an accepted invitation and chat")
    parser.add_argument("--candidate-profile-id")
    parser.add_argument("--conversation-id")
    parser.add_argument("--skip-docker-stats", action="store_true")
    parser.add_argument("--fail-on-thresholds", action="store_true")
    args = parser.parse_args()
    if args.users < 1 or args.duration_seconds <= 0 or args.ramp_seconds < 0 or args.user_pause_seconds < 0:
        parser.error("users must be positive; duration, pause and ramp must be non-negative")
    return args


def main() -> int:
    args = _parse_args()
    try:
        candidates = load_token_pool(
            file_path=args.candidate_token_file,
            values=args.candidate_token,
            environment_name="FSP_LOAD_CANDIDATE_TOKENS",
            file_environment_name="FSP_LOAD_CANDIDATE_TOKEN_FILE",
        )
        employers = load_token_pool(
            file_path=args.employer_token_file,
            values=args.employer_token,
            environment_name="FSP_LOAD_EMPLOYER_TOKENS",
            file_environment_name="FSP_LOAD_EMPLOYER_TOKEN_FILE",
        )
        output_dir = args.output_dir or Path(".agent/runs") / args.run_id / "performance"
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_host_specs(output_dir, args)
        if not args.skip_docker_stats:
            _docker_snapshot(output_dir, "before")
        setup_client = ApiClient(args.base_url, timeout=args.timeout_seconds)
        if args.setup:
            state = prepare_state(setup_client, candidates.at(0), employers.at(0))
        elif args.candidate_profile_id and args.conversation_id:
            state = LoadState(args.candidate_profile_id, args.conversation_id)
        else:
            raise ValueError("use --setup or provide --candidate-profile-id and --conversation-id")
    except (OSError, ValueError, RuntimeError) as error:
        print(f"load setup failed: {error}", file=sys.stderr)
        return 2

    metrics = Metrics()
    client = ApiClient(args.base_url, metrics=metrics, timeout=args.timeout_seconds)
    stop = threading.Event()
    started = time.perf_counter()

    snapshot_thread: threading.Thread | None = None
    if not args.skip_docker_stats:
        def capture_during_snapshot() -> None:
            if stop.wait(max(0.0, args.duration_seconds / 2)):
                return
            _docker_snapshot(output_dir, "during")

        snapshot_thread = threading.Thread(target=capture_during_snapshot, name="load-resource-snapshot", daemon=True)
        snapshot_thread.start()

    def user(vu: int) -> None:
        role = "candidate" if vu % 2 == 0 else "employer"
        token = candidates.at(vu) if role == "candidate" else employers.at(vu)
        rng = random.Random(f"{args.seed}:{vu}")
        iteration = 0
        delay = args.ramp_seconds * vu / max(1, args.users - 1)
        if stop.wait(delay):
            return
        while not stop.is_set() and time.perf_counter() - started < args.duration_seconds:
            if role == "candidate":
                _candidate_iteration(client, token, state, rng, vu, iteration)
            else:
                _employer_iteration(client, token, state, rng, vu, iteration)
            iteration += 1
            stop.wait(args.user_pause_seconds * (0.75 + rng.random() * 0.5))

    threads = [threading.Thread(target=user, args=(vu,), name=f"load-vu-{vu}") for vu in range(args.users)]
    for thread in threads:
        thread.start()
    time.sleep(args.duration_seconds)
    stop.set()
    for thread in threads:
        thread.join(timeout=max(10.0, args.ramp_seconds + 10.0))
    if snapshot_thread is not None:
        snapshot_thread.join(timeout=30.0)
    if not args.skip_docker_stats:
        _docker_snapshot(output_dir, "after")

    rows = metrics.rows()
    metric_summary = _metric_summary(rows)
    thresholds = threshold_result(metric_summary)
    report = {
        "run_id": args.run_id,
        "scenario": "target" if args.users == DEFAULT_TARGET_USERS and args.duration_seconds == DEFAULT_TARGET_DURATION else "custom",
        "timed_seconds": round(time.perf_counter() - started, 3),
        "users": args.users,
        "seed": args.seed,
        "workload": "authenticated candidate/employer profile, discovery, invitation-list and matched-chat traffic",
        "metrics": metric_summary,
        "thresholds": thresholds,
        "resources": _resource_summary(output_dir),
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (output_dir / "request-times.tsv").open("w", encoding="utf-8") as output:
        output.write("method\troute\tstatus\tseconds\n")
        for row in rows:
            output.write(f"{row.method}\t{row.route.split('?')[0]}\t{row.status}\t{row.seconds:.6f}\n")
    (output_dir / "summary.txt").write_text(
        "\n".join(
            [
                f"run_id={args.run_id}",
                f"scenario={report['scenario']}",
                f"request_count={metric_summary['request_count']}",
                f"error_count={metric_summary['error_count']}",
                f"error_rate={metric_summary['error_rate']:.6f}",
                f"p50_seconds={metric_summary['p50_seconds']:.6f}",
                f"p95_seconds={metric_summary['p95_seconds']:.6f}",
                f"p99_seconds={metric_summary['p99_seconds']:.6f}",
                f"common_read_p95_seconds={metric_summary['common_read_p95_seconds']:.6f}",
                f"search_p95_seconds={metric_summary['search_p95_seconds']:.6f}",
                f"write_p95_seconds={metric_summary['write_p95_seconds']:.6f}",
                f"thresholds_passed={thresholds['passed']}",
                f"resource_snapshots_available={report['resources']['available']}",
                f"resource_peak_cpu_percent={report['resources']['peak_cpu_percent']}",
                f"resource_peak_memory_used_bytes={report['resources']['peak_memory_used_bytes']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not args.fail_on_thresholds or thresholds["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
