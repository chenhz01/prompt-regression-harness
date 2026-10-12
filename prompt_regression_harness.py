#!/usr/bin/env python3
"""prompt-regression-harness: snapshot + assertion regression harness for prompts.

Record rendered prompt snapshots, attach assertion rules, then re-run on every
change to catch prompt drift via assertion checks and unified snapshot diffs.
Pure standard library. Deterministic. No LLM calls, no network.
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import sys

MAX_TEMPLATE_LEN = 200_000
MAX_SNAPSHOT_DIFF_LINES = 50
VAR_RE = re.compile(r"\{([^\W\d]\w*)\}")


class HarnessError(Exception):
    """Raised for user-input and data-format problems."""


def render_template(template, variables):
    """Substitute {var} placeholders; single pass, values are not re-expanded."""
    if not isinstance(template, str):
        raise HarnessError("template must be a string, got %s" % type(template).__name__)
    if len(template) > MAX_TEMPLATE_LEN:
        raise HarnessError("template exceeds %d chars" % MAX_TEMPLATE_LEN)
    if variables is None:
        variables = {}
    if not isinstance(variables, dict):
        raise HarnessError("vars must be an object")

    def sub(match):
        key = match.group(1)
        if key not in variables:
            raise HarnessError("missing variable: %s" % key)
        value = variables[key]
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    return VAR_RE.sub(sub, template)


def _check_list_rules(output, rules, key, judge):
    items = rules.get(key)
    if items is None:
        return
    if not isinstance(items, list):
        raise HarnessError("assertions.%s must be an array" % key)
    for i, item in enumerate(items):
        if not judge(item, output):
            return i, item  # first failure
    return None


def check_assertions(output, rules):
    """Return a list of assertion failure dicts; empty list means all passed."""
    failures = []
    if rules is None:
        return failures
    if not isinstance(rules, dict):
        raise HarnessError("assertions must be an object")
    for key, judge, detail in (
        ("contains", lambda n, o: n in o, "missing substring"),
        ("not_contains", lambda n, o: n not in o, "forbidden substring present"),
    ):
        items = rules.get(key)
        if items is None:
            continue
        if not isinstance(items, list):
            raise HarnessError("assertions.%s must be an array" % key)
        for i, needle in enumerate(items):
            if not isinstance(needle, str):
                raise HarnessError("assertions.%s[%d] must be a string" % (key, i))
            if not judge(needle, output):
                failures.append({"rule": key, "index": i, "detail": "%s: %r" % (detail, needle[:80])})
    patterns = rules.get("regex")
    if patterns is not None:
        if not isinstance(patterns, list):
            raise HarnessError("assertions.regex must be an array")
        for i, pattern in enumerate(patterns):
            if not isinstance(pattern, str):
                raise HarnessError("assertions.regex[%d] must be a string" % i)
            try:
                ok = re.search(pattern, output) is not None
            except re.error as exc:
                raise HarnessError("invalid regex %r: %s" % (pattern[:60], exc))
            if not ok:
                failures.append({"rule": "regex", "index": i, "detail": "no match for %r" % pattern[:80]})
    expected = rules.get("equals")
    if expected is not None:
        if not isinstance(expected, str):
            raise HarnessError("assertions.equals must be a string")
        if output != expected:
            failures.append({"rule": "equals", "detail": "exact mismatch (%d vs %d chars)" % (len(output), len(expected))})
    return failures


def snapshot_id(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def diff_snapshots(old, new):
    return list(difflib.unified_diff(
        old.splitlines(), new.splitlines(), fromfile="snapshot", tofile="current", lineterm=""))


def load_cases(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise HarnessError("cannot read cases file: %s" % exc)
    except json.JSONDecodeError as exc:
        raise HarnessError("cases file is not valid JSON: %s" % exc)
    if not isinstance(data, list):
        raise HarnessError("cases must be a JSON array")
    for idx, case in enumerate(data):
        if not isinstance(case, dict):
            raise HarnessError("case #%d must be an object" % idx)
        if "name" not in case or "prompt" not in case:
            raise HarnessError("case #%d must have 'name' and 'prompt'" % idx)
    return data


def safe_case_name(name):
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", str(name)) or "case"
    if len(cleaned) > 120:
        cleaned = cleaned[:120]
    return cleaned


def record(cases_path, snap_dir):
    cases = load_cases(cases_path)
    os.makedirs(snap_dir, exist_ok=True)
    written = []
    for case in cases:
        output = render_template(case["prompt"], case.get("vars"))
        payload = {"name": case["name"], "hash": snapshot_id(output), "rendered": output}
        dest = os.path.join(snap_dir, safe_case_name(case["name"]) + ".json")
        with open(dest, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        written.append(case["name"])
    return written


def run(cases_path, snap_dir, fail_fast=False):
    cases = load_cases(cases_path)
    report = {"total": len(cases), "passed": 0, "failures": []}
    for case in cases:
        issues = []
        try:
            output = render_template(case["prompt"], case.get("vars"))
        except HarnessError as exc:
            issues.append({"rule": "render", "detail": str(exc)})
            output = None
        if output is not None:
            issues.extend(check_assertions(output, case.get("assertions")))
            snap_path = os.path.join(snap_dir, safe_case_name(case["name"]) + ".json")
            if not os.path.exists(snap_path):
                issues.append({"rule": "snapshot", "detail": "no snapshot recorded; run 'record' first"})
            else:
                try:
                    with open(snap_path, "r", encoding="utf-8") as handle:
                        snap = json.load(handle)
                except (json.JSONDecodeError, OSError):
                    issues.append({"rule": "snapshot", "detail": "snapshot file unreadable or corrupt"})
                    snap = None
                if snap is not None:
                    delta = diff_snapshots(str(snap.get("rendered", "")), output)
                    if delta:
                        issues.append({"rule": "snapshot", "detail": "snapshot drift", "diff": delta[:MAX_SNAPSHOT_DIFF_LINES]})
        if issues:
            report["failures"].append({"case": str(case["name"]), "issues": issues})
            if fail_fast:
                break
        else:
            report["passed"] += 1
    return report


def format_report(report):
    lines = ["cases: %d, passed: %d, failed: %d" % (
        report["total"], report["passed"], len(report["failures"]))]
    for failure in report["failures"]:
        lines.append("FAIL %s" % failure["case"])
        for issue in failure["issues"]:
            lines.append("  - %s: %s" % (issue["rule"], issue["detail"]))
            for diff_line in issue.get("diff", [])[:10]:
                lines.append("    " + diff_line)
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="prompt-regression-harness", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_record = sub.add_parser("record", help="render cases and write snapshots")
    p_record.add_argument("cases", help="cases JSON file")
    p_record.add_argument("--snapshots", default="snapshots", help="snapshot directory")
    p_run = sub.add_parser("run", help="render, assert, and diff against snapshots")
    p_run.add_argument("cases", help="cases JSON file")
    p_run.add_argument("--snapshots", default="snapshots", help="snapshot directory")
    p_run.add_argument("--json", action="store_true", help="emit JSON report")
    p_run.add_argument("--fail-fast", action="store_true", help="stop at first failing case")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "record":
            names = record(args.cases, args.snapshots)
            print("recorded %d snapshots in %s" % (len(names), args.snapshots))
            return 0
        report = run(args.cases, args.snapshots, fail_fast=args.fail_fast)
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report))
        return 0 if not report["failures"] else 1
    except HarnessError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
