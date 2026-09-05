"""agent_log: bounded, gzip-aware transcript readers + prime compaction.

Every reader must give the same answer on ``_agent_stdout.log`` and on its
archived ``.gz`` form, and none may need the whole file in memory.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import pytest

from retort.playpen import agent_log
from retort.playpen.local_runner import _parse_prime_usage, agent_consulted


def _event(kind: str, **message) -> str:
    return json.dumps({"type": kind, "message": message}) + "\n"


def _assistant_usage(n: int) -> dict:
    return {
        "input": 100 * n, "output": 10 * n, "cacheRead": 5, "cacheWrite": 0,
        "totalTokens": 110 * n + 5,
        "cost": {"input": 0.001 * n, "output": 0.0005 * n, "total": 0.0015 * n},
    }


def _prime_stream() -> str:
    """Two assistant turns in prime's --mode json shape: the accumulating
    message_update snapshots (bulk), then a message_end carrying usage, plus
    tool events and a non-JSON line, as a real transcript has."""
    out = []
    for turn in (1, 2):
        out.append(json.dumps({"type": "turn_start"}) + "\n")
        out.append(_event("message_start", role="assistant", content=[]))
        for k in range(40):  # snapshots grow as the message streams
            out.append(_event(
                "message_update", role="assistant",
                content=[{"type": "text", "text": "x" * (50 * k)}],
                usage=_assistant_usage(turn), stopReason="", model="m",
            ))
        out.append(_event(
            "message_end", role="assistant", model="m", provider="openrouter",
            responseId=f"gen-{turn}", stopReason="toolUse",
            content=[{"type": "toolCall", "name": "write",
                      "arguments": {"path": "GRAPH_REPORT.md"}}],
            usage=_assistant_usage(turn),
        ))
        for kind, extra in (("tool_execution_start", {"toolName": "write"}),
                            ("tool_execution_update", {"chunk": "…"}),
                            ("tool_execution_end", {"isError": False})):
            out.append(json.dumps({"type": kind, **extra}) + "\n")
        out.append(_event("message_end", role="toolResult",
                          content=[{"type": "text", "text": "ok"}]))
        out.append(json.dumps({"type": "turn_end"}) + "\n")
    out.append("prime-agent: plain stderr-ish line that is not JSON\n")
    return "".join(out)


@pytest.fixture
def plain_log(tmp_path: Path) -> Path:
    p = tmp_path / "_agent_stdout.log"
    p.write_text(_prime_stream())
    return p


@pytest.fixture
def gz_log(tmp_path: Path) -> Path:
    p = tmp_path / "_agent_stdout.log.gz"
    with gzip.open(p, "wb") as fh:
        fh.write(_prime_stream().encode())
    return p


class TestFind:
    def test_prefers_plain_then_gz(self, tmp_path: Path):
        assert agent_log.find_agent_log(tmp_path) is None
        gz = tmp_path / "_agent_stdout.log.gz"
        gz.write_bytes(gzip.compress(b"{}\n"))
        assert agent_log.find_agent_log(tmp_path) == gz
        plain = tmp_path / "_agent_stdout.log"
        plain.write_text("{}\n")
        assert agent_log.find_agent_log(tmp_path) == plain


class TestReaders:
    def test_tail_bounded_same_across_forms(self, plain_log: Path, gz_log: Path):
        full = _prime_stream()
        for log in (plain_log, gz_log):
            tail = agent_log.read_tail(log, max_bytes=500)
            assert len(tail.encode()) <= 500
            assert full.endswith(tail)
        assert agent_log.read_tail(plain_log, 500) == agent_log.read_tail(gz_log, 500)

    def test_tail_of_gz_larger_than_window_streams(self, tmp_path: Path):
        # 3 MB of lines through a 100 KB window: the rolling buffer must end on
        # the true tail, not on some earlier chunk boundary.
        body = "".join(f"line {i:07d}\n" for i in range(250_000))
        gz = tmp_path / "big.log.gz"
        with gzip.open(gz, "wb") as fh:
            fh.write(body.encode())
        tail = agent_log.read_tail(gz, max_bytes=100_000)
        assert body.endswith(tail)
        assert tail.endswith("line 0249999\n")

    def test_search_and_contains_any_both_forms(self, plain_log: Path, gz_log: Path):
        pat = re.compile(r"plain stderr-ish line[^\n]{0,40}")
        for log in (plain_log, gz_log):
            m = agent_log.search(log, pat)
            assert m is not None and m.group(0).startswith("plain stderr-ish")
            assert agent_log.contains_any(log, "graph_report.md") is True
            assert agent_log.contains_any(log, "beads", "clj-kondo") is False
            assert agent_log.contains_any(log) is False

    def test_read_text_missing_file_is_empty(self, tmp_path: Path):
        assert agent_log.read_text(tmp_path / "nope.log") == ""
        assert agent_log.read_tail(tmp_path / "nope.log") == ""


class TestCompactPrimeLog:
    def test_drops_only_message_update_and_preserves_usage(self, plain_log: Path):
        before_parse = _parse_prime_usage(plain_log.read_text())
        before, after = agent_log.compact_prime_log(plain_log)
        assert before > after

        text = plain_log.read_text()
        types = [json.loads(ln)["type"]
                 for ln in text.splitlines() if ln.startswith("{")]
        assert "message_update" not in types
        # Everything else survives verbatim, in order — including the tool
        # events (the zero-write evidence) and the non-JSON line.
        assert types.count("message_end") == 4
        assert types.count("tool_execution_update") == 2
        assert types.count("turn_end") == 2
        assert text.endswith("plain stderr-ish line that is not JSON\n")
        # The usage parser sees the SAME totals: tokens, cost, turns, gen ids.
        assert _parse_prime_usage(text) == before_parse
        tokens, meta = _parse_prime_usage(text)
        assert tokens == (115) + (225)
        assert meta["turns"] == "2"
        assert meta["openrouter_generation_ids"] == "gen-1,gen-2"

    def test_idempotent_and_noop_without_updates(self, plain_log: Path):
        agent_log.compact_prime_log(plain_log)
        size = plain_log.stat().st_size
        b, a = agent_log.compact_prime_log(plain_log)
        assert (b, a) == (size, size)
        assert plain_log.stat().st_size == size
        assert not list(plain_log.parent.glob("*.tmp"))

    def test_gz_in_gz_out(self, gz_log: Path):
        before, after = agent_log.compact_prime_log(gz_log)
        assert before > after
        with gzip.open(gz_log, "rb") as fh:  # still gzip
            text = fh.read().decode()
        assert '"message_update"' not in text
        assert text.count('"message_end"') == 4

    def test_missing_file_is_a_noop(self, tmp_path: Path):
        assert agent_log.compact_prime_log(tmp_path / "absent.log") == (0, 0)

    def test_substring_hint_does_not_drop_other_events(self, tmp_path: Path):
        # An event that merely MENTIONS message_update (e.g. a tool result
        # echoing a log) is not a message_update event.
        p = tmp_path / "_agent_stdout.log"
        keep = json.dumps({"type": "tool_execution_end",
                           "result": 'saw "message_update" in the log'}) + "\n"
        p.write_text(keep + _event("message_update", role="assistant"))
        agent_log.compact_prime_log(p)
        assert p.read_text() == keep


class TestAgentConsultedGzAware:
    def test_agent_consulted_reads_gz_archive(self, tmp_path: Path):
        # A fresh clone of the data branch holds only the .gz form; the
        # consultation detector must not mistake that for "no transcript".
        gz = tmp_path / "_agent_stdout.log.gz"
        with gzip.open(gz, "wb") as fh:
            fh.write(b'{"type":"tool","input":{"command":"graphify query x"}}\n')
        assert agent_consulted(tmp_path, "graphify query") is True
        assert agent_consulted(tmp_path, "beads") is False
        assert agent_consulted(tmp_path / "empty", "graphify") is None
