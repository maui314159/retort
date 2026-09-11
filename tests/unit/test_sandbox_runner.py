"""SandboxRunner (AWS Batch/Fargate) unit tests — every AWS call mocked.

The single mocked seam is ``SandboxRunner._aws``; tests dispatch on the CLI
argument shape and fabricate Batch/S3 responses, including building a real
artifacts tarball for the download step. No test talks to AWS.
"""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

from retort.playpen.runner import StackConfig, TaskSpec
from retort.playpen.sandbox_runner import SandboxRunner, SandboxSpec

# One opencode step_finish line — the same shape test_runner.py pins for the
# opencode usage parser, so usage-delegation is tested against the real parser.
_STEP_FINISH = (
    '{"type":"step_finish","part":{"cost":0.005,"tokens":'
    '{"total":300,"input":250,"output":50,"reasoning":0,'
    '"cache":{"read":0,"write":0}}}}\n'
)


_ECR = "1.dkr.ecr.us-east-1.amazonaws.com"
# tag -> digest, as `aws ecr describe-images --image-ids imageTag=<tag>` would
# answer. python-v4c is the tag the default fake job definition names, and it
# resolves to the digest _make_runner pins — the happy path.
_ECR_TAGS = {
    "imageTag=python-v4c": "sha256:abc123",
    "imageTag=python-v5": "sha256:def456",
}


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

    # No unit test may reach a real AWS account. Every test that needs the
    # seam wires a fake (see _wire_success); this default catches the ones
    # that forgot (the first preflight-image check did exactly that).
    def _no_aws(args: list[str], *, parse_json: bool = True) -> dict:
        raise AssertionError(f"real aws would have been called: {args[:3]}")

    runner._aws = _no_aws  # type: ignore[method-assign]
    return runner


# What `describe-job-definitions` returns for the default fake: one ACTIVE
# revision naming the python-v4c tag, which resolves to the pinned digest.
def _jobdef(tag: str = "python-v4c", revision: int = 8) -> dict:
    return {"jobDefinitionName": "retort-sandbox-python", "revision": revision,
            "containerProperties": {"image": f"{_ECR}/retort-sandbox:{tag}"}}


def _artifact_tar(path: Path, files: dict[str, str]) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for name, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


def _wire_success(runner: SandboxRunner, *, artifacts: dict[str, str],
                  job_detail: dict | None = None,
                  jobdefs: list[dict] | None = None) -> list[list[str]]:
    """Mock _aws for the happy path; returns the recorded call list."""
    calls: list[list[str]] = []
    # What Batch reports for a real job: the job definition it resolved (name +
    # revision) and the image URI that definition names — by TAG, which is the
    # whole reason the runner has to resolve it against ECR.
    detail = {
        "status": "SUCCEEDED", "createdAt": 1000, "startedAt": 31000,
        "jobDefinition": "arn:aws:batch:r:1:job-definition/retort-sandbox-python:8",
        "container": {"image": f"{_ECR}/retort-sandbox:python-v4c"},
    }
    detail.update(job_detail or {})

    def fake_aws(args: list[str], *, parse_json: bool = True) -> dict:
        calls.append(args)
        if args[:2] == ["batch", "submit-job"]:
            return {"jobId": "job-1"}
        if args[:2] == ["batch", "describe-jobs"]:
            return {"jobs": [detail]}
        if args[:2] == ["batch", "describe-job-definitions"]:
            return {"jobDefinitions": jobdefs if jobdefs is not None else [_jobdef()]}
        if args[:2] == ["ecr", "describe-images"]:
            return {"imageDetails": [{"imageDigest": _ECR_TAGS.get(
                args[args.index("--image-ids") + 1], "")}]}
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


