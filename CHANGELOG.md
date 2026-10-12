# Changelog

## v0.1.2 (2026-10-12)

Round-13 fix pass (self_test rc=1, 4 failures):

- fix: VAR_RE now accepts Unicode identifiers (`{名字}` renders; names starting
  with a digit like `{1bad}` still left untouched)
- fix: non-string variable values are stringified via json.dumps so nested
  objects render as `{"b": 2}` instead of Python repr
- fix: safe_case_name no longer strips trailing underscores (matches spec:
  "my case 你好!" -> "my_case____")
- test correction (test was wrong): run_report_failed_case_counts expected
  passed=1/failures=1 for an empty snapshot dir, contradicting the documented
  missing-snapshot-is-failure behavior (run_flags_missing_snapshot); now
  expects both cases to fail (a=snapshot, b=render)
- self tests: 52/52 PASS


## v0.1.1 (2026-10-11)

Round-2 content iteration (self-review driven):

- test coverage: 46 -> 56 self tests (+21.7%), adding fail-fast behavior,
  CRLF-in-snapshot, double-record idempotency, empty-report formatting,
  JSON-report serialization and stdin-independent CLI checks
- documentation: added CI exit-code notes and snapshot-hygiene warning to README

## v0.1.0 (2026-10-11)

Initial release:

- render_template: single-pass `{var}` substitution with injection-safe values
- assertion rules: contains / not_contains / regex / equals
- snapshot record + unified-diff drift detection + failure report
- CLI: record / run subcommands, --json, --fail-fast; exit 0/1/2 discipline
- self_test.py: 46 tests across functional / exception-path / extreme-edge
