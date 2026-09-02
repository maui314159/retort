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

from retort.config.schema import LocalAgentConfig
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

#: Margin added to playpen.timeout_minutes for the Batch attempt timeout —
#: covers image pull + S3 transfer + scoring so Batch's kill never races the
#: entrypoint's own agent timeout/stall watchdog (which should fire first and
#: preserve artifacts; a Batch kill loses the out tarball).
_TIMEOUT_MARGIN_SECONDS = 600

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
        stall_minutes: int = 0,
        local_agents: dict[str, LocalAgentConfig] | None = None,
        default_model: str | None = None,
        model_options: dict[str, Any] | None = None,
        score_in_container: bool = False,
        score_metrics: list[str] | None = None,
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
        # Stall guard, same semantics as the local lane: kill the agent after
        # this many minutes with no new stdout bytes AND no workspace writes
        # (0 = disabled). Enforced by entrypoint.sh's watchdog; without it a
        # hung agent silently burns the whole Batch wall — observed 6 times in
        # one evening on long z-ai streams (2026-08-31).
        self.stall_minutes = stall_minutes
        # Agent profiles + default model: the SAME fallback chain as
        # LocalRunner._model_for (design row -> profile.model -> playpen
        # default), so a workspace that relies on `playpen.model` behaves
        # identically in both lanes.
        self.local_agents = local_agents or {}
        self.default_model = default_model
        # opencode per-model options (e.g. the OpenRouter provider pin) —
        # profile model_options win (per-agent), this is the runner-wide
        # fallback, mirroring the local lane.
        self.model_options = model_options
        # Metric names for full in-container scoring (RETORT_RESPONSES);
        # None/empty means the container runs no full scorer suite.
        self.score_metrics = score_metrics or []
        # v1 mechanical gate (pytest+coverage, python only) inside the
        # container. NOT full scorer parity — code_quality/maintainability/
        # idiomatic still need the host scorer suite; this gate only proves
        # the tests run where the build ran. Off until §0c smoke #4 passes.
        self.score_in_container = score_in_container
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

        if self._resolve_harness(stack) == "opencode":
            self._write_opencode_config(env_dir, stack)

        self._envs[env_id] = _SandboxEnv(
            env_id=env_id, workspace=env_dir, stack=stack, task=task
        )
        logger.info("Provisioned sandbox env %s at %s", env_id, env_dir)
        return env_id

    def _resolve_harness(self, stack: StackConfig) -> str:
        """Profile harness wins, else the agent name is the harness —
        LocalRunner._resolve_harness's precedence, minus model inference
        (sandbox stacks always name their agent)."""
        profile = self.local_agents.get(stack.agent)
        if profile is not None:
            return profile.harness
        return stack.agent

    def _model_for(self, stack: StackConfig) -> str:
        """Design-row model, then profile default, then playpen default —
        the same chain as LocalRunner._model_for."""
        profile = self.local_agents.get(stack.agent)
        profile_model = profile.model if profile is not None else None
        return str(
            stack.extra.get("model") or profile_model or self.default_model or ""
        )

    def _model_options_for(self, stack: StackConfig) -> dict[str, Any] | None:
        """Per-agent profile model_options win; runner-wide options fall back."""
        profile = self.local_agents.get(stack.agent)
        if profile is not None and profile.model_options:
            return profile.model_options
        return self.model_options

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
        options = self._model_options_for(stack)
        entry: dict[str, object] = {"options": options} if options else {}
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
                # The Batch attempt timeout derives from THIS experiment's
                # playpen.timeout_minutes (+ setup/transfer margin), never the
                # job definition's baked-in default — a job-def timeout is one
                # value for every experiment, i.e. a tuning parameter that
                # silently stops matching the config that claims to govern it.
                "--timeout", json.dumps({
                    "attemptDurationSeconds":
                        self.timeout_minutes * 60 + _TIMEOUT_MARGIN_SECONDS,
                }),
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
                        {"name": "RETORT_SCORE_IN_CONTAINER",
                         "value": "1" if self.score_in_container else "0"},
                        {"name": "RETORT_STALL_SECONDS",
                         "value": str(self.stall_minutes * 60)},
                        {"name": "RETORT_RESPONSES",
                         "value": ",".join(self.score_metrics)},
                        {"name": "RETORT_AGENT_TIMEOUT_SECONDS",
                         "value": str(self.timeout_minutes * 60)},
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

        # v1 in-container mechanical gate results, if the entrypoint ran it.
        score_meta = {
            f"sandbox_{k}": str(sandbox_meta[k])
            for k in ("tests_passed", "tests_total", "coverage_pct")
            if k in sandbox_meta
        }
        base_meta.update(score_meta)
        if (info.workspace / "_container_scores.json").exists():
            base_meta["sandbox_container_scores"] = "_container_scores.json"

        stdout_text = _read_text(info.workspace / "_agent_stdout.log")
        stderr_text = _read_text(info.workspace / "_agent_stderr.log")
        token_count, usage_meta = _local._parse_agent_usage(
            self._resolve_harness(stack), stdout_text, info.workspace,
            self._model_for(stack),
        )

        # Watchdog kills surface exactly like the local progress guard: exit
        # 124 + kill_reason metadata, so `retort diagnose` and the crash
        # accounting treat both lanes identically.
        kill_reason = str(sandbox_meta.get("kill_reason") or "")
        if kill_reason in ("stall", "timeout"):
            base_meta["kill_reason"] = kill_reason
            if kill_reason == "stall":
                msg = (
                    f"Killed after {agent_seconds:.0f}s — stalled "
                    f"(no progress for {self.stall_minutes}m, unproductive loop)"
                )
            else:
                msg = f"Timeout after {agent_seconds:.0f}s (in-container wall)"
            return RunArtifacts(
                output_dir=info.workspace,
                stdout=stdout_text,
                stderr=(stderr_text[-5000:] + "\n" + msg) if stderr_text else msg,
                exit_code=124,
                duration_seconds=agent_seconds,
                token_count=token_count,
                metadata={**usage_meta, **base_meta},
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
        harness = self._resolve_harness(stack)
        model = self._model_for(stack)
        if harness in ("opencode", "oc"):
            cmd = [
                "opencode", "run", "--pure", "--print-logs", "--format", "json",
                "--dir", "/workspace",
            ]
            if model and model != "none":
                cmd.extend(["--model", model])
            cmd.append(_local._build_agent_prompt(stack))
            return cmd
        if harness == "prime":
            # Mirrors LocalRunner's prime branch; auth via OPENROUTER_API_KEY,
            # which the job definition injects from Secrets Manager — no
            # auth-file seeding needed (see entrypoint.sh).
            cmd = [
                "prime-agent", "-p", "--mode", "json", "--offline",
                "-nc", "-ns", "-ne", "-np", "--no-session",
                "--cwd", "/workspace",
            ]
            if model and model != "none":
                prefix = "openrouter/"
                if model.startswith(prefix):
                    cmd.extend(["--provider", "openrouter",
                                "--model", model[len(prefix):]])
                else:
                    cmd.extend(["--model", model])
            cmd.extend(["--", _local._build_agent_prompt(stack)])
            return cmd
        raise ValueError(
            f"SandboxRunner supports the opencode and prime harnesses; "
            f"agent {stack.agent!r} resolves to {harness!r}"
        )

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
    """Unpack an artifacts tar into the workspace (overwriting seeds).

    Members the safe filter refuses are SKIPPED, not fatal. An agent that
    builds a `.venv` in its workspace ships symlinks to absolute container
    paths (`.venv/bin/python -> /usr/local/bin/python`); `filter="data"`
    rejects those, and before this guard the whole extraction — and therefore
    a SUCCEEDED cell with real, scored work — was recorded as a 0.0s crash
    (first hit: exp-mu-primeagent brazil, 2026-09-02). The skipped links are
    provisioning artifacts, not deliverables: in-container scoring already
    ran, and host-side rescoring rebuilds a venv anyway (ensure_python_env).
    """
    skipped = 0
    with tarfile.open(tar_path, "r:gz") as tar:
        for member in tar:
            try:
                tar.extract(member, dest_dir, filter="data")
            except tarfile.FilterError:
                skipped += 1
    if skipped:
        logger.warning(
            "artifact extraction skipped %d unsafe member(s) (absolute-path "
            "symlinks etc.) from %s", skipped, tar_path.name,
        )


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
