"""AWS Batch (Fargate) sandbox runner — one cell, one ephemeral container.

Pre-registered design: docs/future-experiments.md §0c (2026-08-31). API-model
experiments (opencode x OpenRouter) are API-bound, yet the one-experiment-at-a-
time rule serializes them because wall-clock is a first-class response on a
shared machine. Here each cell runs in its own ephemeral Fargate task, so
timing is per-environment and cells can run wide without contending.

Flow per cell:
  provision()  build the task workspace locally (TASK.md, support files,
               stack.json, per-workspace opencode.json) — same seeding as
               LocalRunner, minus host-only steps (venv, graphify)
  execute()    tar -> S3 -> `aws batch submit-job` -> poll -> pull out.tar.gz
               -> unpack -> read _sandbox_meta.json + _agent_stdout.log
  teardown()   remove the local workspace and best-effort delete the S3 prefix

Design invariants (each one is a tuning parameter or a comparability rule):
  * The container image DIGEST and the task's vCPU/memory spec are recorded in
    every run's metadata; arms of one experiment must never mix them.
  * ``duration_seconds`` is the IN-CONTAINER agent time from _sandbox_meta.json
    (measured around the agent invocation by entrypoint.sh) — queue and
    provisioning time are recorded separately in metadata and never folded in.
  * Usage parsing delegates to local_runner's ``_parse_agent_usage`` so both
    lanes share one source of truth for tokens/cost.
  * Secrets reach the container via the job definition's Secrets Manager
    wiring; this runner never sees or logs key material.
  * ``runner_lane`` is stamped into metadata: duration/build_time must never be
    pooled across lanes (different hardware).

Like docker_runner, this shells out to the ``aws`` CLI rather than depending
on boto3 — no new dependency, and tests monkeypatch one seam (``_aws``).
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tarfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from retort.playpen import local_runner as _local
from retort.playpen.runner import (
    RunArtifacts,
    StackConfig,
    TaskSpec,
    stack_metadata,
)

logger = logging.getLogger(__name__)

#: Batch terminal states (DescribeJobs ``status``).
_TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED"})

#: Grace period on top of the agent timeout for queueing + image pull +
#: S3 transfer before execute() gives up on a job (seconds).
_DEFAULT_QUEUE_GRACE_SECONDS = 900

#: Poll interval for DescribeJobs (seconds). Injectable for tests.
_DEFAULT_POLL_SECONDS = 15.0


@dataclass(frozen=True)
class SandboxSpec:
    """Fargate task size for every cell of an experiment.

    A tuning parameter: recorded per run, identical across arms. Fargate
    accepts only certain vCPU/memory combinations (e.g. 2 vCPU with
    4096-16384 MB) — the bootstrap script validates the pairing.
    """

    vcpu: float = 2.0
    memory_mb: int = 8192


@dataclass
class _SandboxEnv:
    env_id: str
    workspace: Path
    stack: StackConfig
    task: TaskSpec


class SandboxRunner:
    """Executes experiment runs in ephemeral AWS Batch Fargate tasks."""

    def __init__(
        self,
        *,
        s3_bucket: str,
        job_queue: str = "retort-sandbox",
        job_definition_prefix: str = "retort-sandbox",
        image_digests: dict[str, str] | None = None,
        spec: SandboxSpec | None = None,
        region: str = "us-east-1",
        work_dir: Path | None = None,
        timeout_minutes: int = 30,
        model_options: dict[str, Any] | None = None,
        queue_grace_seconds: int = _DEFAULT_QUEUE_GRACE_SECONDS,
        poll_seconds: float = _DEFAULT_POLL_SECONDS,
    ) -> None:
        self.s3_bucket = s3_bucket
        self.job_queue = job_queue
        self.job_definition_prefix = job_definition_prefix
        # language -> pinned image digest (sha256:...). Recorded per run; a
        # missing entry is recorded as "unpinned" rather than silently blank so
        # the gap is visible in provenance.
        self.image_digests = image_digests or {}
        self.spec = spec or SandboxSpec()
        self.region = region
        self.work_dir = work_dir or Path.home() / ".retort-sandbox"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_minutes = timeout_minutes
        # opencode per-model options (e.g. the OpenRouter provider pin) —
        # mirrors LocalAgentConfig.model_options for the local lane.
        self.model_options = model_options
        self.queue_grace_seconds = queue_grace_seconds
        self.poll_seconds = poll_seconds
        self._envs: dict[str, _SandboxEnv] = {}
        # Injectable clocks for tests.
        self._now = time.monotonic
        self._sleep = time.sleep

    # ------------------------------------------------------------------ AWS --

    def _aws(self, args: list[str], *, parse_json: bool = True) -> dict[str, Any]:
        """Run one ``aws`` CLI command; the single seam tests monkeypatch.

        Returns the parsed JSON payload ({} when the command prints nothing,
        e.g. ``s3 cp``). Raises RuntimeError with stderr on a nonzero exit.
        """
        cmd = ["aws", "--region", self.region, "--output", "json", *args]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise RuntimeError(
                f"aws {' '.join(args[:2])} failed ({proc.returncode}): "
                f"{proc.stderr.strip()[:2000]}"
            )
        if not parse_json or not proc.stdout.strip():
            return {}
        payload: dict[str, Any] = json.loads(proc.stdout)
        return payload

    # ------------------------------------------------------------ provision --

    def provision(self, stack: StackConfig, task: TaskSpec) -> str:
        """Build the cell's workspace locally; the container gets it as a tar.

        Mirrors LocalRunner's seeding (support files first, then TASK.md and
        stack.json so the loader-extracted prompt wins) minus host-only steps:
        the python venv and the graphify hook belong in-container and are
        deferred to the in-container scoring stage.
        """
        env_id = f"retort-sbx-{uuid.uuid4().hex[:12]}"
        env_dir = self.work_dir / env_id
        env_dir.mkdir(parents=True, exist_ok=True)

        if task.support_dir is not None:
            _local._copy_support_files(task.support_dir, env_dir)

        (env_dir / "TASK.md").write_text(task.prompt)
        (env_dir / "stack.json").write_text(
            json.dumps(stack_metadata(stack, self._model_for(stack)))
        )

        # Many agents expect a git repo; skip if the support tree brought one.
        if not (env_dir / ".git").exists():
            subprocess.run(
                ["git", "init", "-q"], cwd=env_dir, capture_output=True
            )

        self._write_opencode_config(env_dir, stack)

        self._envs[env_id] = _SandboxEnv(
            env_id=env_id, workspace=env_dir, stack=stack, task=task
        )
        logger.info("Provisioned sandbox env %s at %s", env_id, env_dir)
        return env_id

    def _model_for(self, stack: StackConfig) -> str:
        return str(stack.extra.get("model") or "")

    def _write_opencode_config(self, workspace: Path, stack: StackConfig) -> None:
        """Per-workspace opencode.json: model registration + permission grants.

        Same shape LocalRunner writes (see its _write_opencode_config for the
        external_directory rationale), with this runner's ``model_options``
        merged into the model entry — the OpenRouter provider pin that keeps a
        multi-provider model on ONE provider/quantization. entrypoint.sh makes
        it authoritative via OPENCODE_CONFIG.
        """
        model = self._model_for(stack)
        if not model or model == "none":
            return
        prefix = "openrouter/"
        bare = model[len(prefix):] if model.startswith(prefix) else model
        permission: dict[str, object] = {
            t: "allow" for t in _local.LocalRunner._OPENCODE_PERMISSION_TOOLS
        }
        permission["external_directory"] = {"*": "allow"}
        entry: dict[str, object] = (
            {"options": self.model_options} if self.model_options else {}
        )
        config = {
            "$schema": "https://opencode.ai/config.json",
            "permission": permission,
            "provider": {"openrouter": {"models": {bare: entry}}},
        }
        (workspace / "opencode.json").write_text(json.dumps(config))

    # -------------------------------------------------------------- execute --

    def execute(self, env_id: str, stack: StackConfig, task: TaskSpec) -> RunArtifacts:
        info = self._envs.get(env_id)
        if info is None:
            return RunArtifacts(stderr=f"Unknown environment: {env_id}", exit_code=1)

        try:
            agent_cmd = self._build_agent_command(stack)
        except ValueError as exc:
            return RunArtifacts(
                output_dir=info.workspace, stderr=str(exc), exit_code=1
            )

        s3_in = f"s3://{self.s3_bucket}/runs/{env_id}/in.tar.gz"
        s3_out = f"s3://{self.s3_bucket}/runs/{env_id}/out.tar.gz"
        in_tar = self.work_dir / f"{env_id}-in.tar.gz"
        _make_tar(info.workspace, in_tar)

        digest = self.image_digests.get(stack.language, "unpinned")
        submitted = self._now()
        try:
            self._aws(["s3", "cp", str(in_tar), s3_in], parse_json=False)
            job = self._aws([
                "batch", "submit-job",
                "--job-name", env_id,
                "--job-queue", self.job_queue,
                "--job-definition",
                f"{self.job_definition_prefix}-{stack.language}",
                "--container-overrides", json.dumps({
                    "resourceRequirements": [
                        {"type": "VCPU", "value": str(self.spec.vcpu)},
                        {"type": "MEMORY", "value": str(self.spec.memory_mb)},
                    ],
                    "environment": [
                        {"name": "RETORT_S3_IN", "value": s3_in},
                        {"name": "RETORT_S3_OUT", "value": s3_out},
                        {"name": "RETORT_AGENT_CMD",
                         "value": json.dumps(agent_cmd)},
                        {"name": "RETORT_ENV_ID", "value": env_id},
                        {"name": "RETORT_LANGUAGE", "value": stack.language},
                        {"name": "RETORT_MODEL",
                         "value": self._model_for(stack)},
                        {"name": "RETORT_IMAGE_DIGEST", "value": digest},
                        # v1: scoring stays on the host; flipping this on is
                        # gated on the scorer-parity smoke (§0c smoke #4).
                        {"name": "RETORT_SCORE_IN_CONTAINER", "value": "0"},
                    ],
                }),
            ])
        except RuntimeError as exc:
            return RunArtifacts(
                output_dir=info.workspace, stderr=str(exc), exit_code=1
            )
        job_id = str(job.get("jobId", ""))
        if not job_id:
            return RunArtifacts(
                output_dir=info.workspace,
                stderr=f"submit-job returned no jobId: {job!r}",
                exit_code=1,
            )
        logger.info("Submitted %s as Batch job %s", env_id, job_id)

        status, detail = self._poll_job(job_id)
        base_meta = {
            "runner_lane": "sandbox",
            "sandbox_job_id": job_id,
            "sandbox_image_digest": digest,
            "sandbox_vcpu": str(self.spec.vcpu),
            "sandbox_memory_mb": str(self.spec.memory_mb),
            "sandbox_queue_seconds": _queue_seconds(detail),
        }

        if status == "TIMEOUT":
            try:
                self._aws([
                    "batch", "terminate-job", "--job-id", job_id,
                    "--reason", "retort sandbox timeout",
                ], parse_json=False)
            except RuntimeError:
                logger.warning("terminate-job failed for %s", job_id)
            wall = self._now() - submitted
            return RunArtifacts(
                output_dir=info.workspace,
                stderr=f"Sandbox job {job_id} timed out after {wall:.0f}s "
                       "(queue grace + agent timeout)",
                exit_code=124,
                metadata=base_meta,
            )

        # Pull artifacts even on FAILED — entrypoint.sh uploads the out tar on
        # a trap, so a failed agent still leaves a diagnosable workspace.
        out_tar = self.work_dir / f"{env_id}-out.tar.gz"
        try:
            self._aws(["s3", "cp", s3_out, str(out_tar)], parse_json=False)
            _extract_tar(out_tar, info.workspace)
        except (RuntimeError, tarfile.TarError, OSError) as exc:
            reason = str(detail.get("statusReason") or "")
            return RunArtifacts(
                output_dir=info.workspace,
                stderr=(
                    f"Batch job {job_id} {status}"
                    f"{' (' + reason + ')' if reason else ''}; "
                    f"artifacts unavailable: {exc}"
                ),
                exit_code=1,
                metadata=base_meta,
            )

        meta_file = info.workspace / "_sandbox_meta.json"
        if not meta_file.exists():
            return RunArtifacts(
                output_dir=info.workspace,
                stderr=f"Batch job {job_id} {status} but _sandbox_meta.json "
                       "missing from artifacts — entrypoint did not complete",
                exit_code=1,
                metadata=base_meta,
            )
        sandbox_meta = json.loads(meta_file.read_text())
        agent_exit = int(sandbox_meta.get("agent_exit", 1))
        # THE duration: measured in-container around the agent invocation.
        # Never wall time here — queue/pull/transfer would pollute a first-
        # class response.
        agent_seconds = float(sandbox_meta.get("agent_seconds", 0.0))

        stdout_text = _read_text(info.workspace / "_agent_stdout.log")
        stderr_text = _read_text(info.workspace / "_agent_stderr.log")
        token_count, usage_meta = _local._parse_agent_usage(
            "opencode", stdout_text, info.workspace, self._model_for(stack)
        )

        return RunArtifacts(
            output_dir=info.workspace,
            stdout=stdout_text,
            stderr=stderr_text,
            exit_code=agent_exit,
            duration_seconds=agent_seconds,
            token_count=token_count,
            metadata={**usage_meta, **base_meta},
        )

    def _build_agent_command(self, stack: StackConfig) -> list[str]:
        """The headless agent command entrypoint.sh runs inside the container.

        v1 supports the opencode harness only (the shakedown lane). The
        command mirrors LocalRunner's opencode branch; --dir is the container
        workspace, fixed by entrypoint.sh.
        """
        if stack.agent not in ("opencode", "oc"):
            raise ValueError(
                f"SandboxRunner v1 supports only the opencode harness; "
                f"got agent {stack.agent!r}"
            )
        model = self._model_for(stack)
        cmd = [
            "opencode", "run", "--pure", "--print-logs", "--format", "json",
            "--dir", "/workspace",
        ]
        if model and model != "none":
            cmd.extend(["--model", model])
        cmd.append(_local._build_agent_prompt(stack))
        return cmd

    def _poll_job(self, job_id: str) -> tuple[str, dict[str, Any]]:
        """Poll DescribeJobs until terminal or deadline.

        Returns (status, job-detail). status is SUCCEEDED / FAILED / TIMEOUT;
        the deadline is the agent timeout plus a queue-and-transfer grace so a
        slow queue is not misread as a slow agent.
        """
        deadline = self._now() + self.timeout_minutes * 60 + self.queue_grace_seconds
        detail: dict[str, Any] = {}
        while self._now() < deadline:
            resp = self._aws(["batch", "describe-jobs", "--jobs", job_id])
            jobs = resp.get("jobs") or []
            detail = jobs[0] if jobs else {}
            status = str(detail.get("status", ""))
            if status in _TERMINAL_STATES:
                return status, detail
            self._sleep(self.poll_seconds)
        return "TIMEOUT", detail

    # ------------------------------------------------------------- teardown --

    def teardown(self, env_id: str) -> None:
        info = self._envs.pop(env_id, None)
        if info is not None and info.workspace.exists():
            shutil.rmtree(info.workspace, ignore_errors=True)
        for suffix in ("-in.tar.gz", "-out.tar.gz"):
            (self.work_dir / f"{env_id}{suffix}").unlink(missing_ok=True)
        try:
            self._aws([
                "s3", "rm", f"s3://{self.s3_bucket}/runs/{env_id}",
                "--recursive",
            ], parse_json=False)
        except RuntimeError:
            logger.warning("S3 cleanup failed for %s (left in place)", env_id)

    def cleanup_all(self) -> None:
        for env_id in list(self._envs):
            self.teardown(env_id)


# ------------------------------------------------------------------- tars --


def _make_tar(src_dir: Path, out_path: Path) -> None:
    """Tar a workspace directory (contents at the archive root)."""
    with tarfile.open(out_path, "w:gz") as tar:
        for child in sorted(src_dir.iterdir()):
            tar.add(child, arcname=child.name)


def _extract_tar(tar_path: Path, dest_dir: Path) -> None:
    """Unpack an artifacts tar into the workspace (overwriting seeds)."""
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(dest_dir, filter="data")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def _queue_seconds(job_detail: dict[str, Any]) -> str:
    """Queue latency from Batch's own timestamps (ms), '' when unknown."""
    created = job_detail.get("createdAt")
    started = job_detail.get("startedAt")
    if isinstance(created, int) and isinstance(started, int) and started >= created:
        return f"{(started - created) / 1000.0:.1f}"
    return ""
