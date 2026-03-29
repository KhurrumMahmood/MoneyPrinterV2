#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
PRIMARY_REPO="/Users/khurrummahmood/Projects/MoneyPrinterV2"
RUN_LOG="$PROJECT_ROOT/.codex-runner.log"

typeset -a ALLOWED_ROOTS
ALLOWED_ROOTS=("$PROJECT_ROOT")
[[ -d "$PRIMARY_REPO" ]] && ALLOWED_ROOTS+=("$PRIMARY_REPO")

typeset -a ALLOWED_COMMANDS
ALLOWED_COMMANDS=(
  bash
  cat
  chmod
  claude
  codex
  cp
  curl
  ffmpeg
  ffprobe
  find
  git
  kill
  ls
  mkdir
  mv
  node
  npm
  npx
  python
  python3
  rg
  sed
  sh
  stat
  touch
  zsh
)

typeset -a BLOCKED_COMMANDS
BLOCKED_COMMANDS=(
  dd
  diskutil
  launchctl
  osascript
  rm
  rsync
  scp
  ssh
  sudo
)

function fail() {
  print -u2 -- "codex-runner: $1"
  exit 1
}

function usage() {
  cat <<'EOF'
Usage:
  codex-runner.sh --cwd <path> [--env KEY=VALUE ...] -- <command> [args...]

Examples:
  codex-runner.sh --cwd /private/tmp/MoneyPrinterV2-citevideo -- git status --short
  codex-runner.sh --cwd /private/tmp/MoneyPrinterV2-citevideo --env CITEVIDEO_ROUNDTABLE_ROUNDS=2 -- python3 -m unittest tests.test_topic_package
EOF
}

function in_allowed_root() {
  local candidate="$1"
  local root
  for root in "${ALLOWED_ROOTS[@]}"; do
    if [[ "$candidate" == "$root" || "$candidate" == "$root"/* ]]; then
      return 0
    fi
  done
  return 1
}

function command_allowed() {
  local head="$1"
  local allowed
  for allowed in "${ALLOWED_COMMANDS[@]}"; do
    if [[ "$head" == "$allowed" ]]; then
      return 0
    fi
  done
  return 1
}

function command_blocked() {
  local head="$1"
  local blocked
  for blocked in "${BLOCKED_COMMANDS[@]}"; do
    if [[ "$head" == "$blocked" ]]; then
      return 0
    fi
  done
  return 1
}

function validate_git_args() {
  shift
  local subcommand="${1:-}"
  local second="${2:-}"
  if [[ "$subcommand" == "reset" && "$second" == "--hard" ]]; then
    fail "git reset --hard is blocked"
  fi
  if [[ "$subcommand" == "clean" ]]; then
    fail "git clean is blocked"
  fi
}

function validate_shell_args() {
  local head="$1"
  local first_arg="${2:-}"
  case "$head" in
    bash|sh|zsh)
      [[ "$first_arg" == "-c" || "$first_arg" == "-lc" || "$first_arg" == "-ic" ]] && \
        fail "inline shell execution is blocked; pass a script path instead"
      ;;
    python|python3)
      [[ "$first_arg" == "-c" || "$first_arg" == "-" ]] && \
        fail "inline python execution is blocked; use a file or module"
      ;;
    node)
      [[ "$first_arg" == "-e" || "$first_arg" == "-p" ]] && \
        fail "inline node execution is blocked; use a file"
      ;;
  esac
}

function validate_curl_args() {
  shift
  local arg
  for arg in "$@"; do
    if [[ "$arg" == http://* || "$arg" == https://* ]]; then
      if [[ "$arg" != http://127.0.0.1* && "$arg" != http://localhost* && "$arg" != https://127.0.0.1* && "$arg" != https://localhost* ]]; then
        fail "curl is restricted to localhost URLs"
      fi
    fi
  done
}

[[ $# -eq 0 ]] && { usage; exit 1; }

typeset -a ENV_VARS
ENV_VARS=()
RUN_CWD=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cwd)
      [[ $# -lt 2 ]] && fail "--cwd requires a path"
      RUN_CWD="$2"
      shift 2
      ;;
    --env)
      [[ $# -lt 2 ]] && fail "--env requires KEY=VALUE"
      [[ ! "$2" =~ '^[A-Za-z_][A-Za-z0-9_]*=.*$' ]] && fail "invalid env var: $2"
      ENV_VARS+=("$2")
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unexpected argument: $1"
      ;;
  esac
done

[[ -z "$RUN_CWD" ]] && fail "missing --cwd"
[[ $# -eq 0 ]] && fail "missing command after --"

if ! RESOLVED_CWD="$(cd "$RUN_CWD" 2>/dev/null && pwd -P)"; then
  fail "cannot resolve cwd: $RUN_CWD"
fi

in_allowed_root "$RESOLVED_CWD" || fail "cwd outside allowed roots: $RESOLVED_CWD"

COMMAND_HEAD="$1"
shift
COMMAND_NAME="$(basename "$COMMAND_HEAD")"

command_blocked "$COMMAND_NAME" && fail "blocked command: $COMMAND_NAME"
command_allowed "$COMMAND_NAME" || fail "command not on allowlist: $COMMAND_NAME"

validate_shell_args "$COMMAND_NAME" "${1:-}"

case "$COMMAND_NAME" in
  git) validate_git_args "$COMMAND_NAME" "$@" ;;
  curl) validate_curl_args "$COMMAND_NAME" "$@" ;;
esac

mkdir -p "$(dirname "$RUN_LOG")"
{
  printf '%s\t%s\t%s' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$RESOLVED_CWD" "$COMMAND_NAME"
  local_arg=""
  for local_arg in "$@"; do
    printf ' %q' "$local_arg"
  done
  printf '\n'
} >>"$RUN_LOG"

cd "$RESOLVED_CWD"
if [[ "${#ENV_VARS[@]}" -gt 0 ]]; then
  env "${ENV_VARS[@]}" "$COMMAND_HEAD" "$@"
else
  "$COMMAND_HEAD" "$@"
fi
