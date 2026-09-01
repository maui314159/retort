"""In-container v1 mechanical gate: pytest under coverage, python only.

Runs the workspace's own test suite where the build ran and records the
result into /tmp/score.json, which entrypoint.sh's finish() merges into
_sandbox_meta.json. Deliberately NOT full scorer parity — code_quality /
maintainability / idiomatic still come from the host scorer suite; this
gate only answers "do the tests run, and how many pass, in the sandbox".
"""

import json
import re
import subprocess


def main() -> None:
    r = subprocess.run(
        [
            "python3", "-m", "coverage", "run", "-m", "pytest",
            "-q", "--tb=no", "-p", "no:cacheprovider",
        ],
        cwd="/workspace",
        capture_output=True,
        text=True,
        timeout=600,
    )
    out = r.stdout + r.stderr
    print(out)

    passed = failed = 0
    m = re.search(r"(\d+) passed", out)
    if m:
        passed = int(m.group(1))
    m = re.search(r"(\d+) failed", out)
    if m:
        failed = int(m.group(1))

    cov = None
    try:
        subprocess.run(
            ["python3", "-m", "coverage", "json", "-o", "/tmp/cov.json"],
            cwd="/workspace",
            capture_output=True,
            timeout=120,
        )
        with open("/tmp/cov.json") as fh:
            cov = json.load(fh)["totals"]["percent_covered"]
    except Exception:  # noqa: BLE001 - coverage is best-effort beside pass/fail
        pass

    with open("/tmp/score.json", "w") as fh:
        json.dump(
            {
                "scored": True,
                "tests_passed": passed,
                "tests_total": passed + failed,
                "coverage_pct": round(cov, 2) if cov is not None else None,
            },
            fh,
        )


if __name__ == "__main__":
    main()
