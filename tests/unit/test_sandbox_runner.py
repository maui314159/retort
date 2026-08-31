"""SandboxRunner (AWS Batch/Fargate) unit tests — every AWS call mocked.

The single mocked seam is ``SandboxRunner._aws``; tests dispatch on the CLI
argument shape and fabricate Batch/S3 responses, including building a real
artifacts tarball for the download step. No test talks to AWS.
"""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

from retort.playpen.runner import StackConfig, TaskSpec
from retort.playpen.sandbox_runner import SandboxRunner, SandboxSpec

# One opencode step_finish line — the same shape test_runner.py pins for the
# opencode usage parser, so usage-delegation is tested against the real parser.
_STEP_FINISH = (
    '{"type":"step_finish","part":{"cost":0.005,"tokens":'
    '{"total":300,"input":250,"output":50,"reasoning":0,'
    '"cache":{"read":0,"write":0}}}}\n'
)


def _stack(agent: str = "opencode") -> StackConfig:
    return StackConfig(
        language="python", agent=agent, framework="stdlib",
        extra={"model": "openrouter/z-ai/glm-5.3-flash", "tooling": "none"},
    )


def _task() -> TaskSpec:
    return TaskSpec(name="t", description="d", prompt="Do the thing.")


def _make_runner(tmp_path: Path, **kwargs) -> SandboxRunner:
    defaults = dict(
        s3_bucket="bkt",
        image_digests={"python": "sha256:abc123"},
        spec=SandboxSpec(vcpu=2.0, memory_mb=8192),
        work_dir=tmp_path / "sbx",
        timeout_minutes=1,
        queue_grace_seconds=0,
        poll_seconds=0.0,
    )
    defaults.update(kwargs)
    runner = SandboxRunner(**defaults)
    runner._sleep = lambda _s: None
    return runner


def _artifact_tar(path: Path, files: dict[str, str]) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for name, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


def _wire_success(runner: SandboxRunner, *, artifacts: dict[str, str],
                  job_detail: dict | None = None) -> list[list[str]]:
    """Mock _aws for the happy path; returns the recorded call list."""
    calls: list[list[str]] = []
    detail = {"status": "SUCCEEDED", "createdAt": 1000, "startedAt": 31000}
    detail.update(job_detail or {})

    def fake_aws(args: list[str], *, parse_json: bool = True) -> dict:
        calls.append(args)
        if args[:2] == ["batch", "submit-job"]:
            return {"jobId": "job-1"}
        if args[:2] == ["batch", "describe-jobs"]:
            return {"jobs": [detail]}
        if args[:2] == ["s3", "cp"] and args[2].startswith("s3://"):
            _artifact_tar(Path(args[3]), artifacts)  # download out.tar.gz
            return {}
        return {}

    runner._aws = fake_aws  # type: ignore[method-assign]
    return calls


_META = json.dumps({"agent_exit": 0, "agent_seconds": 42.5})


class TestProvision:
    def test_seeds_workspace_and_opencode_config(self, tmp_path):
        pin = {"provider": {"order": ["z-ai"], "allow_fallbacks": False}}
        runner = _make_runner(tmp_path, model_options=pin)
        env_id = runner.provision(_stack(), _task())
        ws = runner._envs[env_id].workspace

        assert (ws / "TASK.md").read_text() == "Do the thing."
        stack_data = json.loads((ws / "stack.json").read_text())
        assert stack_data["model"] == "openrouter/z-ai/glm-5.3-flash"
        cfg = json.loads((ws / "opencode.json").read_text())
        entry = cfg["provider"]["openrouter"]["models"]["z-ai/glm-5.3-flash"]
        # The provider pin ships INSIDE the tarred workspace — the container
        # has no other config source.
        assert entry["options"] == pin
        assert cfg["permission"]["external_directory"] == {"*": "allow"}

    def test_tar_round_trip(self, tmp_path):
        from retort.playpen.sandbox_runner import _extract_tar, _make_tar

        src = tmp_path / "src"
        (src / "sub").mkdir(parents=True)
        (src / "a.txt").write_text("alpha")
        (src / "sub" / "b.txt").write_text("beta")
        tar = tmp_path / "ws.tar.gz"
        _make_tar(src, tar)
        dest = tmp_path / "dest"
        dest.mkdir()
        _extract_tar(tar, dest)
        assert (dest / "a.txt").read_text() == "alpha"
        assert (dest / "sub" / "b.txt").read_text() == "beta"