class TestInContainerScoring:
    def test_score_flag_flips_env(self, tmp_path):
        runner = _make_runner(tmp_path, score_in_container=True)
        calls = _wire_success(runner, artifacts={"_sandbox_meta.json": _META})
        env_id = runner.provision(_stack(), _task())
        runner.execute(env_id, _stack(), _task())

        submit = next(c for c in calls if c[:2] == ["batch", "submit-job"])
        overrides = json.loads(submit[submit.index("--container-overrides") + 1])
        env = {e["name"]: e["value"] for e in overrides["environment"]}
        assert env["RETORT_SCORE_IN_CONTAINER"] == "1"

    def test_scoring_defaults_on_and_can_be_disabled(self, tmp_path):
        # In-container scores are authoritative for container lanes (Phase 2),
        # so scoring in the container is the default; off is an explicit choice.
        runner = _make_runner(tmp_path)
        calls = _wire_success(runner, artifacts={"_sandbox_meta.json": _META})
        env_id = runner.provision(_stack(), _task())
        runner.execute(env_id, _stack(), _task())
        submit = next(c for c in calls if c[:2] == ["batch", "submit-job"])
        overrides = json.loads(submit[submit.index("--container-overrides") + 1])
        env = {e["name"]: e["value"] for e in overrides["environment"]}
        assert env["RETORT_SCORE_IN_CONTAINER"] == "1"

        runner = _make_runner(tmp_path, score_in_container=False)
        calls = _wire_success(runner, artifacts={"_sandbox_meta.json": _META})
        env_id = runner.provision(_stack(), _task())
        runner.execute(env_id, _stack(), _task())
        submit = next(c for c in calls if c[:2] == ["batch", "submit-job"])
        overrides = json.loads(submit[submit.index("--container-overrides") + 1])
        env = {e["name"]: e["value"] for e in overrides["environment"]}
        assert env["RETORT_SCORE_IN_CONTAINER"] == "0"

    def test_score_meta_surfaced_in_artifacts(self, tmp_path):
        meta = json.dumps({
            "agent_exit": 0, "agent_seconds": 7.0, "scored": True,
            "tests_passed": 5, "tests_total": 6, "coverage_pct": 83.1,
        })
        runner = _make_runner(tmp_path, score_in_container=True)
        _wire_success(runner, artifacts={"_sandbox_meta.json": meta})
        env_id = runner.provision(_stack(), _task())
        art = runner.execute(env_id, _stack(), _task())

        assert art.metadata["sandbox_tests_passed"] == "5"
        assert art.metadata["sandbox_tests_total"] == "6"
        assert art.metadata["sandbox_coverage_pct"] == "83.1"

    def test_no_score_keys_when_not_scored(self, tmp_path):
        runner = _make_runner(tmp_path)
        _wire_success(runner, artifacts={"_sandbox_meta.json": _META})
        env_id = runner.provision(_stack(), _task())
        art = runner.execute(env_id, _stack(), _task())

        assert "sandbox_tests_passed" not in art.metadata


class TestTimeoutAndStallParity:
    def test_batch_timeout_derived_from_playpen_timeout(self, tmp_path):
        runner = _make_runner(tmp_path, timeout_minutes=90)
        env_id = runner.provision(_stack(), _task())
        calls = _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        })
        runner.execute(env_id, _stack(), _task())

        submit = next(c for c in calls if c[:2] == ["batch", "submit-job"])
        timeout = json.loads(submit[submit.index("--timeout") + 1])
        # playpen.timeout_minutes + the setup/transfer margin — never the job
        # definition's baked-in default.
        assert timeout["attemptDurationSeconds"] == 90 * 60 + 600

    def test_stall_and_wall_env_reach_container(self, tmp_path):
        runner = _make_runner(tmp_path, timeout_minutes=40, stall_minutes=25)
        env_id = runner.provision(_stack(), _task())
        calls = _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        })
        runner.execute(env_id, _stack(), _task())

        submit = next(c for c in calls if c[:2] == ["batch", "submit-job"])
        overrides = json.loads(submit[submit.index("--container-overrides") + 1])
        env = {e["name"]: e["value"] for e in overrides["environment"]}
        assert env["RETORT_STALL_SECONDS"] == str(25 * 60)
        assert env["RETORT_AGENT_TIMEOUT_SECONDS"] == str(40 * 60)

    def test_stall_kill_surfaces_like_local_lane(self, tmp_path):
        meta = json.dumps({
            "agent_exit": 124, "agent_seconds": 1810.0, "kill_reason": "stall",
        })
        runner = _make_runner(tmp_path, stall_minutes=25)
        env_id = runner.provision(_stack(), _task())
        _wire_success(runner, artifacts={
            "_sandbox_meta.json": meta, "_agent_stdout.log": _STEP_FINISH,
        })
        art = runner.execute(env_id, _stack(), _task())

        # Same contract as the local progress guard: exit 124, kill_reason in
        # metadata, the stall message in stderr — diagnose sees one shape.
        assert art.exit_code == 124
        assert art.metadata["kill_reason"] == "stall"
        assert "stalled" in art.stderr
        assert art.duration_seconds == 1810.0
        # Usage still parsed — a killed agent's spend is real spend.
        assert art.token_count == 300


