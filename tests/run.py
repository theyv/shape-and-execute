"""Parallel runner of the sae tests: single test cases spread over worker processes.

    python3 tests/run.py [-j N] [--durations N] [NAME ...]

NAME is a module (`test_sae`), a class or test id (`test_sae.SaeTest.test_x`) or a bare test
method name (`test_x`). No NAME runs every test that `python3 -m unittest discover -s
tests` finds. Prints the failures and exits non-zero on any failure or error.
Standard library only.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys
import time
import unittest
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))


def flatten(suite) -> list:
    tests = []
    for item in suite:
        tests.extend(flatten(item) if isinstance(item, unittest.TestSuite) else [item])
    return tests


def selected(test_id: str, names: list[str]) -> bool:
    if not names:
        return True
    module, method = test_id.split(".", 1)[0], test_id.rsplit(".", 1)[-1]
    return any(name in (module, method, test_id) or test_id.startswith(name + ".") for name in names)


def selected_broken(test: unittest.TestCase, names: list[str]) -> bool:
    """A module that failed to import: its id is `unittest.loader._FailedTest.<module>`."""
    module = test.id().rsplit(".", 1)[-1]
    return not names or any(name == module or name.startswith(module + ".") for name in names)


def run_one(test_id: str, test=None) -> tuple:
    """Run one test case; returns picklable (test_id, outcome, report, seconds)."""
    if test is None:
        test = unittest.defaultTestLoader.loadTestsFromName(test_id)
    start = time.monotonic()
    # unittest echoes a failing test's prints to the stdout it saw at creation; drop that copy
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        result = unittest.TextTestResult(io.StringIO(), descriptions=False, verbosity=0)
        result.buffer = True  # a test's own prints go into its failure report only
        unittest.TestSuite([test]).run(result)
    seconds = time.monotonic() - start
    # One test can both fail and error (in subtests): report every entry, not only the first kind.
    bad = [(outcome, entries) for outcome, entries in (
        ("error", result.errors), ("fail", result.failures),
        ("unexpected success", [(t, "") for t in result.unexpectedSuccesses])) if entries]
    if bad:
        report = "\n".join(report for _, entries in bad for _, report in entries)
        return test_id, " + ".join(outcome for outcome, _ in bad), report, seconds
    return test_id, "skip" if result.skipped else "ok", "", seconds


def init_worker() -> None:
    sys.dont_write_bytecode = True
    sys.path.insert(0, HERE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the sae tests in parallel.")
    parser.add_argument("names", nargs="*", help="module, class, test id or test method name")
    parser.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 1, help="worker processes (default: CPU cores)")
    parser.add_argument("--durations", type=int, default=0, metavar="N", help="print the N slowest tests")
    args = parser.parse_args()

    init_worker()
    tests = flatten(unittest.defaultTestLoader.discover(HERE, pattern="test*.py", top_level_dir=HERE))
    # A module that fails to import becomes unittest.loader._FailedTest: run it here, it reports the error.
    broken = [t for t in tests if isinstance(t, unittest.loader._FailedTest) and selected_broken(t, args.names)]
    ids = [t.id() for t in tests if not isinstance(t, unittest.loader._FailedTest) and selected(t.id(), args.names)]
    unmatched = [n for n in args.names
                 if not any(selected(i, [n]) for i in ids) and not any(selected_broken(t, [n]) for t in broken)]
    if unmatched:
        print(f"run.py: no test matches {', '.join(unmatched)}", file=sys.stderr)
        return 2

    workers = max(1, min(args.jobs, len(ids)))
    start = time.monotonic()
    results = [run_one(t.id(), t) for t in broken]
    with ProcessPoolExecutor(max_workers=workers, initializer=init_worker) as pool:
        for future in as_completed([pool.submit(run_one, i) for i in ids]):
            results.append(future.result())
            print("." if results[-1][1] in ("ok", "skip") else "F", end="", flush=True)
    wall = time.monotonic() - start
    print()

    bad = [r for r in results if r[1] not in ("ok", "skip")]
    for test_id, outcome, report, _ in sorted(bad):
        print("=" * 70 + f"\n{outcome.upper()}: {test_id}\n" + "-" * 70 + f"\n{report}")
    if args.durations:
        print("Slowest tests:")
        for test_id, _, _, seconds in sorted(results, key=lambda r: -r[3])[:args.durations]:
            print(f"  {seconds:6.1f}s  {test_id}")
    skipped = sum(r[1] == "skip" for r in results)
    print("-" * 70 + f"\nRan {len(results)} tests in {wall:.1f}s ({workers} workers)")
    print(f"FAILED ({len(bad)} of {len(results)})" if bad else "OK" + (f" (skipped={skipped})" if skipped else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
