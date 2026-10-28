#!/usr/bin/env python3
"""Grader-only deterministic checks. This program is NOT a security sandbox.

Use only inside a disposable offline grading sandbox. Never mount this file or
fixtures.json in a participant's workspace. --self-check never runs submissions.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
MAX_STREAM_BYTES = 65536
CASE_TIMEOUT_SECONDS = 5


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def reject_constant(value):
    raise ValueError("non-finite JSON number")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def equal_json(actual, expected, path=()):
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and set(actual) == set(expected)
            and all(equal_json(actual[key], value, path + (key,))
                    for key, value in expected.items())
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(equal_json(a, b, path + (str(i),))
                    for i, (a, b) in enumerate(zip(actual, expected)))
        )
    if expected is None:
        return actual is None
    if isinstance(expected, bool):
        return type(actual) is bool and actual is expected
    if isinstance(expected, (int, float)):
        if type(actual) not in (int, float):
            return False
        if not math.isfinite(actual):
            return False
        # Rate and uplift fields are JSON numbers, including exact 0 and 100.
        if path and path[-1] in ("rate", "uplift_pp"):
            return abs(actual - expected) <= 0.0000011
        return type(actual) is int and actual == expected
    return type(actual) is type(expected) and actual == expected


def run_submission(submission, payload):
    raw_input = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    # Files bound captured memory even when the candidate emits excessive output.
    # Actual disk/CPU/process/network limits must be imposed by the outer sandbox.
    with tempfile.TemporaryFile() as out_handle, tempfile.TemporaryFile() as err_handle:
        environment = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8",
                       "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
        process = subprocess.Popen(
            [sys.executable, "-I", "-B", str(submission)],
            stdin=subprocess.PIPE, stdout=out_handle, stderr=err_handle,
            cwd=str(submission.parent), env=environment,
        )
        try:
            process.communicate(raw_input, timeout=CASE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            return {"ok": False, "reason": "timeout"}
        out_handle.seek(0)
        err_handle.seek(0)
        stdout = out_handle.read(MAX_STREAM_BYTES + 1)
        stderr = err_handle.read(MAX_STREAM_BYTES + 1)
        if len(stdout) > MAX_STREAM_BYTES or len(stderr) > MAX_STREAM_BYTES:
            return {"ok": False, "reason": "stream_limit"}
        if process.returncode != 0:
            return {"ok": False, "reason": "nonzero_exit"}
        try:
            value = json.loads(stdout.decode("utf-8"),
                               object_pairs_hook=unique_object,
                               parse_constant=reject_constant)
        except (UnicodeDecodeError, ValueError, RecursionError):
            return {"ok": False, "reason": "invalid_json"}
        return {"ok": True, "value": value}


def check_protocol():
    tasks = load_json(ROOT / "tasks.json")
    grading = load_json(ROOT / "grading.json")
    fixtures = load_json(ROOT / "fixtures.json")
    task_ids = {task["id"] for task in tasks["tasks"]}
    assert task_ids == {"C1", "C2", "N1", "N2"}
    assert tasks["common_limits"]["wall_seconds"] == 300
    assert all(len(grading["tasks"][task]["criteria"]) == 6
               for task in ("N1", "N2"))
    assert "method_" not in json.dumps(tasks, ensure_ascii=False)
    ids = [case["id"] for case in fixtures["cases"]]
    assert len(ids) == len(set(ids)) == 14
    for task in ("C1", "C2"):
        cases = [case for case in fixtures["cases"] if case["task_id"] == task]
        assert len(cases) == 7 and sum(case["weight"] for case in cases) == 12
        assert sum(case["visibility"] == "public" for case in cases) == 1
        assert all(case["weight"] == (0 if case["visibility"] == "public" else 2)
                   for case in cases)
        assert all("input" in case and "expected" in case for case in cases)
    assert equal_json({"n": 2, "rate": 0.5}, {"n": 2, "rate": 0.5})
    assert not equal_json({"n": True}, {"n": 1})
    assert not equal_json({"n": 2.0}, {"n": 2})
    assert equal_json({"rate": 0.0}, {"rate": 0})
    assert not equal_json({"x": 1, "extra": 2}, {"x": 1})
    print(json.dumps({"status": "protocol_valid", "task_count": 4,
                      "coding_cases": 14, "participant_runs": 0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--task", choices=("C1", "C2"))
    parser.add_argument("--submission", type=Path)
    parser.add_argument("--public-only", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        if args.task or args.submission or args.public_only:
            parser.error("--self-check does not accept grading arguments")
        check_protocol()
        return
    if not args.task or args.submission is None:
        parser.error("--task and --submission are required for grading")
    submission = args.submission.resolve()
    if not submission.is_file():
        parser.error("submission must be an existing solution.py")
    fixtures = load_json(ROOT / "fixtures.json")
    cases = [case for case in fixtures["cases"] if case["task_id"] == args.task
             and (not args.public_only or case["visibility"] == "public")]
    report = []
    for case in cases:
        passes = []
        for mode in ("literal", "reverse_input"):
            payload = json.loads(json.dumps(case["input"]))
            if mode == "reverse_input":
                key = "events" if args.task == "C1" else "records"
                payload[key].reverse()
            result = run_submission(submission, payload)
            matched = result["ok"] and equal_json(result["value"], case["expected"])
            passes.append({"mode": mode, "passed": bool(matched),
                           "reason": "match" if matched else
                           ("wrong_result" if result["ok"] else result["reason"])})
        report.append({"id": case["id"], "points": int(case["weight"] * sum(p["passed"] for p in passes) / 2),
                       "max_points": case["weight"], "checks": passes})
    print(json.dumps({"task_id": args.task, "points": sum(r["points"] for r in report),
                      "max_points": sum(r["max_points"] for r in report), "cases": report},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
