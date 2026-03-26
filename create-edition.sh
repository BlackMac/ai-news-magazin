#!/usr/bin/env bash
# Daily Die Inferenz edition via Claude Code (non-interactive)
# Intended to be run via system cron, e.g.:
#   0 6 * * * /home/lange-hegermann/projects/ai-news-agent/create-edition.sh >> /tmp/ai-news-edition.log 2>&1

set -euo pipefail

cd /home/lange-hegermann/projects/ai-news-agent

TODAY=$(date +%Y-%m-%d)

# Skip if today's edition already exists
if [ -f "editions/${TODAY}.html" ]; then
    echo "[$(date)] Edition ${TODAY} already exists, skipping."
    exit 0
fi

echo "[$(date)] Starting edition ${TODAY}..."

cat /home/lange-hegermann/projects/ai-news-agent/.claude/commands/new-edition.md | \
    /home/lange-hegermann/.local/bin/claude -p \
    --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,Agent,Skill"

echo "[$(date)] Edition ${TODAY} done."