class TestImageIdentity:
    """The digest in provenance must be what RAN, not what the yaml says.

    Job definitions name images by tag and the runner submits the latest
    revision, so the configured digest and the running image can diverge
    silently. Every path here is the config-vs-effective check.
    """

    def test_effective_digest_and_jobdef_recorded(self, tmp_path):
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        })
        art = runner.execute(env_id, _stack(), _task())

        assert art.exit_code == 0
        assert art.metadata["sandbox_image_digest"] == "sha256:abc123"
        assert art.metadata["sandbox_image_digest_effective"] == "sha256:abc123"
        assert art.metadata["sandbox_job_definition"] == "retort-sandbox-python:8"

    def test_preflight_cache_is_reused_after_the_job(self, tmp_path):
        """One ECR lookup per language per run: the post-job check reuses
        what check_design resolved instead of paying (and risking) a
        describe-images call per cell."""
        runner = _make_runner(tmp_path)
        calls = _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        })
        assert runner.check_design([{"language": "python", "agent": "opencode"}]) == []
        for _ in range(2):
            env_id = runner.provision(_stack(), _task())
            art = runner.execute(env_id, _stack(), _task())
            assert art.exit_code == 0
            assert art.metadata["sandbox_image_digest_effective"] == "sha256:abc123"
        ecr_calls = [c for c in calls if c[:2] == ["ecr", "describe-images"]]
        assert len(ecr_calls) == 1

    def test_aws_timeout_is_a_clean_failure_not_a_traceback(self, tmp_path):
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())

        def hung(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd, kw.get("timeout", 300))
        # go through the REAL _aws so the timeout conversion is what's tested
        runner._aws = type(runner)._aws.__get__(runner)  # type: ignore[method-assign]
        import retort.playpen.sandbox_runner as mod
        orig = mod.subprocess.run
        mod.subprocess.run = hung
        try:
            art = runner.execute(env_id, _stack(), _task())
        finally:
            mod.subprocess.run = orig
        assert art.exit_code == 1
        assert "timed out" in art.stderr

    def test_mismatch_is_a_harness_failure(self, tmp_path):
        # Someone registered revision 9 with python-v5 and forgot the yaml.
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        }, job_detail={
            "jobDefinition": "arn:aws:batch:r:1:job-definition/retort-sandbox-python:9",
            "container": {"image": f"{_ECR}/retort-sandbox:python-v5"},
        })
        art = runner.execute(env_id, _stack(), _task())

        assert art.exit_code == 1
        assert art.stderr.startswith("HARNESS:")
        assert "image mismatch" in art.stderr
        assert "retort-sandbox-python:9" in art.stderr
        # Both identities recorded so the archive shows exactly what diverged.
        assert art.metadata["sandbox_image_digest"] == "sha256:abc123"
        assert art.metadata["sandbox_image_digest_effective"] == "sha256:def456"
        # Never a data point: no duration, no usage.
        assert art.duration_seconds == 0.0
        assert art.token_count == 0
        # The workspace was still pulled, so the cell stays diagnosable.
        assert (art.output_dir / "_sandbox_meta.json").exists()

    def test_unverifiable_pin_fails_closed(self, tmp_path):
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        }, job_detail={"container": {}})
        art = runner.execute(env_id, _stack(), _task())

        assert art.exit_code == 1
        assert "cannot be verified" in art.stderr

    def test_unpinned_records_effective_without_failing(self, tmp_path):
        # No configured digest: the honest state is "unpinned, and here is what
        # ran" — recorded, not hidden, and not an error.
        runner = _make_runner(tmp_path, image_digests={})
        env_id = runner.provision(_stack(), _task())
        _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        })
        art = runner.execute(env_id, _stack(), _task())

        assert art.exit_code == 0
        assert art.metadata["sandbox_image_digest"] == "unpinned"
        assert art.metadata["sandbox_image_digest_effective"] == "sha256:abc123"

    def test_digest_reference_needs_no_ecr_lookup(self, tmp_path):
        # A job definition registered BY DIGEST (the bootstrap's new default)
        # carries the identity in the URI itself.
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        calls = _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        }, job_detail={
            "container": {"image": f"{_ECR}/retort-sandbox@sha256:abc123"},
        })
        art = runner.execute(env_id, _stack(), _task())

        assert art.exit_code == 0
        assert art.metadata["sandbox_image_digest_effective"] == "sha256:abc123"
        assert not any(c[:2] == ["ecr", "describe-images"] for c in calls)

    def test_container_witnesses_surface_in_metadata(self, tmp_path):
        meta = json.dumps({
            "agent_exit": 0, "agent_seconds": 10.0,
            "container_image_id": "sha256:cfg999",
            "cpu_model": "Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz",
            "availability_zone": "us-east-1c",
        })
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        _wire_success(runner, artifacts={
            "_sandbox_meta.json": meta, "_agent_stdout.log": _STEP_FINISH,
        })
        art = runner.execute(env_id, _stack(), _task())

        assert art.metadata["sandbox_container_image_id"] == "sha256:cfg999"
        assert art.metadata["sandbox_cpu_model"].startswith("Intel(R) Xeon")
        assert art.metadata["sandbox_az"] == "us-east-1c"


