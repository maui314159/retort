"""§0c scorer-parity check, full-suite edition (run AFTER the v3 image push).

Takes one COMPLETED archived local workspace, copies it (read-only source),
ships it through a v3 sandbox cell whose "agent" is a no-op (`true`), so the
only thing the container does is run the REAL scorer suite — then compares
_container_scores.json against the archive's scores.json metric by metric.

Small numeric drift is acceptable (different toolchain builds); a pass/fail
FLIP on any metric is a parity failure. build_time is EXPECTED to differ
(different hardware) and is compared for presence, not value.

Usage: python sandbox/parity_check.py <archived-rep-dir> <bucket> <queue> \
          <job-definition> <region>
"""

import json
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

DRIFT_OK = 0.05          # absolute drift tolerated per metric
PRESENCE_ONLY = {"build_time", "token_efficiency"}  # hardware/usage-dependent


def aws(region: str, *args: str) -> str:
    proc = subprocess.run(
        ["aws", "--region", region, "--output", "json", *args],
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        raise SystemExit(f"aws {args[0]} failed: {proc.stderr[:500]}")
    return proc.stdout


def main() -> int:
    rep_dir, bucket, queue, jobdef, region = sys.argv[1:6]
    rep = Path(rep_dir)
    local_scores = json.loads((rep / "scores.json").read_text())

    env_id = f"retort-parity-{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td) / "ws"
        shutil.copytree(rep, ws)
        # The archive's own score artifacts must not leak into the rescore.
        for name in ("scores.json", "_container_scores.json"):
            (ws / name).unlink(missing_ok=True)
        tarball = Path(td) / "in.tar.gz"
        # python tarfile, NOT shell tar: macOS bsdtar writes AppleDouble
        # `._*` sidecars, which extract on Linux as real `*.py` files full of
        # non-UTF-8 bytes — scorers crash reading them and the collector
        # records 0.0 (measured 2026-09-01: defect_rate + maintainability
        # false-zeroed by `._db.py`). The runner's _make_tar already uses
        # tarfile and is immune.
        import tarfile

        with tarfile.open(tarball, "w:gz") as tar:
            for child in sorted(ws.iterdir()):
                tar.add(child, arcname=child.name)
        s3_in = f"s3://{bucket}/runs/{env_id}/in.tar.gz"
        s3_out = f"s3://{bucket}/runs/{env_id}/out.tar.gz"
        aws(region, "s3", "cp", str(tarball), s3_in)

        metrics = ",".join(sorted(set(local_scores) - {"_meta"}))
        job = json.loads(aws(
            region, "batch", "submit-job",
            "--job-name", env_id,
            "--job-queue", queue,
            "--job-definition", jobdef,
            "--timeout", json.dumps({"attemptDurationSeconds": 1800}),
            "--container-overrides", json.dumps({"environment": [
                {"name": "RETORT_S3_IN", "value": s3_in},
                {"name": "RETORT_S3_OUT", "value": s3_out},
                {"name": "RETORT_AGENT_CMD", "value": json.dumps(["true"])},
                {"name": "RETORT_ENV_ID", "value": env_id},
                {"name": "RETORT_LANGUAGE", "value": "python"},
                {"name": "RETORT_MODEL", "value": "parity-check"},
                {"name": "RETORT_SCORE_IN_CONTAINER", "value": "1"},
                {"name": "RETORT_RESPONSES", "value": metrics},
                {"name": "RETORT_STALL_SECONDS", "value": "0"},
                {"name": "RETORT_AGENT_TIMEOUT_SECONDS", "value": "60"},
            ]}),
        ))
        job_id = job["jobId"]
        print(f"parity job {job_id} ({env_id}), metrics: {metrics}")

        while True:
            detail = json.loads(aws(
                region, "batch", "describe-jobs", "--jobs", job_id
            ))["jobs"][0]
            if detail["status"] in ("SUCCEEDED", "FAILED"):
                break
            time.sleep(15)
        print("job status:", detail["status"])

        out_tar = Path(td) / "out.tar.gz"
        aws(region, "s3", "cp", s3_out, str(out_tar))
        out_dir = Path(td) / "out"
        out_dir.mkdir()
        subprocess.run(
            ["tar", "-C", str(out_dir), "-xzf", str(out_tar)], check=True
        )
        container = json.loads((out_dir / "_container_scores.json").read_text())
        aws(region, "s3", "rm", f"s3://{bucket}/runs/{env_id}", "--recursive")

    flips = 0
    print(f"{'metric':<20}{'local':>10}{'container':>12}  verdict")
    for name, local_val in sorted(local_scores.items()):
        if not isinstance(local_val, (int, float)):
            continue
        c_val = container.get(name)
        if name in PRESENCE_ONLY:
            verdict = "present" if c_val is not None else "MISSING"
        elif c_val is None:
            verdict = "MISSING"
            flips += 1
        elif abs(float(c_val) - float(local_val)) <= DRIFT_OK:
            verdict = "ok"
        elif (float(c_val) >= 0.5) == (float(local_val) >= 0.5):
            verdict = f"drift {abs(float(c_val) - float(local_val)):.3f}"
        else:
            verdict = "FLIP"
            flips += 1
        c_txt = "-" if c_val is None else f"{float(c_val):.3f}"
        print(f"{name:<20}{float(local_val):>10.3f}{c_txt:>12}  {verdict}")

    print("PARITY:", "PASS" if flips == 0 else f"FAIL ({flips} flip/missing)")
    return 0 if flips == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
