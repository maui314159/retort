# Claude Sonnet (via OpenRouter / `openai-completions`) aborts after the first tool call — `"Request was aborted"`, 0 tokens, not retried

## Summary

When driving `anthropic/claude-sonnet-4.6` through the OpenRouter `openai-completions`
provider in headless mode (`omp -p`), the agent **aborts the follow-up request
immediately after the first tool call** (e.g. a `read` of `TASK.md`). The
second assistant turn is born with `stopReason: "aborted"`,
`errorMessage: "Request was aborted"`, and **0 usage tokens** — the HTTP request
never goes out — and because `fetchWithRetry` treats aborts as intentional, it
is **not retried**, so the whole session ends after one turn with no work done.

The same prompt/tools on `anthropic/claude-opus-4.8` through the **identical**
provider, account, and minute runs **25+ turns** with no abort. So it is specific
to the Sonnet path through this adapter, not the account, routing, auth, or model
capability.

It's intermittent in the large: in a real batch (multi-file MCP-server task,
3 reps × 3 languages) **4–7 of 9 cells aborted on turn 2** while the rest ran the
full task and passed — but a tight repro reproduces it **4/4**.

## Environment

- **Platform:** macOS (arm64)
- **omp version:** 15.12.3 (`omp-darwin-arm64`, Homebrew `can1357/tap`)
- **Bun version:** 1.3.13
- **Provider:** OpenRouter — a `models.yml` provider with `api: openai-completions`,
  `baseUrl: https://openrouter.ai/api/v1`, `auth: apiKey` from `OPENROUTER_API_KEY`
- **Area:** Tool execution / provider stream
- **Model:** `anthropic/claude-sonnet-4.6` (invoked as `openrouter/anthropic/claude-sonnet-4.6`);
  `upstreamProvider: "Anthropic"` per the transcript

## Reproduction

```bash
mkdir /tmp/repro && cd /tmp/repro
# A task that makes the agent READ a file (the trigger is the tool-result → next request).
cat > TASK.md <<'EOF'
Implement a small Python project in this directory: a module `calc.py` with an
add(a, b) function, and a pytest test in test_calc.py. Make sure tests pass.
EOF

export OPENROUTER_API_KEY=sk-or-...    # OpenRouter key; models.yml openrouter provider as above

omp -p --no-session --mode json --model openrouter/anthropic/claude-sonnet-4.6 \
  "You are working in python. Read TASK.md in the current directory and implement \
everything it asks for. Write all code files to the current directory. Make sure \
the code builds and tests pass."
```

**Actual:** turn 1 is a `read` tool call; turn 2 aborts (see transcript); no files written.
**Expected:** the agent continues iterating after the tool result, like every other model.

Swap the model to `openrouter/anthropic/claude-opus-4.8` with **no other change** →
it iterates normally (25+ turns, writes files).

A plain task that does **not** read a file (e.g. "create hello.py containing
`print('hi')`") completes fine on Sonnet — the abort is tied to the request that
**follows a tool result**.

## Observed transcript (`--mode json`)

Turn 1 — correct:

```json
{"type":"agent_end","messages":[
  {"role":"assistant","content":[
    {"type":"thinking","thinking":"Let me start by reading the TASK.md file to understand what needs to be implemented."},
    {"type":"toolCall","name":"read","arguments":{"path":"TASK.md"}}],
   "stopReason":"toolUse", "usage":{"cacheWrite":38192,"cost":{"total":0.143}}}]}
```

Turn 2 — aborted before any request is sent:

```json
{"type":"message_start","message":{
  "role":"assistant","content":[],
  "api":"openai-completions","provider":"openrouter","model":"anthropic/claude-sonnet-4.6",
  "usage":{"input":0,"output":0,"totalTokens":0,"cost":{"total":0}},
  "stopReason":"aborted","errorMessage":"Request was aborted"}}
```

(`turn_end`/`agent_end` carry the same `stopReason:"aborted"`, `errorMessage:"Request was aborted"`, 0 tokens.)

## Source-level trace (15.12.3)

- The message is the **generic abort sentinel**: `packages/utils/src/fetch-retry.ts`
  throws `new Error("Request was aborted")` at the top of the retry loop when
  `signal?.aborted` is already true — i.e. **the request's `AbortSignal` was
  aborted before the fetch started** (consistent with the 0 tokens / no HTTP).
- `fetchWithRetry` **does not retry** an aborted signal (aborts are treated as
  intentional), so the single internal abort terminates the session.
- This is an **internal turn abort with no explicit reason** — matching the case
  `session/messages.ts` / `task/executor.ts` describe ("abort originated inside
  the turn … no caller signal and no runtime-limit timer"), which is why it falls
  back to the generic `errorMessage` rather than a specific reason.

### Ruled out (by reading `packages/agent/src/agent-loop.ts`)

- **Harmony-leak mitigation** — `isHarmonyLeakMitigationTarget(config.model)` gates
  `harmonyAbortController`; it targets GPT-5/gpt-oss, not Anthropic. Disabled here.
- **Repetition abort** (`repetitionAbortController`) and **owned-tools
  `<tool_response>` abort** (`promptToolAbortController`, only when `ownedSyntax`
  is set via `config.toolCallSyntax` / `PI_OWNED_TOOLS`) — both require *generated
  output* to trip; our abort is **0-token**, and owned-tools is off by default.
- **Wall-clock / user / caller signal** — none present in `omp -p`; omp's own code
  classifies this as the reason-less internal abort.

So the agent's top-level `AbortController` is being tripped between the tool
result and the next request, specifically on the Sonnet `openai-completions` path,
and the loop then ends instead of retrying.

### Likely scope: the `openai-completions` adapter, not Anthropic itself

The native `packages/ai/src/providers/anthropic.ts` path is independent of
`openai-completions.ts`, and recent issues (#2617, #2619) are both
`openai-completions`/`openai-responses` stream-handling bugs — so this is almost
certainly in the `openai-completions` adapter's handling of Sonnet's stream/tool
turns, **not** in Anthropic's responses per se. Two data points that fit:
`anthropic/claude-opus-4.8` runs 25+ turns fine through the *same* adapter, and a
no-tool-read task on Sonnet completes — i.e. it's an interaction between the
adapter and Sonnet's specific second-turn stream. We expect routing Sonnet through
the **native Anthropic provider (an `ANTHROPIC_API_KEY`)** would avoid it; we
haven't confirmed that (we only have OpenRouter access), but it's the natural place
to look first.

## Impact

Sonnet is effectively **unusable for any multi-turn task that reads a file** through
this provider — it dies after the first tool call most of the time, silently
(looks like an "empty" run that still bills the ~$0.14 cache-write). It also makes
benchmarking Sonnet via OpenRouter impossible.

## Asks

1. **Don't abort here** — identify why the follow-up request's signal is aborted on
   the Sonnet/`openai-completions` path (a tool-result/cache/format quirk?) and stop it.
2. Failing that, **surface the real reason** instead of the generic
   `"Request was aborted"` (the CHANGELOG shows prior work in this direction), and
   **retry** the reason-less internal abort rather than ending the session.
3. A request-level debug flag (beyond `PI_DEBUG_STARTUP`) to dump the
   provider-stream error/abort reason would make this self-diagnosable.

Happy to provide full `--mode json` transcripts for both the Sonnet (aborted) and
opus (working) runs on identical input.