class _FakeProc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


_INSPECT_OK = f"{_ECR}/retort-sandbox@sha256:abc123|sha256:cfg1"
_INSPECT_OTHER = f"{_ECR}/retort-sandbox@sha256:def456|sha256:cfg2"


def _wire_docker(runner: SandboxRunner, *, meta: str | None = _META,
                 stdout_log: str = _STEP_FINISH, inspect: str = _INSPECT_OK,
                 run_rc: int = 0,
                 run_raises: Exception | None = None) -> list[list[str]]:
    """Mock the docker seam: `image inspect` answers `inspect`; `run` writes
    the files the entrypoint would have left in the bind-mounted workspace."""
    calls: list[list[str]] = []

    def fake_docker(args: list[str], *, timeout: float):
        calls.append(args)
        if args[:2] == ["image", "inspect"]:
            return _FakeProc(0, inspect + "\n")
        if args[0] == "run":
            if run_raises is not None:
                raise run_raises
            ws = Path(args[args.index("-v") + 1].split(":", 1)[0])
            if meta is not None:
                (ws / "_sandbox_meta.json").write_text(meta)
            (ws / "_agent_stdout.log").write_text(stdout_log)
            return _FakeProc(run_rc, "", "container stderr")
        return _FakeProc(0)

    runner._docker = fake_docker  # type: ignore[method-assign]
    return calls


