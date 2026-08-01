"""Provenance must record the stack that RAN, not every stack installed.

Until 2026-08-11 `capture()` recorded the local Hermes/oMLX stack
unconditionally, so every cloud experiment carried a sampling dict —
`temperature 0.7, top_p 0.95, top_k 40` — read off this machine's local serving
stack and never applied to the hosted model that actually ran. 12 of 30 archived
manifests are affected.

That is not cosmetic. This module exists because unrecorded sampling silently
halved the local numbers before exp-27, and the repo's rule is that provenance
reports the EFFECTIVE value. A manifest stating the wrong sampling confidently is
worse than one stating none.
"""
from __future__ import annotations

from pathlib import Path

from retort.reporting import provenance as pv


class _Agent:
    def __init__(self, harness, model):
        self.harness, self.model = harness, model


class _Playpen:
    runner = "local"
    replicates = 3
    timeout_minutes = 150
    stall_minutes = 30
    max_turns = 200
    no_write_abort_after = None
    stack_presets = None

    def __init__(self, agents):
        self.local_agents = agents


def _capture(agents_cfg, agents):
    return pv.capture(repo=Path("."), config_dir=Path("."),
                      playpen_config=_Playpen(agents_cfg), agents=agents)


def test_cloud_run_records_no_local_serving_stack():
    """The regression: a Codex run must not claim oMLX sampling."""
    m = _capture({"codex": _Agent("codex", "gpt-5.6-luna")}, ["codex"])

    assert "omlx" not in m["serving"]
    assert "hermes" not in m["agent_config"]
    assert m["agents"] == {"codex": "codex"}


def test_cloud_run_says_sampling_is_provider_side():
    """Unknown must read as unknown, not as a value we happened to find."""
    m = _capture({"codex": _Agent("codex", "gpt-5.6-luna")}, ["codex"])
    codex = m["agent_config"].get("codex")
    if codex is not None:                      # only when the CLI is installed
        assert "provider-side" in codex["sampling"]


def test_local_run_still_records_hermes_and_omlx():
    m = _capture({"qwen-local": _Agent("hermes", "moe")}, ["qwen-local"])

    assert "omlx" in m["serving"]
    assert "hermes" in m["agent_config"]


def test_mixed_design_records_both_stacks():
    m = _capture({"qwen-local": _Agent("hermes", "moe"),
                  "codex": _Agent("codex", "gpt-5.6-luna")},
                 ["qwen-local", "codex"])

    assert "hermes" in m["agent_config"]
    assert "omlx" in m["serving"]
    assert "codex" in m["agent_config"]


def test_summary_omits_the_stack_that_did_not_run():
    m = _capture({"codex": _Agent("codex", "gpt-5.6-luna")}, ["codex"])
    text = "\n".join(pv.summarize(m))

    assert "oMLX" not in text
    assert "hermes" not in text
    assert "codex" in text


def test_unknown_agents_falls_back_to_recording_everything():
    """Callers that cannot say which agents run must not lose information."""
    m = _capture({"qwen-local": _Agent("hermes", "moe")}, None)
    assert "hermes" in m["agent_config"]



def _write_hermes_config(home: Path, body: str) -> None:
    (home / ".hermes").mkdir(parents=True, exist_ok=True)
    (home / ".hermes" / "config.yaml").write_text(body)


def test_hermes_config_accepts_mapping_model(tmp_path, monkeypatch):
    """A mapping-valued `model:` must not abort capture.

    Hermes' `model:` was a plain string, then became a mapping
    ({default, provider, base_url}). The code used it directly as a dict key,
    raising "unhashable type: 'dict'" — which aborted the ENTIRE manifest, so
    provenance silently stopped being written for every run on a machine with
    the newer schema.
    """
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    _write_hermes_config(
        tmp_path,
        "model:\n"
        "  default: anthropic/claude-opus-4.6\n"
        "  provider: auto\n"
        "  base_url: https://openrouter.ai/api/v1\n"
        "max_turns: 40\n",
    )

    cfg = pv._hermes_config()

    assert cfg is not None
    # The id is normalised out of the mapping, not left as a dict.
    assert cfg["model"] == "anthropic/claude-opus-4.6"
    assert cfg["max_turns"] == 40


def test_hermes_config_string_model_still_reports_per_model_context(tmp_path, monkeypatch):
    """The legacy string form keeps resolving the per-model context_length.

    The per-model value is the one Hermes actually honours; a top-level
    context_length can disagree, and provenance must report the effective one.
    """
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    _write_hermes_config(
        tmp_path,
        "model: mlx-community/some-model\n"
        "context_length: 262144\n"
        "providers:\n"
        "  mlxlocal:\n"
        "    models:\n"
        "      mlx-community/some-model:\n"
        "        context_length: 131072\n",
    )

    cfg = pv._hermes_config()

    assert cfg is not None
    assert cfg["context_length"] == 131072          # effective
    assert cfg["context_length_top_level"] == 262144  # what the file claims
    assert cfg["context_length_unset_per_model"] is False


def test_hermes_config_missing_per_model_context_is_flagged(tmp_path, monkeypatch):
    """An unset per-model context is flagged, not silently reported as the top-level."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    _write_hermes_config(
        tmp_path,
        "model:\n  default: mlx-community/some-model\ncontext_length: 262144\n",
    )

    cfg = pv._hermes_config()

    assert cfg is not None
    assert cfg["context_length"] is None
    assert cfg["context_length_unset_per_model"] is True


def test_hermes_config_absent_returns_none(tmp_path, monkeypatch):
    """No Hermes install is not an error — capture must still produce a manifest."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    assert pv._hermes_config() is None
