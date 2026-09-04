#!/usr/bin/env python3
"""Post-deploy smoke tests. API_BASE_URL env, exit non-zero on failure.

Checks: /health, /health/db, OpenAPI docs, /admin/health aggregate,
/admin/metrics/prometheus exposition.
"""

import os
import sys
import urllib.request

BASE = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
CHECKS = [
    ("/health", 200, '"status": "ok"'),
    ("/health/db", 200, None),
    ("/docs", 200, None),
    ("/admin/health", 200, "services"),
    ("/admin/metrics/prometheus", 200, "bi_"),
]


def check(path: str, want_status: int, want_body: str | None) -> bool:
    try:
        with urllib.request.urlopen(BASE + path, timeout=15) as res:
            body = res.read().decode(errors="replace")
            ok = res.status == want_status and (want_body is None or want_body in body)
            print(("PASS" if ok else "FAIL"), path, res.status)
            return ok
    except Exception as exc:
        print("FAIL", path, exc)
        return False


def main() -> int:
    print("Smoke testing", BASE)
    results = [check(*c) for c in CHECKS]
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
