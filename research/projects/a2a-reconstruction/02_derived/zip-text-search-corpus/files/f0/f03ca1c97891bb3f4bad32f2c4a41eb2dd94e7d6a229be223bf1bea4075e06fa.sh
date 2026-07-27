#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${ZHIPU_API_KEY:-}" ]]; then
  printf '%s\n' 'ZHIPU_API_KEY is not set. Inject it with your existing secret-management method, then retry.' >&2
  exit 2
fi

if ! command -v claude >/dev/null 2>&1; then
  printf '%s\n' 'Claude Code is not available on PATH.' >&2
  exit 3
fi

# Keep all provider configuration scoped to this process tree.
unset ANTHROPIC_API_KEY
export ANTHROPIC_AUTH_TOKEN="${ZHIPU_API_KEY}"
export ANTHROPIC_BASE_URL="https://open.bigmodel.cn/api/anthropic"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="glm-4.7"
export ANTHROPIC_DEFAULT_SONNET_MODEL="${GLM52_CLAUDE_MODEL:-glm-5.2[1m]}"
export ANTHROPIC_DEFAULT_OPUS_MODEL="${GLM52_CLAUDE_MODEL:-glm-5.2[1m]}"
export CLAUDE_CODE_AUTO_COMPACT_WINDOW="1000000"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1"
export API_TIMEOUT_MS="${GLM52_API_TIMEOUT_MS:-3000000}"

exec claude --model opus "$@"

