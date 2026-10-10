"""Model resolution: which model runs which job."""

from __future__ import annotations

from .common import EXIT_USAGE, LEVEL_PHASE_OF_KIND, fail
from .config import cfg
from .tasks import Task


def resolve_model(task: Task, job: dict, config: dict, harness: str | None = None,
                  provider: str | None = None) -> dict:
    settings = task.settings
    if job["kind"] == "review":
        chosen = provider or harness or settings["review"]["provider"]
        rung = cfg(config, f"review_level_map.{settings['levels']['review']}")
    else:
        chosen = harness or task.info.get("orchestrator_harness")
        if not chosen:
            fail(EXIT_USAGE, "The task has no orchestrator harness. Add --harness claude|codex.")
        level = settings["levels"][LEVEL_PHASE_OF_KIND.get(job["kind"], "execution")]
        rung = cfg(config, f"level_map.{level}.{job['difficulty']}")
    entry = cfg(config, f"rungs.{chosen}.{rung}")
    model = cfg(config, f"rungs.{chosen}.{rung}.model")
    effort = entry.get("effort") if chosen == "codex" else None
    return {"harness": chosen, "rung": rung, "model": model, "effort": effort}
