"""Full in-container scoring: retort's REAL scorer suite over /workspace.

The image installs retort itself (wheel, --no-deps + the scoring path's pure
dependencies — see Dockerfile.python), so this runs the exact ScoreCollector /
ScorerRegistry code the host runs, not a reimplementation. Metrics come from
RETORT_RESPONSES (comma-separated), i.e. the experiment's `responses:` list.

Output: /workspace/_container_scores.json  {metric: value|null}.
The host pipeline still computes its own scores.json today; the container
file exists for (a) the §0c scorer-parity check and (b) cross-lane
build_time comparability, where only the in-container number is honest.
Promoting _container_scores.json to the authoritative scores is a host-side
pipeline decision deliberately NOT made here.
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

    from retort.playpen.runner import RunArtifacts, StackConfig
    from retort.scoring.collector import ScoreCollector

    ws = Path("/workspace")
    stack = StackConfig(
        language=os.environ.get("RETORT_LANGUAGE", "python"),
        agent="opencode",
        framework="unknown",
    )
    artifacts = RunArtifacts(
        output_dir=ws,
        stdout=_read(ws / "_agent_stdout.log"),
        stderr=_read(ws / "_agent_stderr.log"),
        exit_code=0,
    )
    collector = ScoreCollector(metrics=metrics)
    vector = collector.collect(artifacts, stack)
    scores = {s.metric_name: s.value for s in vector.scores}
    (ws / "_container_scores.json").write_text(json.dumps(scores, indent=2))
    print(f"score_full: wrote _container_scores.json {scores}")
    return 0


def _read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


if __name__ == "__main__":
    sys.exit(main())
