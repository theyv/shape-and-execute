"""Command ask: questions the orchestrator puts to the owner ([ASK-COMMAND]). An ask opens with
`sae ask` (event `ask.opened`) and closes as a side effect of logging the owner's answer with
`--by human`, or with `sae ask --answered` (event `ask.closed`). The events are the only record.
Also: the reminder line of `sae next` ([ASK-REMINDER]) and the owner-wait data the viewer draws."""

from __future__ import annotations

from .common import EXIT_OK, EXIT_USAGE, emit, fail
from .config import ask_signal
from .gitutil import find_root
from .tasks import Task, open_task, parked_reason


def open_asks(task: Task) -> list[dict]:
    """The open asks, oldest first: `{"n": int, "question": str, "job": str | None, "at": iso}`."""
    opened: dict[int, dict] = {}
    closed: set = set()
    for event in task.events():
        if event.get("type") == "ask.opened" and isinstance(event.get("n"), int):
            opened[event["n"]] = {"n": event["n"], "question": event.get("question") or "",
                                  "job": event.get("job"), "at": event.get("at")}
        elif event.get("type") == "ask.closed":
            closed.update(n for n in event.get("asks") or [] if isinstance(n, int))
    return [ask for n, ask in sorted(opened.items()) if n not in closed]


def close_asks(task: Task, asks: list[dict], how: str) -> list[int]:
    """Closes these asks (event `ask.closed`, `how`: log | answered); returns their numbers."""
    numbers = [a["n"] for a in asks]
    if numbers:
        task.event("ask.closed", asks=numbers, how=how)
    return numbers


def close_answered_asks(task: Task, job: str | None) -> list[int]:
    """A `--by human` log answers the open asks of its `--job`, or without `--job` the open asks
    without a job."""
    return close_asks(task, [a for a in open_asks(task) if a["job"] == job], "log")


def asks_closed_text(numbers: list[int]) -> str:
    return ("Closed ask " if len(numbers) == 1 else "Closed asks ") + ", ".join(str(n) for n in numbers) + "."


def ask_reminder_line(task: Task) -> str | None:
    """The reminder line of `sae next` ([ASK-REMINDER]): only in phase executing with the ask signal
    on ([ASK-SETTING]); else None, and nothing mentions sae ask."""
    if task.phase != "executing" or not ask_signal(task.settings)["on"]:
        return None
    return (f"Before you ask the owner anything: sae ask {task.id} \"<question>\" [--job <ID>]. After the answer: "
            f"sae log {task.id} decision \"<answer>\" --by human [--job <ID>], or sae ask {task.id} --answered.")


def owner_wait(task: Task) -> dict:
    """What the viewer draws for "waiting for the owner" ([WAIT-FRAMES], [WAIT-TAB-TITLE]).

    `{"asks": [open ask, as open_asks], "waiting": [reason, ...]}`. `asks` lists every open ask in
    any phase; an ask with a `job` names the job card that gets the red frame. `waiting` is empty
    unless the task is in phase executing; then it holds one reason per thing that waits for the
    owner, in this order: open asks, parked jobs, the parked task, active holds. A reason is
    `{"kind": "ask" | "parked" | "parked-task" | "hold", "job": str | None, "text": one line}`:
    the question, the parked job's reason, the integration round that parks the task, or the hold
    and its reason. The task waits for the owner exactly when `waiting` is not empty."""
    from .graph import active_holds, integration_parked  # late import: graph imports findings, which imports this
    asks = open_asks(task)
    waiting: list[dict] = []
    if task.phase == "executing":
        waiting += [{"kind": "ask", "job": a["job"], "text": a["question"]} for a in asks]
        waiting += [{"kind": "parked", "job": i, "text": f"{i} is parked: {parked_reason(task, i)}"}
                    for i, j in task.jobs.items() if j["status"] == "parked"]
        parked_round = integration_parked(task)
        if parked_round:
            waiting.append({"kind": "parked-task", "job": parked_round,
                            "text": f"The task is parked: {parked_round} still requires changes after a fix round."})
        for job_id in active_holds(task):
            reason = ((task.info.get("holds") or {}).get(job_id) or {}).get("reason")
            waiting.append({"kind": "hold", "job": job_id,
                            "text": f"Hold after {job_id}" + (f": {reason}" if reason else "")})
    return {"asks": asks, "waiting": waiting}


def cmd_ask(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        if args.job:
            task.job(args.job)  # an unknown job fails with exit 1
        if args.answered:
            if args.question:
                fail(EXIT_USAGE, "--answered closes asks; it takes no question.")
            asks = [a for a in open_asks(task) if not args.job or a["job"] == args.job]
            numbers = close_asks(task, asks, "answered")
            emit(args, asks_closed_text(numbers) if numbers else "No open ask" + (f" of {args.job}." if args.job else "."),
                 {"closed": numbers, "open": open_asks(task)})
            return EXIT_OK
        question = (args.question or "").strip()
        if not question:
            fail(EXIT_USAGE, 'Give the question: sae ask <task> "<question>" [--job <ID>], or --answered.')
        n = 1 + sum(1 for e in task.events() if e.get("type") == "ask.opened")
        task.event("ask.opened", n=n, question=question, **({"job": args.job} if args.job else {}))
        job = f" --job {args.job}" if args.job else ""
        emit(args, "\n".join([f"Ask {n} is open. Ask the owner now. After the answer:",
                              f"  sae log {task.id} decision \"<answer>\" --by human{job}",
                              f"Or: sae ask {task.id} --answered"]),
             {"ask": n, "question": question, "job": args.job, "open": open_asks(task)})
    return EXIT_OK


def register_ask(sub, command):
    """Add the `ask` command to the parser."""
    p = command(sub, "ask", "Record a question to the owner; the viewer shows that the task waits for them.",
                "Run it before you ask the owner anything during execution. With --job, that job's card is\n"
                "marked too. Several asks can be open. Logging the answer closes the asks it belongs to:\n"
                "sae log <task> decision \"<answer>\" --by human --job <ID> closes the open asks of that job;\n"
                "a --by human log without --job closes the open asks without a job. --answered closes every\n"
                "open ask (with --job: that job's). sae status lists the open asks.",
                ['ask claims-status "Keep the v1 envelope or move to v2?"',
                 'ask claims-status "Drop the CSV export?" --job STATUS-API',
                 "ask claims-status --answered"], [0, 1], cmd_ask)
    p.add_argument("task")
    p.add_argument("question", nargs="?", help="the question, as you put it to the owner")
    p.add_argument("--job", metavar="ID", help="the job the question is about")
    p.add_argument("--answered", action="store_true", help="close the open asks: the owner answered")
