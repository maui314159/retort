"""Full in-container scoring: retort's REAL scorer suite over /workspace.

The image installs retort itself (wheel, --no-deps + the scoring path's pure
dependencies — see Dockerfile.python), so this runs the exact ScoreCollector /
ScorerRegistry code the host runs, not a reimplementation. Metrics come from
RETORT_RESPONSES (comma-separated), i.e. the experiment's `responses:` list.

Output: /workspace/_container_scores.json  {metric: value|null}.
Since Phase 2 this file IS scores.json for container lanes (cli._collect_scores
adopts it for a succeeded cell and the host never rescores). The artifacts
handed to the scorers therefore mirror what the host collector would have
seen: RETORT_AGENT_EXIT / RETORT_AGENT_SECONDS / RETORT_KILL_REASON from the
entrypoint, the parsed token count, and the same bounded transcript tails.
"""

import json
import os
import sys
from pathlib import Path


def main() -> int:
    metrics = [m for m in os.environ.get("RETORT_RESPONSES", "").split(",") if m]
    if not metrics:
        print("score_full: RETORT_RESPONSES empty — nothing to score")
        return 0

    from retort.playpen import agent_log, local_runner
    from retort.playpen.runner import RunArtifacts, StackConfig
    from retort.scoring.collector import ScoreCollector

    ws = Path("/workspace")
    cmd = json.loads(os.environ.get("RETORT_AGENT_CMD", "[]"))
    harness = "prime" if cmd and "prime" in os.path.basename(cmd[0]) else "opencode"
    stack = StackConfig(
        language=os.environ.get("RETORT_LANGUAGE", "python"),
        agent=harness,
        framework="unknown",
    )
    # Build the artifacts EXACTLY as SandboxRunner._collect does on the host,
    # because these scores are authoritative for container lanes: the agent's
    # real exit code (a watchdog kill is 124 — the runtime/quality scorers
    # return "not applicable" for a cell that did not succeed, as they would
    # locally), its in-container seconds, the parsed token count (so
    # token_efficiency never falls back to transcript length), and the same
    # bounded stdout/stderr tails LocalRunner carries.
    stdout_text = agent_log.read_text(ws / "_agent_stdout.log")
    stderr_text = _read(ws / "_agent_stderr.log")
    token_count, _usage = local_runner._parse_agent_usage(
        harness, stdout_text, ws, os.environ.get("RETORT_MODEL", ""),
    )
    exit_code = _int_env("RETORT_AGENT_EXIT", 0)
    if os.environ.get("RETORT_KILL_REASON", "").strip():
        exit_code = 124
    artifacts = RunArtifacts(
        output_dir=ws,
        stdout=stdout_text[-10000:],
        stderr=stderr_text[-5000:],
        exit_code=exit_code,
        duration_seconds=_float_env("RETORT_AGENT_SECONDS", 0.0),
        token_count=token_count,
    )
    collector = ScoreCollector(metrics=metrics)
    vector = collector.collect(artifacts, stack)
    # EVERY requested metric appears as a key. `null` means the scorer ran and
    # said "not applicable" (ScoreCollector omits those — e.g. runtime with no
    # probe); an ABSENT key means the scorer never ran. The host treats the
    # file as authoritative for container lanes and needs that distinction to
    # tell a NULL data point from a harness gap.
    scored = {s.metric_name: s.value for s in vector.scores}
    scores = {m: scored.get(m) for m in metrics}
    (ws / "_container_scores.json").write_text(json.dumps(scores, indent=2))
    print(f"score_full: wrote _container_scores.json {scores}")
    return 0


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


if __name__ == "__main__":
    sys.exit(main())
