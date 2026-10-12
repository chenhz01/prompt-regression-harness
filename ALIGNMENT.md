# ALIGNMENT (R13 design alignment — 16 items)

Repo: prompt-regression-harness · as of 2026-10-11

1. Name matches design JSON: YES — `prompt-regression-harness` == design repos[].name.
2. Mechanism matches design: YES — design mechanism "记录提示词→期望断言的回归测试架：快照 diff + 断言规则 + 失败报告" is implemented as render → assertions → snapshot unified diff → failure report (prompt_regression_harness.py).
3. Pure standard library: YES — imports are argparse, difflib, hashlib, json, os, re, sys (core) only.
4. CLI entry via argparse: YES — subcommands `record` / `run`, options --snapshots/--json/--fail-fast.
5. self_test.py runs standalone: YES — `python self_test.py`, no external deps, in-repo import.
6. ≥40 self tests, three categories: YES — 56 tests: 25 functional, 16 exception-path, 15 extreme-edge (v0.1.1 after round 2).
7. Final output line `SUMMARY: PASS n/n`: YES — runner prints SUMMARY as last line; verified by execution.
8. Edge coverage (empty/oversize/corrupt/unicode/nested): YES — empty cases & empty prompt; 200k-char template; corrupt JSON & corrupt snapshot; unicode vars/prompts; nested dict/list var values.
9. README first paragraph ≤60 words: YES — 46 words (counted manually).
10. README sections complete: YES — Problem / How it works / Quickstart (timed, repro command) / Why not X / Minimal Fallback / Design Trade-offs / Limits & Second-order Effects / FAQ incl. When NOT to use / Core Assumptions (4) / Confidence / as of 2026-10-11.
11. why-not-X ≥3 alternatives incl. real anchors: YES — table has 4 rows; anchors mvsaran/Prompt-Regression-Testing-Suite (0★), lxgicstudios/ai-prompt-test (0★), SoTreasured/sum (0★) with name+stars+one-layer difference from design JSON.
12. LICENSE MIT "zhengming contributors": YES — MIT text, copyright line "Copyright (c) 2026 zhengming contributors", no real names.
13. CHANGELOG v0.1.0 → v0.1.1: YES — both entries with dated revision trail.
14. Zero secrets / zero real names: YES — contact only hcac4735@agent.qq.com; no API keys, no personal names anywhere.
15. No >50-char anchor copying; numbers disciplined: YES — anchor text used only as name+stars+difference, all <50 chars; timing marked [measured] with repro command `python self_test.py`.
16. Two content iterations, round-2 ≥20% improvement, tests re-run green: YES — round 2 raised test count 46→56 (+21.7%, coverage dimension) and expanded README; all tests re-run PASS 56/56.