class TestDockerBackend:
    """backend=docker: the same image + entrypoint under a local `docker run`,
    workspace bind-mounted, no AWS, its own lane stamp."""

    def test_hung_daemon_at_inspect_is_a_harness_artifact(self, tmp_path):
        runner = self._runner(tmp_path)
        env_id = runner.provision(_stack(), _task())

        def hung(args, *, timeout):
            raise subprocess.TimeoutExpired(args, timeout)
        runner._docker = hung  # type: ignore[method-assign]
        art = runner.execute(env_id, _stack(), _task())
        assert art.exit_code == 1
        assert art.stderr.startswith("HARNESS:")
        assert art.metadata["runner_lane"] == "docker-local"

    def _runner(self, tmp_path, **kw):
        defaults = dict(backend="docker", s3_bucket="",
                        docker_images={"python": "retort-sandbox:python-v4c"})
        defaults.update(kw)
        return _make_runner(tmp_path, **defaults)

    def test_invalid_backend_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="backend"):
            _make_runner(tmp_path, backend="fargate-ish")

    def test_run_command_shape_and_no_aws(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-secret")
        runner = self._runner(tmp_path)

        def no_aws(*a, **k):
            raise AssertionError("aws called under backend=docker")
        runner._aws = no_aws  # type: ignore[method-assign]

        env_id = runner.provision(_stack(), _task())
        calls = _wire_docker(runner)
        art = runner.execute(env_id, _stack(), _task())

        assert art.exit_code == 0
        run = next(c for c in calls if c[0] == "run")
        assert run[1:3] == ["--rm", "--name"] and run[3] == env_id
        assert run[run.index("--platform") + 1] == "linux/amd64"
        assert run[run.index("--cpus") + 1] == "2.0"
        assert run[run.index("--memory") + 1] == "8192m"
        assert run[run.index("-v") + 1] == f"{runner.work_dir / env_id}:/workspace"
        assert run[-1] == "retort-sandbox:python-v4c"
        env = {}
        for i, tok in enumerate(run):
            if tok == "-e" and "=" in run[i + 1]:
                k, v = run[i + 1].split("=", 1)
                env[k] = v
        # Same RETORT_* contract as the Batch lane, minus the S3 locations.
        assert "RETORT_S3_IN" not in env and "RETORT_S3_OUT" not in env
        assert env["RETORT_ENV_ID"] == env_id
        assert env["RETORT_IMAGE_DIGEST"] == "sha256:abc123"
        assert json.loads(env["RETORT_AGENT_CMD"])[:2] == ["opencode", "run"]
        # The secret is forwarded by NAME only — never its value on argv.
        assert "OPENROUTER_API_KEY" in run
        assert not any("sk-secret" in tok for tok in run)

    def test_lane_stamp_and_collect_parity_with_batch(self, tmp_path):
        runner = self._runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        _wire_docker(runner)
        art = runner.execute(env_id, _stack(), _task())

        md = art.metadata
        assert md["runner_lane"] == "docker-local"      # never pooled
        assert md["sandbox_job_id"] == env_id
        assert md["sandbox_docker_image"] == "retort-sandbox:python-v4c"
        assert md["sandbox_container_exit"] == "0"
        assert art.duration_seconds == 42.5              # in-container, from meta
        assert art.token_count == 300                    # shared usage parser
        stderr_log = art.output_dir / "_container_stderr.log"
        assert stderr_log.read_text() == "container stderr"

    def test_effective_digest_from_inspect_and_mismatch_blocks_run(self, tmp_path):
        runner = self._runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        calls = _wire_docker(runner, inspect=_INSPECT_OTHER)
        art = runner.execute(env_id, _stack(), _task())

        assert art.exit_code == 1
        assert "image mismatch" in art.stderr
        assert art.metadata["sandbox_image_digest_effective"] == "sha256:def456"
        assert art.metadata["sandbox_container_image_id"] == "sha256:cfg2"
        assert not any(c[0] == "run" for c in calls)    # refused BEFORE running

    def test_local_build_unpinned_ok_pinned_refused(self, tmp_path):
        # A locally built image has no RepoDigests: fine unpinned, refused pinned.
        runner = self._runner(tmp_path, image_digests={})
        env_id = runner.provision(_stack(), _task())
        _wire_docker(runner, inspect="|sha256:localcfg")
        art = runner.execute(env_id, _stack(), _task())
        assert art.exit_code == 0
        assert art.metadata["sandbox_image_digest"] == "unpinned"
        assert art.metadata["sandbox_container_image_id"] == "sha256:localcfg"
        assert "sandbox_image_digest_effective" not in art.metadata

        pinned = self._runner(tmp_path)
        env_id = pinned.provision(_stack(), _task())
        _wire_docker(pinned, inspect="|sha256:localcfg")
        art = pinned.execute(env_id, _stack(), _task())
        assert art.exit_code == 1 and "local build" in art.stderr

    def test_missing_image_for_language_is_harness(self, tmp_path):
        runner = self._runner(tmp_path, docker_images={"go": "retort-sandbox:go-v3b"})
        env_id = runner.provision(_stack(), _task())
        _wire_docker(runner)
        art = runner.execute(env_id, _stack(), _task())
        assert art.exit_code == 1 and "no docker image configured" in art.stderr

    def test_timeout_kills_container(self, tmp_path):
        runner = self._runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        calls = _wire_docker(runner, run_raises=subprocess.TimeoutExpired("docker", 1))
        art = runner.execute(env_id, _stack(), _task())
        assert art.exit_code == 124
        assert ["kill", env_id] in calls

    def test_missing_meta_is_harness_failure(self, tmp_path):
        runner = self._runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        _wire_docker(runner, meta=None, run_rc=137)
        art = runner.execute(env_id, _stack(), _task())
        assert art.exit_code == 1
        assert "exited 137" in art.stderr
        assert "entrypoint did not complete" in art.stderr

    def test_teardown_touches_no_s3(self, tmp_path):
        runner = self._runner(tmp_path)

        def no_aws(*a, **k):
            raise AssertionError("aws called in docker teardown")
        runner._aws = no_aws  # type: ignore[method-assign]
        env_id = runner.provision(_stack(), _task())
        runner.teardown(env_id)
        assert not (runner.work_dir / env_id).exists()

    def test_schema_backend_requirements(self):
        from retort.config.schema import SandboxConfig
        SandboxConfig(backend="docker", docker_images={"python": "img"})
        SandboxConfig(s3_bucket="bkt")
        with pytest.raises(ValueError, match="s3_bucket"):
            SandboxConfig()
        with pytest.raises(ValueError, match="docker_images"):
            SandboxConfig(backend="docker")


class TestDesignPreflight:
    """check_design(): refuse every factor level the lane would silently drop."""

    def test_runnable_design_has_no_problems(self, tmp_path):
        runner = _make_runner(tmp_path)
        calls = _wire_success(runner, artifacts={})
        rcs = [
            {"language": "python", "agent": "opencode", "model": "m",
             "tooling": "none"},
            {"language": "go", "agent": "prime", "model": "m", "prompt": "none"},
        ]
        assert runner.check_design(rcs) == []
        # python is pinned: its job definition was resolved ONCE, before any
        # submit. go is unpinned: nothing to verify, no lookup.
        jobdef_calls = [c for c in calls if c[:2] == ["batch", "describe-job-definitions"]]
        assert [c[c.index("--job-definition-name") + 1] for c in jobdef_calls] == [
            "retort-sandbox-python"
        ]
        assert not any(c[:2] == ["batch", "submit-job"] for c in calls)

    def test_pin_mismatch_is_refused_before_any_submit(self, tmp_path):
        """The whole point of Phase 0: a grid must not run on the wrong image
        at full Batch cost and then be discovered afterwards."""
        runner = _make_runner(tmp_path)
        calls = _wire_success(runner, artifacts={}, jobdefs=[_jobdef("python-v5", 9)])
        problems = runner.check_design([{"language": "python", "agent": "opencode"}])
        assert len(problems) == 1
        assert "retort-sandbox-python:9" in problems[0]
        assert "sha256:def456" in problems[0] and "sha256:abc123" in problems[0]
        assert not any(c[:2] == ["batch", "submit-job"] for c in calls)

    def test_unverifiable_pin_is_refused_before_any_submit(self, tmp_path):
        runner = _make_runner(tmp_path)

        def denied(args, *, parse_json=True):
            if args[:2] == ["batch", "describe-job-definitions"]:
                raise RuntimeError("AccessDeniedException: batch:DescribeJobDefinitions")
            return {}
        runner._aws = denied
        problems = runner.check_design([{"language": "python", "agent": "opencode"}])
        assert len(problems) == 1
        assert "cannot verify the pinned image" in problems[0]
        assert "AccessDenied" in problems[0]

    def test_unpinned_language_makes_no_aws_call(self, tmp_path):
        runner = _make_runner(tmp_path, image_digests={})  # _make_runner's _aws raises
        assert runner.check_design([{"language": "go", "agent": "opencode"}]) == []

    def test_scoring_off_is_refused(self, tmp_path):
        runner = _make_runner(tmp_path, image_digests={}, score_in_container=False)
        problems = runner.check_design([{"language": "go", "agent": "opencode"}])
        assert len(problems) == 1
        assert "score_in_container" in problems[0]

    def test_docker_backend_verifies_images_at_preflight(self, tmp_path):
        runner = _make_runner(
            tmp_path, backend="docker", image_digests={},
            docker_images={"python": "retort-sandbox:python-local"},
        )
        runner._docker = lambda args, *, timeout: subprocess.CompletedProcess(
            args, 0, stdout="|sha256:img", stderr="")
        assert runner.check_design([{"language": "python", "agent": "opencode"}]) == []
        problems = runner.check_design([{"language": "go", "agent": "opencode"}])
        assert problems and "no docker image configured" in problems[0]

    def test_docker_preflight_survives_a_hung_daemon(self, tmp_path):
        runner = _make_runner(
            tmp_path, backend="docker", image_digests={},
            docker_images={"python": "retort-sandbox:python-local"},
        )

        def hung(args, *, timeout):
            raise subprocess.TimeoutExpired(args, timeout)
        runner._docker = hung
        problems = runner.check_design([{"language": "python", "agent": "opencode"}])
        assert len(problems) == 1 and "python" in problems[0]

    def test_prompt_level_is_refused_not_dropped(self, tmp_path):
        runner = _make_runner(tmp_path)
        problems = runner.check_design([
            {"language": "python", "agent": "opencode", "prompt": "bdd"},
        ])
        assert len(problems) == 1
        assert "prompt='bdd'" in problems[0]
        assert "PLAIN prompt" in problems[0]

    def test_tooling_stack_effort_thinking_refused(self, tmp_path):
        runner = _make_runner(tmp_path)
        problems = runner.check_design([
            {"agent": "opencode", "tooling": "graphify"},
            {"agent": "opencode", "stack": "q35-8bit"},
            {"agent": "opencode", "effort": "low"},
            {"agent": "prime", "thinking": "high"},
        ])
        joined = "\n".join(problems)
        assert "tooling='graphify'" in joined
        assert "stack='q35-8bit'" in joined
        assert "effort='low'" in joined
        assert "thinking='high'" in joined
        assert len(problems) == 4

    def test_unknown_agent_refused_and_profile_harness_honoured(self, tmp_path):
        from retort.config.schema import LocalAgentConfig
        runner = _make_runner(tmp_path, local_agents={
            "oc-pinned": LocalAgentConfig(harness="opencode"),
            "hermes-local": LocalAgentConfig(harness="hermes"),
        })
        assert runner.check_design([{"agent": "oc-pinned"}]) == []
        problems = runner.check_design(
            [{"agent": "hermes-local"}, {"agent": "claude-code"}]
        )
        assert len(problems) == 2
        assert any("hermes-local" in p and "'hermes'" in p for p in problems)
        assert any("claude-code" in p for p in problems)

    def test_problems_deduplicated_across_cells(self, tmp_path):
        runner = _make_runner(tmp_path)
        rcs = [{"agent": "opencode", "prompt": "tdd"}] * 12
        assert len(runner.check_design(rcs)) == 1


class TestModelResolution:
    def test_profile_model_fallback(self, tmp_path):
        from retort.config.schema import LocalAgentConfig

        runner = _make_runner(tmp_path, local_agents={
            "oc": LocalAgentConfig(
                harness="opencode", model="openrouter/z-ai/glm-5.3-flash"
            ),
        })
        stack = StackConfig(
            language="python", agent="oc", framework="stdlib",
            extra={"tooling": "none"},  # no model in the design row
        )
        assert runner._model_for(stack) == "openrouter/z-ai/glm-5.3-flash"
        # And the profile-named agent resolves to the opencode harness.
        assert runner._build_agent_command(stack)[0] == "opencode"

    def test_playpen_default_model_fallback(self, tmp_path):
        runner = _make_runner(
            tmp_path, default_model="openrouter/z-ai/glm-5.2"
        )
        stack = StackConfig(
            language="python", agent="opencode", framework="stdlib",
            extra={"tooling": "none"},
        )
        assert runner._model_for(stack) == "openrouter/z-ai/glm-5.2"

    def test_design_row_wins_over_profile_and_default(self, tmp_path):
        from retort.config.schema import LocalAgentConfig

        runner = _make_runner(
            tmp_path,
            default_model="openrouter/z-ai/glm-5.2",
            local_agents={"opencode": LocalAgentConfig(
                harness="opencode", model="openrouter/z-ai/glm-5.3"
            )},
        )
        assert runner._model_for(_stack()) == "openrouter/z-ai/glm-5.3-flash"

    def test_profile_model_options_win(self, tmp_path):
        from retort.config.schema import LocalAgentConfig

        profile_pin = {"provider": {"order": ["parasail"]}}
        runner = _make_runner(
            tmp_path,
            model_options={"provider": {"order": ["z-ai"]}},
            local_agents={"opencode": LocalAgentConfig(
                harness="opencode", model_options=profile_pin
            )},
        )
        env_id = runner.provision(_stack(), _task())
        cfg = json.loads(
            (runner._envs[env_id].workspace / "opencode.json").read_text()
        )
        entry = cfg["provider"]["openrouter"]["models"]["z-ai/glm-5.3-flash"]
        assert entry["options"] == profile_pin


class TestFullScoringPlumbing:
    def test_responses_env_reaches_container(self, tmp_path):
        runner = _make_runner(
            tmp_path,
            score_in_container=True,
            score_metrics=["code_quality", "test_coverage"],
        )
        env_id = runner.provision(_stack(), _task())
        calls = _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        })
        runner.execute(env_id, _stack(), _task())

        submit = next(c for c in calls if c[:2] == ["batch", "submit-job"])
        overrides = json.loads(submit[submit.index("--container-overrides") + 1])
        env = {e["name"]: e["value"] for e in overrides["environment"]}
        assert env["RETORT_RESPONSES"] == "code_quality,test_coverage"

    def test_container_scores_file_noted_in_metadata(self, tmp_path):
        runner = _make_runner(tmp_path, score_in_container=True)
        env_id = runner.provision(_stack(), _task())
        _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META,
            "_agent_stdout.log": _STEP_FINISH,
            "_container_scores.json": json.dumps({"test_coverage": 0.9}),
        })
        art = runner.execute(env_id, _stack(), _task())

        assert art.metadata["sandbox_container_scores"] == \
            "_container_scores.json"


