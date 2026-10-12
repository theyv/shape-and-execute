# Nested worktrees and test runners

Question: if job worktrees lived inside the repository (for example `.tasks/.worktrees/<x>/`),
would tools run in the main checkout pick them up?

Tested 2026-10-06 by a research subagent with a real worktree:

| Tool | Version | Scans `.tasks/.worktrees/<x>/` by default? | Note |
|---|---|---|---|
| Jest | 30.5.2 | **yes** | default ignore is only `/node_modules/`; also warns "Haste module naming collision" |
| Vitest | 5.0.3 | **yes** | default exclude is `**/node_modules/**` and `**/.git/**` |
| pytest | 9.1.1 | no | `norecursedirs` default includes `.*`; an explicit path still collects |
| TypeScript `tsc` | 5.9.3, 7.0.2 | no | `**/*` skips dot-folders (implementation detail; docs are silent) |

Tested workarounds: Jest `--testPathIgnorePatterns '/node_modules/' '<rootDir>/\.tasks/'
--modulePathIgnorePatterns '<rootDir>/\.tasks/'`; Vitest `--exclude '**/.tasks/**'`.

Consequence: worktrees live outside the repository by default (a per-user cache), so no
repository needs tool-config changes. See [Worktrees live in a persistent user cache](../2026-10-06-worktrees-live-in-a-persistent-user-cach.md).
