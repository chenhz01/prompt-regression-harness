# prompt-regression-harness

A tiny regression harness for rendered prompts. Record snapshots, attach `contains` / `not_contains` / `regex` / `equals` assertions, and re-run on every change to catch prompt drift with a reviewable failure report. Single file, pure Python standard library, no LLM calls, no network, fully deterministic.

**Status:** v0.1.1 · Confidence: high (deterministic structural checks) · as of 2026-10-11

## Problem

Prompt templates get edited constantly — wording tweaks, new variables, swapped examples — and rendered output drifts silently. Teams notice when a user complains, not when the prompt changed. There is no cheap, offline way to diff *rendered* prompts and enforce simple expectations on them without wiring up a testing framework.

## How it works

1. **Cases file** (JSON array): each case has `name`, `prompt` (a `{var}` template), optional `vars`, optional `assertions`.
2. **Record**: every case is rendered deterministically and a snapshot (`hash` + full `rendered` text) is written to a snapshot directory.
3. **Run**: cases are re-rendered; assertion rules are checked; rendered output is diffed (unified diff, `difflib`) against the stored snapshot. Any render error, assertion failure, or snapshot drift lands in a failure report; CLI exit code is `1`.

## Quickstart

```bash
# ~0.5 s total [measured; reproduce: python self_test.py]
python self_test.py

cat > cases.json <<'EOF'
[
  {"name": "greet", "prompt": "Hello {user}, you have {n} items.",
   "vars": {"user": "ada", "n": 3},
   "assertions": {"contains": ["Hello ada"], "not_contains": ["error"], "regex": ["\\d+"]}}
]
EOF

python prompt_regression_harness.py record cases.json --snapshots snaps   # ~0.1 s
python prompt_regression_harness.py run cases.json --snapshots snaps      # ~0.1 s, exit 0
# ... edit the prompt ...
python prompt_regression_harness.py run cases.json --snapshots snaps      # exit 1 + diff
```

## Why not X

| Alternative | Stars | Why not this |
| --- | --- | --- |
| [mvsaran/Prompt-Regression-Testing-Suite](https://github.com/mvsaran/Prompt-Regression-Testing-Suite) | 0 ★ | Java-based AI quality-engineering framework: heavier install and framework lock-in. This is one stdlib Python file with snapshot diff built in. |
| [lxgicstudios/ai-prompt-test](https://github.com/lxgicstudios/ai-prompt-test) | 0 ★ | Prompt unit tests and assertions, but no recorded-snapshot diffing of full renders. Here every render is hashed and diffed. |
| [SoTreasured/sum](https://github.com/SoTreasured/sum) | 0 ★ | A prompt/test-case demo, not a reusable harness. |
| pytest + golden files | — | Works, but you re-implement render/assert/report plumbing each time; exit-code discipline for CI is built in here. |

## Minimal Fallback

If you cannot run this: render the prompt twice (old vs new commit), `diff old.txt new.txt`, and manually grep for the substrings you care about. That reproduces ~70% of the value with zero tooling.

## Design Trade-offs

- **Snapshot whole renders, not token streams** — diffs are readable, but formatting-only changes show as drift. Deliberate: formatting *is* behavior for prompts.
- **Assertions are substring/regex only** — no model-judge scoring. Deterministic and free, at the cost of not catching semantic drift.
- **Single JSON cases file** — no per-case directories or YAML; trivially reviewable, harder to share cases across repos.
- **Single-pass `{var}` substitution** — values containing `{y}` are not re-expanded (injection-safe by construction).

## Limits & Second-order Effects

- Rendered output is compared against *itself over time*, not against a spec. A bad prompt recorded as a snapshot "locks in" the badness — re-record consciously.
- Regex assertions can become their own maintenance burden; keep them short.
- Because it never calls a model, this catches *structural* regressions only. Second-order: teams may over-trust a green run and skip qualitative review.
- Snapshot files are plaintext; do not record prompts containing secrets.

## FAQ

**When NOT to use this?**
When you need to evaluate *model responses* to a prompt (use an eval framework with an LLM judge), when prompts are generated dynamically at runtime, or when your team already runs a full LLM evaluation pipeline.

**Does it call an LLM?** Never. It tests the prompt text itself.

**Can two cases share a snapshot name?** Sanitized names may collide; use distinct case names.

**Windows-safe?** Yes — pure stdlib, path handling via `os.path`.

## Core Assumptions

1. Rendered prompt text is a meaningful test surface (formatting changes are regressions worth catching).
2. Cases are static and known in advance; dynamic prompt construction is out of scope.
3. Assertion needs are mostly substring/regex-shaped; if you need semantic scoring, this is the wrong layer.
4. Snapshots are checked into version control next to the cases file.

## LICENSE

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 zhengming contributors.
Contact: hcac4735@agent.qq.com

---

Part of the [zhengming-toolbox](https://github.com/chenhz01/zhengming-toolbox) — 55 purpose-built AI-engineering tools across neglected niches.

Related tools: [prompt-version-diff](https://github.com/chenhz01/prompt-version-diff) · [prompt-template-merge](https://github.com/chenhz01/prompt-template-merge) · [token-budget-clamp](https://github.com/chenhz01/token-budget-clamp)