class TestSecondChanceContract:
    def test_workspace_lives_at_work_dir_slash_env_id(self, tmp_path):
        """cli.py's second chance seeds ``runner.work_dir / env_id2`` between
        provision() and execute() (the _seed_repair_workspace call site). That
        works for the sandbox lane ONLY because provision() builds the
        workspace at exactly that path and execute() tars it afterwards —
        this pins the contract so a workspace relocation can't silently turn
        every sandbox second chance into an unseeded fresh attempt."""
        runner = _make_runner(tmp_path)
        env_id = runner.provision(_stack(), _task())
        assert runner._envs[env_id].workspace == runner.work_dir / env_id
        # Seed a repair file the way the second chance does, then prove it
        # ships inside the input tarball execute() uploads.
        (runner.work_dir / env_id / "FEEDBACK.md").write_text("fix R3")
        calls = _wire_success(runner, artifacts={
            "_sandbox_meta.json": _META, "_agent_stdout.log": _STEP_FINISH,
        })
        runner.execute(env_id, _stack(), _task())
        upload = next(c for c in calls if c[:2] == ["s3", "cp"])
        with tarfile.open(upload[2]) as tar:
            assert "FEEDBACK.md" in tar.getnames()


class TestSandboxConfigSchema:
    def test_playpen_sandbox_block_parses(self):
        from retort.config.schema import PlaypenConfig, RunnerType

        cfg = PlaypenConfig(
            runner="sandbox",
            sandbox={
                "s3_bucket": "retort-sandbox-artifacts-x",
                "image_digests": {"python": "sha256:52dd"},
                "score_in_container": True,
            },
        )
        assert cfg.runner == RunnerType.sandbox
        assert cfg.sandbox is not None
        assert cfg.sandbox.job_queue == "retort-sandbox"
        assert cfg.sandbox.vcpu == 2.0 and cfg.sandbox.memory_mb == 8192
        assert cfg.sandbox.image_digests["python"] == "sha256:52dd"

    def test_sandbox_block_optional_for_other_runners(self):
        from retort.config.schema import PlaypenConfig

        cfg = PlaypenConfig(runner="local")
        assert cfg.sandbox is None


