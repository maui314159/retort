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

    def test_scoring_defaults_off(self, tmp_path):
        runner = _make_runner(tmp_path)
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


class TestDesignPreflight:
    """check_design(): refuse every factor level the lane would silently drop."""

    def test_runnable_design_has_no_problems(self, tmp_path):
        runner = _make_runner(tmp_path)
        rcs = [
            {"language": "python", "agent": "opencode", "model": "m",
             "tooling": "none"},
            {"language": "go", "agent": "prime", "model": "m", "prompt": "none"},
        ]
        assert runner.check_design(rcs) == []

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