class TestExecute:
    def test_submit_job_structure(self, tmp_path):
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        calls = _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        })
        runner.execute(env_id, _stack(), _task())

        submit = next(c for c in calls if c[:2] == ["batch", "submit-job"])
        assert submit[submit.index("--job-queue") + 1] == "retort-sandbox"
        # Per-language job definition from the prefix.
        assert submit[submit.index("--job-definition") + 1] == \
            "retort-sandbox-python"
        overrides = json.loads(submit[submit.index("--container-overrides") + 1])
        reqs = {r["type"]: r["value"] for r in overrides["resourceRequirements"]}
        assert reqs == {"VCPU": "2.0", "MEMORY": "8192"}
        env = {e["name"]: e["value"] for e in overrides["environment"]}
        assert env["RETORT_S3_IN"].startswith(f"s3://bkt/runs/{env_id}/")
        assert env["RETORT_IMAGE_DIGEST"] == "sha256:abc123"
        cmd = json.loads(env["RETORT_AGENT_CMD"])
        assert cmd[:3] == ["opencode", "run", "--pure"]
        assert "openrouter/z-ai/glm-5.3-flash" in cmd
        # The input tar was uploaded before submit.
        upload = next(c for c in calls if c[:2] == ["s3", "cp"])
        assert upload[3] == env["RETORT_S3_IN"]

    def test_duration_from_meta_not_wall_time(self, tmp_path):
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        })
        artifacts = runner.execute(env_id, _stack(), _task())

        # In-container agent time, NOT the poll loop's wall time.
        assert artifacts.duration_seconds == 42.5
        assert artifacts.exit_code == 0
        # Queue latency recorded separately from Batch's own timestamps.
        assert artifacts.metadata["sandbox_queue_seconds"] == "30.0"

    def test_usage_delegates_to_opencode_parser(self, tmp_path):
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        })
        artifacts = runner.execute(env_id, _stack(), _task())

        assert artifacts.token_count == 300
        assert abs(float(artifacts.metadata["total_cost_usd"]) - 0.005) < 1e-9

    def test_provenance_metadata(self, tmp_path):
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        })
        artifacts = runner.execute(env_id, _stack(), _task())

        md = artifacts.metadata
        assert md["runner_lane"] == "sandbox"
        assert md["sandbox_image_digest"] == "sha256:abc123"
        assert md["sandbox_vcpu"] == "2.0"
        assert md["sandbox_memory_mb"] == "8192"
        assert md["sandbox_job_id"] == "job-1"

    def test_failed_job_carries_reason(self, tmp_path):
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())

        def fake_aws(args: list[str], *, parse_json: bool = True) -> dict:
            if args[:2] == ["batch", "submit-job"]:
                return {"jobId": "job-9"}
            if args[:2] == ["batch", "describe-jobs"]:
                return {"jobs": [{"status": "FAILED",
                                  "statusReason": "Essential container exited"}]}
            if args[:2] == ["s3", "cp"] and args[2].startswith("s3://"):
                raise RuntimeError("aws s3 cp failed (1): 404 not found")
            return {}

        runner._aws = fake_aws  # type: ignore[method-assign]
        artifacts = runner.execute(env_id, _stack(), _task())

        assert artifacts.exit_code == 1
        assert "FAILED" in artifacts.stderr
        assert "Essential container exited" in artifacts.stderr

    def test_timeout_terminates_job(self, tmp_path):
        runner = _make_runner(tmp_path, timeout_minutes=1)
        env_id = runner.provision(_stack(), _task())
        calls: list[list[str]] = []

        def fake_aws(args: list[str], *, parse_json: bool = True) -> dict:
            calls.append(args)
            if args[:2] == ["batch", "submit-job"]:
                return {"jobId": "job-slow"}
            if args[:2] == ["batch", "describe-jobs"]:
                return {"jobs": [{"status": "RUNNING"}]}
            return {}

        runner._aws = fake_aws  # type: ignore[method-assign]
        # Fake clock: each call advances 30s, so the 60s deadline passes.
        tick = {"t": 0.0}

        def fake_now() -> float:
            tick["t"] += 30.0
            return tick["t"]

        runner._now = fake_now  # type: ignore[method-assign]
        artifacts = runner.execute(env_id, _stack(), _task())

        assert artifacts.exit_code == 124
        assert "timed out" in artifacts.stderr
        assert any(c[:2] == ["batch", "terminate-job"] for c in calls)

    def test_missing_meta_is_harness_failure(self, tmp_path):
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        _wire_success(runner, artifacts={"_agent_stdout.log": _STEP_FINISH})
        artifacts = runner.execute(env_id, _stack(), _task())

        assert artifacts.exit_code == 1
        assert "_sandbox_meta.json" in artifacts.stderr

    def test_non_opencode_agent_rejected(self, tmp_path):
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(agent="hermes"), _task())
        artifacts = runner.execute(env_id, _stack(agent="hermes"), _task())

        assert artifacts.exit_code == 1
        assert "opencode" in artifacts.stderr


class TestTeardown:
    def test_removes_workspace_and_s3_prefix(self, tmp_path):
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        ws = runner._envs[env_id].workspace
        calls: list[list[str]] = []
        runner._aws = (  # type: ignore[method-assign]
            lambda args, *, parse_json=True: calls.append(args) or {}
        )
        runner.teardown(env_id)

        assert not ws.exists()
        assert any(c[:2] == ["s3", "rm"] and "--recursive" in c for c in calls)