class TestPrimeHarnessSandbox:
    def test_prime_agent_command_built_for_container(self, tmp_path):
        from retort.config.schema import LocalAgentConfig

        runner = _make_runner(tmp_path)
        runner.local_agents = {"pa": LocalAgentConfig(harness="prime")}
        stack = _stack(agent="pa")
        stack.extra["model"] = "openrouter/z-ai/glm-5.3-flash"

        cmd = runner._build_agent_command(stack)

        assert cmd[0] == "prime-agent"
        assert cmd[cmd.index("--cwd") + 1] == "/workspace"
        assert cmd[cmd.index("--provider") + 1] == "openrouter"
        assert cmd[cmd.index("--model") + 1] == "z-ai/glm-5.3-flash"
        for flag in ("-nc", "-ns", "-ne", "-np", "--no-session"):
            assert flag in cmd

    def test_prime_provision_writes_no_opencode_config(self, tmp_path):
        from retort.config.schema import LocalAgentConfig

        runner = _make_runner(tmp_path)
        runner.local_agents = {"pa": LocalAgentConfig(harness="prime")}
        env_id = runner.provision(_stack(agent="pa"), _task())

        ws = runner._envs[env_id].workspace
        assert not (ws / "opencode.json").exists()


def test_extract_tar_skips_absolute_symlinks_keeps_files(tmp_path):
    """A workspace venv ships symlinks to absolute container paths; the safe
    filter refuses them. They must be SKIPPED — a SUCCEEDED cell's real files
    must still land instead of the whole extraction crashing (the 0.0s-crash
    mode from exp-mu-primeagent brazil, 2026-09-02)."""
    import tarfile

    from retort.playpen.sandbox_runner import _extract_tar

    src = tmp_path / "src"
    (src / ".venv" / "bin").mkdir(parents=True)
    (src / "app.py").write_text("print('real work')\n")
    (src / ".venv" / "bin" / "python").symlink_to("/usr/local/bin/python")
    tar_path = tmp_path / "out.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(src, arcname=".")

    dest = tmp_path / "dest"
    dest.mkdir()
    _extract_tar(tar_path, dest)

    assert (dest / "app.py").read_text() == "print('real work')\n"
    assert not (dest / ".venv" / "bin" / "python").exists()
