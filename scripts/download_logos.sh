#!/usr/bin/env bash
# Refresh brand SVGs from Simple Icons (unpkg) into remotion/public/logos/
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)/remotion/public/logos"
mkdir -p "$DIR"

download() {
  local name="$1"
  local slug="$2"
  if curl -fsSL "https://unpkg.com/simple-icons@14.6.0/icons/${slug}.svg" -o "${DIR}/${name}.svg"; then
    echo "ok ${name}"
  elif curl -fsSL -A "Mozilla/5.0" "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/${slug}.svg" -o "${DIR}/${name}.svg"; then
    echo "ok ${name} (github)"
  else
    echo "fail ${name}" >&2
    return 1
  fi
}

download meta meta
download cursor cursor
download langchain langchain
download anthropic anthropic
download openai openai
download github github
download githubcopilot githubcopilot
download amazonaws amazonwebservices
download google google
download snowflake snowflake
download apachekafka apachekafka
download databricks databricks
download docker docker
download kubernetes kubernetes

echo "Done. linkedin.svg is bundled manually (trademark)."
