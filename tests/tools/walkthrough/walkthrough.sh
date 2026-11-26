#!/bin/bash
# First-run walkthrough: starts the skill from the current branch in a throwaway HOME.
# Usage: see `walkthrough.sh --help` and README.md next to this file.
set -euo pipefail

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# Every sandbox lives here, and nowhere else. A short path: Unix socket paths are limited.
WALKTHROUGH_ROOT="$(cd /tmp && pwd -P)/sae-walkthrough"
SCENARIOS="fresh upgrade"

usage() {
  cat <<EOF
Usage:
  $(basename "$0") start fresh|upgrade [--codex] [--ref <git ref>] [--no-orca] [--orca-worktree <selector>]
  $(basename "$0") clean [fresh|upgrade]

start   Build the sandbox $WALKTHROUGH_ROOT/<scenario>, install the skill from <ref>
        (default HEAD: committed files only), check the isolation, and open the session in a
        new Orca terminal (or print the command to run).
          fresh    no sae config: the skill starts setup.
          upgrade  a config from before the easy column (upgrade-config.json).
          --codex  the session runs in Codex (fresh 'codex login'); default: Claude.
clean   Stop the sandbox's viewer, log the sandbox out, close its Orca terminal and delete
        the sandbox (one scenario, or all of $WALKTHROUGH_ROOT).
EOF
}

die() { echo "walkthrough: $*" >&2; exit 1; }
note() { echo "walkthrough: $*"; }

