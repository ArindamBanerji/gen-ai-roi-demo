#!/usr/bin/env python3
"""
scripts/validate_contracts.py — API contract validator.

Reads contracts/api_contracts.yaml and hits every endpoint against
a running backend. Reports PASS/FAIL per endpoint.

Usage:
    python scripts/validate_contracts.py --port 8001 --verbose
    python scripts/validate_contracts.py --port 8001 --tab AlertTriageTab
"""
import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

import yaml


def load_contracts(path: Path) -> list:
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("endpoints", [])


def _resolve_queue_alert_id(base_url: str) -> str:
    """GET /api/alerts/queue and return the first alert's id, or 'SIM-001' fallback."""
    try:
        req = urllib.request.Request(f"{base_url}/api/alerts/queue", method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        alerts = data.get("alerts", [])
        if alerts:
            return alerts[0].get("id", "SIM-001")
    except Exception:
        pass
    return "SIM-001"


# Cache so we only fetch once per run
_cached_alert_id = {}


def _get_queue_alert_id(base_url: str) -> str:
    if "id" not in _cached_alert_id:
        _cached_alert_id["id"] = _resolve_queue_alert_id(base_url)
    return _cached_alert_id["id"]


def validate_endpoint(base_url: str, ep: dict, verbose: bool) -> dict:
    """Hit one endpoint and check status + required fields."""
    path = ep["path"]
    method = ep.get("method", "GET")
    body = ep.get("body")
    required = ep.get("required_fields", [])
    url = f"{base_url}{path}"

    # Resolve __FROM_QUEUE__ placeholders with a real alert_id
    if body and "__FROM_QUEUE__" in json.dumps(body):
        real_id = _get_queue_alert_id(base_url)
        body = json.loads(json.dumps(body).replace("__FROM_QUEUE__", real_id))

    result = {
        "path": path,
        "method": method,
        "status": None,
        "pass": False,
        "missing_fields": [],
        "error": None,
    }

    try:
        if method == "POST":
            data = json.dumps(body or {}).encode("utf-8")
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        else:
            req = urllib.request.Request(url, method="GET")

        with urllib.request.urlopen(req, timeout=15) as resp:
            result["status"] = resp.status
            resp_body = resp.read().decode("utf-8")

        # Check for non-JSON responses (PDF, CSV, etc.)
        try:
            resp_json = json.loads(resp_body)
        except json.JSONDecodeError:
            # Non-JSON 200 is still a pass if no required fields
            if not required:
                result["pass"] = True
            else:
                result["error"] = "Response is not JSON"
            return result

        # Check required fields
        missing = []
        for field in required:
            if field not in resp_json:
                missing.append(field)

        result["missing_fields"] = missing
        result["pass"] = len(missing) == 0

        if verbose and not result["pass"]:
            result["actual_keys"] = list(resp_json.keys())[:20]

    except urllib.error.HTTPError as e:
        result["status"] = e.code
        result["error"] = f"HTTP {e.code}: {e.reason}"
        try:
            err_body = e.read().decode("utf-8")[:200]
            result["error_detail"] = err_body
        except Exception:
            pass

    except urllib.error.URLError as e:
        result["error"] = f"Connection failed: {e.reason}"

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"

    return result


def main():
    parser = argparse.ArgumentParser(description="Validate API contracts")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--tab", help="Only validate endpoints for this tab")
    parser.add_argument(
        "--contracts",
        default=str(Path(__file__).parents[1] / "contracts" / "api_contracts.yaml"),
    )
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    contracts_path = Path(args.contracts)

    if not contracts_path.exists():
        print(f"FATAL: {contracts_path} not found")
        sys.exit(1)

    endpoints = load_contracts(contracts_path)

    # Filter by tab if requested
    if args.tab:
        endpoints = [
            ep for ep in endpoints
            if args.tab in ep.get("consumed_by", [])
        ]

    print(f"Validating {len(endpoints)} endpoints against {base_url}")
    print("=" * 70)

    passed = 0
    failed = 0
    errors = []

    for ep in endpoints:
        result = validate_endpoint(base_url, ep, args.verbose)

        if result["pass"]:
            passed += 1
            status_str = f"\033[32mPASS\033[0m"
        else:
            failed += 1
            status_str = f"\033[31mFAIL\033[0m"
            errors.append(result)

        status_code = result["status"] or "---"
        print(f"  {status_str}  {result['method']:4s} {result['path']:<50s} [{status_code}]")

        if args.verbose and not result["pass"]:
            if result.get("error"):
                print(f"         Error: {result['error']}")
            if result.get("error_detail"):
                print(f"         Detail: {result['error_detail'][:150]}")
            if result.get("missing_fields"):
                print(f"         Missing: {result['missing_fields']}")
            if result.get("actual_keys"):
                print(f"         Got keys: {result['actual_keys']}")

    print("=" * 70)
    print(f"TOTAL: {passed} passed, {failed} failed, {len(endpoints)} total")

    if errors:
        print(f"\n--- FAILURES ---")
        for e in errors:
            msg = e.get("error") or f"missing fields: {e['missing_fields']}"
            print(f"  {e['method']:4s} {e['path']}: {msg}")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
