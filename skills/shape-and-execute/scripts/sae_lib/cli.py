"""Assembles the argument parser from the commands of each module; main()."""

from __future__ import annotations

import argparse
import sys

from .common import EXIT_CODES_HELP, EXIT_USAGE, Parser, SaeError, wrap_notice_lines
from .control import register_hold
from .doctor import register_doctor
from .findings import register_decision, register_finding, register_log
from .lifecycle import register_abandon, register_finish, register_new, register_start
from .planning import register_approve, register_check, register_job, register_set
from .progress import register_dispatch, register_next, register_status
from .reviews import register_collect, register_merge
from .setup_mode import register_project, register_setup
from .viewer import register_view


CODE_TEXT = {0: "ok", 1: "usage or precondition error", 2: "user config missing or invalid: offer setup mode",
             3: "gate refused", 4: "git problem (dirty tree, merge conflict, worktree or setup failure)",
             5: "re-run verify failed: resume the same worker"}


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="print a JSON object instead of text")
    parser = Parser(
        prog="sae", formatter_class=argparse.RawDescriptionHelpFormatter,
        description="The CLI of the shape-and-execute skill. It records task state, checks gates, computes what is\n"
                    "ready and which model runs it, prints dispatch prompts, and moves git branches and worktrees.\n"
                    "Agents decide; sae never calls a model and never pushes.\n\n"
                    "Invoke: python3 <SKILL_DIR>/scripts/sae.py <command> [args]. <task> is a task ID or a unique\n"
                    "end of it (usually the slug). Details of one command: sae <command> --help.",
        epilog=EXIT_CODES_HELP)
    sub = parser.add_subparsers(dest="command", metavar="<command>", title="commands", parser_class=Parser)

    def command(parent, name: str, summary: str, details: str, examples: list[str], codes: list[int], func,
                parents=True):
        epilog = "Examples:\n" + "\n".join(f"  sae {e}" for e in examples)
        epilog += "\n\nExit codes:\n" + "\n".join(f"  {c}  {CODE_TEXT[c]}" for c in codes)
        p = parent.add_parser(name, help=summary, description=f"{summary}\n\n{details}".strip(), epilog=epilog,
                              formatter_class=argparse.RawDescriptionHelpFormatter,
                              parents=[common] if parents else [])
        p.set_defaults(func=func)
        return p

    register_new(sub, command)
    register_status(sub, command)
    register_set(sub, command)
    register_approve(sub, command)
    register_check(sub, command)
    register_start(sub, command)
    register_finish(sub, command)
    register_abandon(sub, command)
    register_view(sub, command)
    job = register_job(sub, command)
    register_next(sub, command)
    register_dispatch(sub, command)
    register_hold(sub, command)
    register_collect(sub, command)
    register_merge(sub, command)
    decision = register_decision(sub, command)
    register_log(sub, command)
    finding = register_finding(sub, command)
    setup = register_setup(sub, command)
    project = register_project(sub, command)
    register_doctor(sub, command)

    fill_missing_help(parser)
    for name, group in (("job", job), ("decision", decision), ("finding", finding), ("setup", setup),
                        ("project", project)):
        group.set_defaults(func=lambda args, g=group: (g.print_help(), EXIT_USAGE)[1])
    return parser


ARGUMENT_HELP = {
    "task": "task ID or a unique end of it (usually the slug)",
    "id": "job ID, UPPER-KEBAB",
    "title": "short title",
    "file": "path of the finding file",
    "summary": "one line: what was decided, amended or noted",
    "type": "what to log",
    "gate": "which gate",
    "pairs": "settings to change, for example execution=economy",
    "resume": "run the job again (running, parked or failed); needs --reason",
    "reason": "why: required with --resume, for graph changes during execution, and for abandon",
    "review": "flag the job for review (review point selected-jobs)",
    "final": "the final validation job; runs after every other job and review",
    "fix_of": "the writer job this fix job repairs; it works in that job's workspace and branch",
    "needs": "comma list of job IDs that must be done first (writers: also merged)",
    "difficulty": "mechanical | normal | hard; with the phase level it selects the routing cell",
    "kind": "what the job does",
    "allow_dirty": "start although tracked files outside .tasks/ have uncommitted changes",
    "open": "open the URL in the default browser",
    "repo": "also check this repository: .tasks/, repo profile, a throwaway worktree, the viewer",
    "tokens": "token use of the subagent, when the harness reports it",
    "duration_s": "run time of the subagent in seconds, when the harness reports it",
    "agent_ref": "the harness agent ID, to resume the same agent later",
    "outcome": "why the finding is closed",
    "job": "the job this entry is about",
    "decision_class": "decision class",
    "amend_id": "the amendment ID under ## Amendments in specs.md",
    "from_job": "the parked job whose decision request this answers",
    "confidence": "how sure you are",
    "source": "where it came from: <task>/<JOB-ID> for findings, <task> for backlog items",
    "paths": "comma list of related paths",
    "harness": "orchestrator harness, when it differs from the one recorded at sae new",
    "accept_review": "merge although the last review said changes-required; logs a decision with this reason",
    "by": "who decided: human, agent or joint (agent entries are listed in the final report)",
}


def fill_missing_help(parser: argparse.ArgumentParser) -> None:
    """Every option and argument gets a help line (agents read --help as the reference)."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                fill_missing_help(child)
        elif action.help is None and action.dest in ARGUMENT_HELP:
            action.help = ARGUMENT_HELP[action.dest]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return EXIT_USAGE
    try:
        return int(args.func(args) or 0)
    except SaeError as exc:
        print(wrap_notice_lines(str(exc)), file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        return 130