# The only paths this tool creates or deletes: $WALKTHROUGH_ROOT and one level below it.
guard_sandbox() {
  local path="$1"
  [ -n "$path" ] || die "empty sandbox path"
  [ ! -L "$WALKTHROUGH_ROOT" ] || die "$WALKTHROUGH_ROOT is a symlink; refusing"
  case "$path" in
    "$WALKTHROUGH_ROOT"/*/*|*..*|*//*) die "refusing sandbox path $path" ;;
    "$WALKTHROUGH_ROOT"/?*) ;;
    *) die "refusing sandbox path $path: not under $WALKTHROUGH_ROOT" ;;
  esac
  if [ -e "$path" ]; then
    [ ! -L "$path" ] || die "$path is a symlink; refusing"
    [ "$(cd "$path" && pwd -P)" = "$path" ] || die "$path resolves elsewhere; refusing"
  fi
}

scenario_dir() {
  case "${1:-}" in
    fresh|upgrade) echo "$WALKTHROUGH_ROOT/$1" ;;
    *) die "unknown scenario '${1:-}' (fresh or upgrade)" ;;
  esac
}

# The installed sae of a sandbox: Claude installs into CLAUDE_CONFIG_DIR, Codex into ~/.agents.
sandbox_sae() {
  local sb="$1" candidate
  for candidate in "$sb/home/.claude/skills/shape-and-execute/scripts/sae.py" \
                   "$sb/home/.agents/skills/shape-and-execute/scripts/sae.py"; do
    [ -f "$candidate" ] && { echo "$candidate"; return 0; }
  done
  return 1
}

clean_one() {
  local sb="$1" sae handle
  guard_sandbox "$sb"
  [ -d "$sb" ] || return 0
  [ -x "$sb/env.sh" ] || die "$sb has no env.sh: not a walkthrough sandbox; delete it by hand if you are sure"
  if [ -f "$sb/orca-terminal" ] && command -v orca >/dev/null 2>&1; then
    handle="$(cat "$sb/orca-terminal")"
    orca terminal close --terminal "$handle" --tab >/dev/null 2>&1 \
      && note "closed Orca terminal $handle" || note "Orca terminal $handle already closed"
  fi
  if sae="$(sandbox_sae "$sb")"; then
    (cd "$sb" && "$sb/env.sh" python3 "$sae" view --stop >/dev/null 2>&1) || true
  fi
  if [ -e "$sb/bin/claude" ] && [ -d "$sb/home/.claude" ]; then
    # Removes the login of this sandbox only: its Keychain entry is keyed by CLAUDE_CONFIG_DIR
    (cd "$sb" && "$sb/env.sh" claude auth logout >/dev/null 2>&1) || true
  fi
  if [ -e "$sb/bin/codex" ] && [ -f "$sb/home/.codex/auth.json" ]; then
    (cd "$sb" && "$sb/env.sh" codex logout >/dev/null 2>&1) || true
  fi
  if [ -f "$sb/used-login" ]; then
    note "Claude /login was used in $sb. 'claude auth logout' ran; to confirm no Keychain entry is left:"
    note "  security find-generic-password -s '$(cat "$sb/used-login")' >/dev/null 2>&1 && echo present || echo gone"
  fi
  guard_sandbox "$sb"
  rm -rf -- "$sb"
  note "deleted $sb"
}

cmd_clean() {
  local scenario
  if [ $# -gt 0 ]; then
    clean_one "$(scenario_dir "$1")"
  else
    for scenario in $SCENARIOS; do clean_one "$WALKTHROUGH_ROOT/$scenario"; done
  fi
  if [ -d "$WALKTHROUGH_ROOT" ] && [ ! -L "$WALKTHROUGH_ROOT" ]; then
    rmdir "$WALKTHROUGH_ROOT" 2>/dev/null \
      || note "$WALKTHROUGH_ROOT still holds: $(ls -A "$WALKTHROUGH_ROOT" | tr '\n' ' ')"
  fi
  [ -e "$WALKTHROUGH_ROOT" ] || note "nothing left under $WALKTHROUGH_ROOT"
}

link_tool() {
  local sb="$1" name="$2" path
  path="$(type -P "$name")" || die "'$name' is not on PATH"
  ln -s "$path" "$sb/bin/$name"
}

write_env_script() {
  # Runs "$@" with nothing of the caller's environment but the terminal basics.
  cat > "$1/env.sh" <<'EOF'
#!/bin/bash
SB="$(cd "$(dirname "$0")" && pwd -P)"
exec env -i HOME="$SB/home" CLAUDE_CONFIG_DIR="$SB/home/.claude" CODEX_HOME="$SB/home/.codex" \
  XDG_CONFIG_HOME="$SB/home/.config" XDG_CACHE_HOME="$SB/home/.cache" SAE_STATE_DIR="$SB/state" \
  TMPDIR="$SB/tmp" PATH="$SB/bin:/usr/bin:/bin" SHELL=/bin/zsh \
  TERM="${TERM:-xterm-256color}" COLORTERM="${COLORTERM:-}" LANG="${LANG:-en_US.UTF-8}" \
  USER="${USER:-walkthrough}" LOGNAME="${LOGNAME:-${USER:-walkthrough}}" \
  DISABLE_AUTOUPDATER=1 ENABLE_CLAUDEAI_MCP_SERVERS=false "$@"
EOF
  chmod +x "$1/env.sh"
}

write_launch_script() {
  local sb="$1" harness="$2"
  if [ "$harness" = codex ]; then
    cat > "$sb/launch.sh" <<'EOF'
#!/bin/bash
# Opens the Codex session of the walkthrough sandbox.
SB="$(cd "$(dirname "$0")" && pwd -P)"
cd "$SB/repo" || exit 1
if ! "$SB/env.sh" codex login status >/dev/null 2>&1; then
  echo "Log in to Codex inside the sandbox (its login stays in $SB/home/.codex)."
  "$SB/env.sh" codex login || { echo "Codex login failed; run 'bash $SB/launch.sh' again."; exit 1; }
fi
echo "Type: \$shape-and-execute <a rough note of what you want>"
exec "$SB/env.sh" codex --no-daemon -C "$SB/repo"
EOF
  else
    cat > "$sb/launch.sh" <<'EOF'
#!/bin/bash
# Opens the Claude session of the walkthrough sandbox.
SB="$(cd "$(dirname "$0")" && pwd -P)"
cd "$SB/repo" || exit 1
logged_in() {
  "$SB/env.sh" claude auth status --json 2>/dev/null \
    | "$SB/env.sh" python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin).get("loggedIn") else 1)' 2>/dev/null
}
token_session() {
  echo "Fallback: in a normal terminal run 'claude setup-token', then paste the token here (hidden)."
  echo "The token lasts a year and 'clean' does not revoke it. Enter alone stops."
  read -rs tok; echo
  [ -n "$tok" ] || exit 1
  echo "Type: /shape-and-execute <a rough note of what you want>"
  exec "$SB/env.sh" env CLAUDE_CODE_OAUTH_TOKEN="$tok" claude
}
if logged_in; then
  echo "Type: /shape-and-execute <a rough note of what you want>"
  exec "$SB/env.sh" claude
fi
printf 'Claude login: Enter = /login inside the session (default), t = paste a setup-token token: '
read -r choice
case "$choice" in t|T) token_session ;; esac
# The Keychain entry a /login creates is named after the config folder; clean prints it
printf 'Claude Code-credentials-%s\n' "$(printf '%s' "$SB/home/.claude" | shasum -a 256 | cut -c1-8)" > "$SB/used-login"
echo "Log in with /login in the session. Then type: /shape-and-execute <a rough note of what you want>"
"$SB/env.sh" claude
if ! logged_in; then
  echo
  echo "/login did not keep a login under the relocated HOME (the Keychain or the file fallback failed)."
  token_session
fi
EOF
  fi
  chmod +x "$sb/launch.sh"
}

# Fails when a check command prints a path of the owner's home: the sandbox must not see it.
check_no_owner_paths() {
  local label="$1" output="$2"
  if printf '%s' "$output" | grep -qF "$HOME/"; then
    printf '%s\n' "$output" | grep -F "$HOME/" >&2
    die "$label shows a path under your HOME: the sandbox leaks; run 'clean'"
  fi
}

cmd_start() {
  local scenario="" harness=claude ref=HEAD use_orca=1 orca_worktree=active
  while [ $# -gt 0 ]; do
    case "$1" in
      fresh|upgrade) scenario="$1" ;;
      --codex) harness=codex ;;
      --ref) ref="${2:?--ref needs a git ref}"; shift ;;
      --no-orca) use_orca=0 ;;
      --orca-worktree) orca_worktree="${2:?--orca-worktree needs a selector}"; shift ;;
      *) usage >&2; exit 2 ;;
    esac
    shift
  done
  [ -n "$scenario" ] || { usage >&2; exit 2; }
  local sb repo apm sae output
  sb="$(scenario_dir "$scenario")"
  guard_sandbox "$sb"
  repo="$(git -C "$TOOL_DIR" rev-parse --show-toplevel)"
  apm="$(type -P apm)" || die "APM is not installed (README, Install); the walkthrough installs the skill with it"
  for tool in git python3 "$harness"; do type -P "$tool" >/dev/null || die "'$tool' is not on PATH"; done
  git -C "$repo" rev-parse --verify --quiet "$ref^{commit}" >/dev/null || die "unknown git ref '$ref'"
  if [ "$ref" = HEAD ] && [ -n "$(git -C "$repo" status --porcelain -- skills/shape-and-execute)" ]; then
    note "uncommitted changes in skills/shape-and-execute are NOT installed (git archive exports commits)"
  fi

  if [ -d "$sb" ]; then note "replacing the existing $scenario sandbox"; clean_one "$sb"; fi
  if [ ! -d "$WALKTHROUGH_ROOT" ]; then mkdir -m 700 "$WALKTHROUGH_ROOT"; fi
  [ ! -L "$WALKTHROUGH_ROOT" ] || die "$WALKTHROUGH_ROOT is a symlink; refusing"
  mkdir -m 700 "$sb"
  mkdir -p "$sb"/{bin,home,repo,src,state,tmp} "$sb/home/Library/Caches/shape-and-execute/worktrees"
  write_env_script "$sb"
  link_tool "$sb" git
  link_tool "$sb" python3
  link_tool "$sb" "$harness"
  [ "$harness" = codex ] && link_tool "$sb" node   # the codex CLI is a node script

  note "exporting skills/shape-and-execute at $ref ($(git -C "$repo" rev-parse --short "$ref"))"
  git -C "$repo" archive "$ref" skills/shape-and-execute | tar -x -C "$sb/src"
  note "installing like a new user: apm install -g <export> --target $harness"
  (cd "$sb" && "$sb/env.sh" "$apm" install -g "$sb/src/skills/shape-and-execute" --target "$harness") \
    > "$sb/apm-install.log" 2>&1 || { cat "$sb/apm-install.log" >&2; die "apm install failed"; }
  sae="$(sandbox_sae "$sb")" || die "apm install put no skill into the sandbox (see $sb/apm-install.log)"
  diff -rq "$sb/src/skills/shape-and-execute" "$(dirname "$(dirname "$sae")")" >/dev/null \
    || die "the installed skill differs from the export"

  (cd "$sb/repo" && "$sb/env.sh" git init -q -b main . \
    && "$sb/env.sh" git config user.name "SaE Walkthrough" \
    && "$sb/env.sh" git config user.email "walkthrough@example.invalid" \
    && echo "# demo" > README.md && "$sb/env.sh" git add README.md \
    && "$sb/env.sh" git commit -qm "Initial commit")

  if [ "$scenario" = upgrade ]; then
    mkdir -p "$sb/home/.config/shape-and-execute"
    "$sb/env.sh" python3 -I - "$TOOL_DIR/upgrade-config.json" "$sb" <<'EOF'
import json, sys
config = json.load(open(sys.argv[1]))
config["worktrees"]["root"] = sys.argv[2] + "/home/Library/Caches/shape-and-execute/worktrees"
with open(sys.argv[2] + "/home/.config/shape-and-execute/config.json", "w") as out:
    json.dump(config, out, indent=2)
EOF
    chmod 600 "$sb/home/.config/shape-and-execute/config.json"
  fi

  note "isolation check"
  if [ "$harness" = claude ]; then
    output="$(cd "$sb/repo" && "$sb/env.sh" claude auth status --text 2>&1 || true)"
  else
    output="$(cd "$sb/repo" && "$sb/env.sh" codex login status 2>&1 || true)"
  fi
  echo "  $harness login: $(printf '%s' "$output" | head -1)"
  printf '%s' "$output" | grep -qi "not logged in" || die "the sandbox $harness is logged in before the owner logged in"
  output="$(cd "$sb/repo" && "$sb/env.sh" env SAE_HARNESS="$harness" python3 "$sae" doctor 2>&1 || true)"
  printf '%s\n' "$output" | sed 's/^/  /'
  check_no_owner_paths "sae doctor" "$output"
  check_no_owner_paths "the installed apm manifest" "$(cat "$sb/home/.apm/apm.yml" 2>/dev/null || true)"

  write_launch_script "$sb" "$harness"
  local launch="bash '$sb/launch.sh'"
  if [ "$use_orca" = 1 ] && command -v orca >/dev/null 2>&1; then
    output="$(orca terminal create --worktree "$orca_worktree" --title "SaE walkthrough: $scenario ($harness)" \
      --command "$launch" --focus --json 2>&1)" && {
      # The first "handle" anywhere in the reply: clean closes only this terminal
      printf '%s' "$output" | python3 -I -c 'import json, sys
def find(node):
    if isinstance(node, dict):
        if isinstance(node.get("handle"), str):
            return node["handle"]
        node = list(node.values())
    if isinstance(node, list):
        for item in node:
            found = find(item)
            if found:
                return found
    return None
print(find(json.load(sys.stdin)) or "")' > "$sb/orca-terminal" 2>/dev/null || true
      [ -s "$sb/orca-terminal" ] || rm -f "$sb/orca-terminal"
      note "opened the session in a new Orca terminal"
      note "afterwards: $0 clean $scenario"
      return 0
    }
    note "Orca could not open a terminal: $(printf '%s' "$output" | head -1)"
  fi
  note "run this in a terminal to open the session:"
  echo "  $launch"
  note "afterwards: $0 clean $scenario"
}

case "${1:-}" in
  start) shift; cmd_start "$@" ;;
  clean) shift; cmd_clean "$@" ;;
  -h|--help|help) usage ;;
  *) usage >&2; exit 2 ;;
esac
