#!/bin/bash
# usage: make.sh <dir> <extra-toml-file>
set -eu
probe_dir="$1"; extra="$2"
mkdir -p "$probe_dir"; probe_dir="$(cd "$probe_dir" && pwd -P)"
mkdir "$probe_dir/home" "$probe_dir/worktrees" "$probe_dir/ipc"
main="$probe_dir/main"; job="$probe_dir/worktrees/job"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
git init -q --ref-format=files -b main "$main"
git -C "$main" -c user.name=Probe -c user.email=probe@example.invalid commit --allow-empty -qm base
git -C "$main" worktree add -qb sae-job "$job"
printf 'merge source\n' > "$main/merge-source.txt"
git -C "$main" add merge-source.txt
git -C "$main" -c user.name=Probe -c user.email=probe@example.invalid commit -qm source
common="$(git -C "$job" rev-parse --path-format=absolute --git-common-dir)"
gitdir="$(git -C "$job" rev-parse --absolute-git-dir)"
cat > "$probe_dir/home/sae-probe.config.toml" <<T
default_permissions = "shape-and-execute"

[permissions.shape-and-execute]
extends = ":workspace"

[permissions.shape-and-execute.filesystem]
"$probe_dir" = "read"
"$probe_dir/worktrees" = "write"
"$probe_dir/ipc" = "write"
"$common/objects" = "write"
"$common/refs" = "write"
"$common/logs" = "write"

[permissions.shape-and-execute.filesystem.":workspace_roots"]
".git" = "read"

[permissions.shape-and-execute.filesystem."$gitdir"]
"." = "write"
"config.worktree" = "read"
"commondir" = "read"
"gitdir" = "read"
T
sed "s#@IPC@#$probe_dir/ipc#g" "$extra" >> "$probe_dir/home/sae-probe.config.toml"
echo "$probe_dir"
