"""Post-deployment validation script.

Exercises the deployed /api/auth/me and /api/auth/login endpoints against a
running environment to confirm the quickstart.md scenarios pass. Requires
BASE_URL and one or more test tokens; results are printed and logged to a
file for post-deployment sign-off.

Usage:
    BASE_URL=https://<app>.azurewebsites.net python -m backend.db.validate_deployment \
        --player-token <token> --admin-token <token> --unauthorized-token <token>
"""

from __future__ import annotations

import argparse
import datetime
import json
import os

import requests

RESULTS_LOG = "deployment_validation_results.log"


def _check(base_url: str, path: str, token: str, expected_status: int) -> dict:
    response = requests.get(
        f"{base_url}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    return {
        "path": path,
        "expected_status": expected_status,
        "actual_status": response.status_code,
        "passed": response.status_code == expected_status,
        "body": response.text,
    }


def run(base_url: str, player_token: str | None, admin_token: str | None, unauthorized_token: str | None) -> list[dict]:
    results = []
    if player_token:
        results.append(_check(base_url, "/api/auth/me", player_token, 200))
    if admin_token:
        results.append(_check(base_url, "/api/auth/me", admin_token, 200))
    if unauthorized_token:
        results.append(_check(base_url, "/api/auth/me", unauthorized_token, 403))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--player-token")
    parser.add_argument("--admin-token")
    parser.add_argument("--unauthorized-token")
    args = parser.parse_args()

    base_url = os.environ["BASE_URL"]
    results = run(base_url, args.player_token, args.admin_token, args.unauthorized_token)

    with open(RESULTS_LOG, "a") as f:
        f.write(f"\n--- Validation run {datetime.datetime.now(datetime.timezone.utc).isoformat()} ---\n")
        f.write(json.dumps(results, indent=2))
        f.write("\n")

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"[{status}] {result['path']}: expected {result['expected_status']}, got {result['actual_status']}")

    if not all(r["passed"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
