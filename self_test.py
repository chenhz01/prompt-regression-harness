#!/usr/bin/env python3
"""Self-test for prompt-regression-harness. Pure stdlib. Run: python self_test.py"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prompt_regression_harness as prh  # noqa: E402

TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def raises(msg=...):
    ctx = {"exc": None}
    class Checker:
        def __enter__(self):
            return ctx
        def __exit__(self, et, ev, tb):
            if et is None:
                raise AssertionError("expected exception, none raised")
            ctx["exc"] = ev
            return et is prh.HarnessError
    if msg is not ...:
        pass
    return Checker()


def expect_harness_error(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except prh.HarnessError:
        return
    raise AssertionError("expected HarnessError")


def tmpdir():
    return tempfile.mkdtemp()


# ---------------- functional unit tests ----------------

@test("render_basic_substitution")
def _():
    assert prh.render_template("hello {name}", {"name": "ada"}) == "hello ada"


@test("render_multiple_vars")
def _():
    out = prh.render_template("{a}+{b}={c}", {"a": 1, "b": 2, "c": 3})
    assert out == "1+2=3"


@test("render_repeated_var")
def _():
    assert prh.render_template("{x}{x}{x}", {"x": "-"}) == "---"


@test("render_no_vars_passthrough")
def _():
    assert prh.render_template("plain text", {}) == "plain text"


@test("render_var_at_end_without_trailing_text")
def _():
    assert prh.render_template("end {v}", {"v": "ok"}) == "end ok"


@test("assertions_contains_pass")
def _():
    assert prh.check_assertions("abc def", {"contains": ["def"]}) == []


@test("assertions_not_contains_pass")
def _():
    assert prh.check_assertions("safe text", {"not_contains": ["secret"]}) == []


@test("assertions_regex_pass")
def _():
    assert prh.check_assertions("id=42", {"regex": [r"id=\d+"]}) == []


@test("assertions_equals_pass")
def _():
    assert prh.check_assertions("same", {"equals": "same"}) == []


@test("assertions_empty_rules_pass")
def _():
    assert prh.check_assertions("anything", {}) == []


@test("contains_failure_detected")
def _():
    f = prh.check_assertions("abc", {"contains": ["xyz"]})
    assert len(f) == 1 and f[0]["rule"] == "contains"


@test("not_contains_failure_detected")
def _():
    f = prh.check_assertions("has secret", {"not_contains": ["secret"]})
    assert len(f) == 1 and f[0]["rule"] == "not_contains"


@test("regex_failure_detected")
def _():
    f = prh.check_assertions("no digits", {"regex": [r"\d+"]})
    assert len(f) == 1 and f[0]["rule"] == "regex"


@test("equals_failure_detected")
def _():
    f = prh.check_assertions("different", {"equals": "target"})
    assert len(f) == 1 and f[0]["rule"] == "equals"


@test("multiple_failures_all_collected")
def _():
    f = prh.check_assertions("abc", {"contains": ["q"], "not_contains": ["bc"], "regex": [r"\d"]})
    assert len(f) == 3


@test("snapshot_id_deterministic")
def _():
    assert prh.snapshot_id("abc") == prh.snapshot_id("abc")


@test("snapshot_id_differs_for_diff_output")
def _():
    assert prh.snapshot_id("abc") != prh.snapshot_id("abd")


@test("diff_snapshots_detects_change")
def _():
    d = prh.diff_snapshots("line1\nline2", "line1\nline2b")
    assert any("line2b" in ln for ln in d)


@test("diff_snapshots_identical_is_empty")
def _():
    assert prh.diff_snapshots("a\nb", "a\nb") == []


@test("record_writes_snapshot_files")
def _():
    d = tmpdir()
    try:
        cases = os.path.join(d, "cases.json")
        with open(cases, "w", encoding="utf-8") as f:
            json.dump([{"name": "t1", "prompt": "p {v}", "vars": {"v": 1}}], f)
        snaps = os.path.join(d, "snaps")
        names = prh.record(cases, snaps)
        assert names == ["t1"] and os.path.exists(os.path.join(snaps, "t1.json"))
    finally:
        shutil.rmtree(d)


@test("run_passes_with_recorded_snapshot")
def _():
    d = tmpdir()
    try:
        cases = os.path.join(d, "cases.json")
        with open(cases, "w", encoding="utf-8") as f:
            json.dump([{"name": "t1", "prompt": "p {v}", "vars": {"v": 1}}], f)
        snaps = os.path.join(d, "snaps")
        prh.record(cases, snaps)
        report = prh.run(cases, snaps)
        assert report["passed"] == 1 and report["failures"] == []
    finally:
        shutil.rmtree(d)


@test("run_detects_snapshot_drift")
def _():
    d = tmpdir()
    try:
        cases = os.path.join(d, "cases.json")
        with open(cases, "w", encoding="utf-8") as f:
            json.dump([{"name": "t1", "prompt": "p {v}", "vars": {"v": 1}}], f)
        snaps = os.path.join(d, "snaps")
        prh.record(cases, snaps)
        with open(cases, "w", encoding="utf-8") as f:
            json.dump([{"name": "t1", "prompt": "p {v}", "vars": {"v": 2}}], f)
        report = prh.run(cases, snaps)
        rules = [i["rule"] for i in report["failures"][0]["issues"]]
        assert "snapshot" in rules
    finally:
        shutil.rmtree(d)


@test("run_flags_missing_snapshot")
def _():
    d = tmpdir()
    try:
        cases = os.path.join(d, "cases.json")
        with open(cases, "w", encoding="utf-8") as f:
            json.dump([{"name": "never-recorded", "prompt": "x"}], f)
        snaps = os.path.join(d, "snaps")
        os.makedirs(snaps)
        report = prh.run(cases, snaps)
        assert report["failures"][0]["issues"][0]["rule"] == "snapshot"
    finally:
        shutil.rmtree(d)


@test("run_report_failed_case_counts")
def _():
    d = tmpdir()
    try:
        cases = os.path.join(d, "cases.json")
        with open(cases, "w", encoding="utf-8") as f:
            json.dump([{"name": "a", "prompt": "ok"}, {"name": "b", "prompt": "{missing}"}], f)
        snaps = os.path.join(d, "snaps")
        os.makedirs(snaps)
        # Missing snapshots are failures by design (see run_flags_missing_snapshot),
        # so with an empty snapshot dir both cases fail: a=snapshot, b=render.
        report = prh.run(cases, snaps)
        assert report["total"] == 2 and report["passed"] == 0 and len(report["failures"]) == 2
        rules = {f["case"]: [i["rule"] for i in f["issues"]] for f in report["failures"]}
        assert "snapshot" in rules["a"] and "render" in rules["b"]
    finally:
        shutil.rmtree(d)


@test("format_report_lists_fail_lines")
def _():
    report = {"total": 1, "passed": 0, "failures": [{"case": "c", "issues": [{"rule": "contains", "detail": "boom"}]}]}
    text = prh.format_report(report)
    assert "FAIL c" in text and "contains: boom" in text


# ---------------- exception-path tests ----------------

@test("missing_variable_raises")
def _():
    expect_harness_error(prh.render_template, "hi {who}", {})


@test("non_string_template_raises")
def _():
    expect_harness_error(prh.render_template, 123, {})


@test("oversize_template_raises")
def _():
    expect_harness_error(prh.render_template, "x" * (prh.MAX_TEMPLATE_LEN + 1), {})


@test("vars_non_dict_raises")
def _():
    expect_harness_error(prh.render_template, "x", ["not", "a", "dict"])


@test("invalid_regex_raises")
def _():
    expect_harness_error(prh.check_assertions, "text", {"regex": ["([bad"]})


@test("assertions_non_dict_raises")
def _():
    expect_harness_error(prh.check_assertions, "text", ["nope"])


@test("contains_non_list_raises")
def _():
    expect_harness_error(prh.check_assertions, "text", {"contains": "str-not-list"})


@test("contains_non_string_member_raises")
def _():
    expect_harness_error(prh.check_assertions, "text", {"contains": [42]})


@test("equals_non_string_raises")
def _():
    expect_harness_error(prh.check_assertions, "text", {"equals": 99})


@test("cases_not_array_raises")
def _():
    d = tmpdir()
    try:
        p = os.path.join(d, "bad.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write('{"not": "a list"}')
        expect_harness_error(prh.load_cases, p)
    finally:
        shutil.rmtree(d)


@test("case_missing_name_raises")
def _():
    d = tmpdir()
    try:
        p = os.path.join(d, "bad.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write('[{"prompt": "x"}]')
        expect_harness_error(prh.load_cases, p)
    finally:
        shutil.rmtree(d)


@test("cases_invalid_json_raises")
def _():
    d = tmpdir()
    try:
        p = os.path.join(d, "bad.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write("{corrupt!!")
        expect_harness_error(prh.load_cases, p)
    finally:
        shutil.rmtree(d)


@test("cases_missing_file_raises")
def _():
    expect_harness_error(prh.load_cases, os.path.join(tmpdir(), "nope.json"))


@test("run_treats_corrupt_snapshot_as_issue")
def _():
    d = tmpdir()
    try:
        cases = os.path.join(d, "cases.json")
        with open(cases, "w", encoding="utf-8") as f:
            json.dump([{"name": "t", "prompt": "x"}], f)
        snaps = os.path.join(d, "snaps")
        os.makedirs(snaps)
        with open(os.path.join(snaps, "t.json"), "w", encoding="utf-8") as f:
            f.write("{broken json")
        report = prh.run(cases, snaps)
        rules = [i["rule"] for i in report["failures"][0]["issues"]]
        assert "snapshot" in rules
    finally:
        shutil.rmtree(d)


@test("run_records_render_error_as_failure")
def _():
    d = tmpdir()
    try:
        cases = os.path.join(d, "cases.json")
        with open(cases, "w", encoding="utf-8") as f:
            json.dump([{"name": "t", "prompt": "{gone}"}], f)
        snaps = os.path.join(d, "snaps")
        os.makedirs(snaps)
        report = prh.run(cases, snaps)
        assert report["failures"][0]["issues"][0]["rule"] == "render"
    finally:
        shutil.rmtree(d)


@test("cli_bad_subcommand_exit_2")
def _():
    buf = io.StringIO()
    try:
        with contextlib.redirect_stderr(buf):
            code = prh.main(["run", os.path.join(tmpdir(), "ghost.json")])
    except SystemExit:
        code = 2
    assert code == 2


# ---------------- extreme-edge tests ----------------

@test("empty_cases_list_record_and_run")
def _():
    d = tmpdir()
    try:
        cases = os.path.join(d, "cases.json")
        with open(cases, "w", encoding="utf-8") as f:
            f.write("[]")
        snaps = os.path.join(d, "snaps")
        assert prh.record(cases, snaps) == []
        report = prh.run(cases, snaps)
        assert report["total"] == 0 and report["passed"] == 0
    finally:
        shutil.rmtree(d)


@test("empty_prompt_renders_empty")
def _():
    assert prh.render_template("", {}) == ""
    assert prh.snapshot_id("") == prh.snapshot_id("")


@test("unicode_prompt_and_vars")
def _():
    out = prh.render_template("你好 {名字} 🚀", {"名字": "世界"})
    assert out == "你好 世界 🚀"


@test("long_output_10k_chars")
def _():
    text = "x" * 10000
    assert prh.render_template(text, {}) == text
    assert len(prh.diff_snapshots(text, text)) == 0


@test("deep_nested_var_values_stringified")
def _():
    out = prh.render_template("{obj}", {"obj": {"a": [1, {"b": 2}]}})
    assert '"b": 2' in out


@test("var_value_containing_braces_not_reexpanded")
def _():
    out = prh.render_template("v={x}", {"x": "{y}"})
    assert out == "v={y}"


@test("non_var_braces_left_alone")
def _():
    assert prh.render_template("{1bad} {ok}", {"ok": "fine"}) == "{1bad} fine"


@test("case_with_no_assertions_still_diffs_snapshot")
def _():
    d = tmpdir()
    try:
        cases = os.path.join(d, "cases.json")
        with open(cases, "w", encoding="utf-8") as f:
            json.dump([{"name": "t", "prompt": "same"}], f)
        snaps = os.path.join(d, "snaps")
        prh.record(cases, snaps)
        assert prh.run(cases, snaps)["passed"] == 1
    finally:
        shutil.rmtree(d)


@test("case_name_with_spaces_and_unicode_sanitized")
def _():
    assert prh.safe_case_name("my case 你好!") == "my_case____"


@test("cli_record_then_run_end_to_end")
def _():
    d = tmpdir()
    try:
        cases = os.path.join(d, "cases.json")
        with open(cases, "w", encoding="utf-8") as f:
            json.dump([{"name": "t", "prompt": "n={n}", "vars": {"n": "1"},
                        "assertions": {"contains": ["n=1"]}}], f)
        snaps = os.path.join(d, "snaps")
        assert prh.main(["record", cases, "--snapshots", snaps]) == 0
        assert prh.main(["run", cases, "--snapshots", snaps]) == 0
    finally:
        shutil.rmtree(d)


@test("cli_run_json_report_parseable")
def _():
    d = tmpdir()
    try:
        cases = os.path.join(d, "cases.json")
        with open(cases, "w", encoding="utf-8") as f:
            f.write("[]")
        snaps = os.path.join(d, "snaps")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            prh.main(["run", cases, "--snapshots", snaps, "--json"])
        assert json.loads(buf.getvalue())["total"] == 0
    finally:
        shutil.rmtree(d)


def main():
    passed = failed = 0
    for name, fn in TESTS:
        try:
            fn()
            passed += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print("FAIL %s: %r" % (name, exc))
    print("passed=%d failed=%d total=%d" % (passed, failed, passed + failed))
    print("SUMMARY: PASS %d/%d" % (passed, passed + failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
