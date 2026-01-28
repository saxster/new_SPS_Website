#!/bin/bash
# notify_content.sh - Notify when new content is published
# Usage: ./notify_content.sh "<title>" "<type>" "<url>" "<quality_score>"

TITLE=${1:-"New Article"}
TYPE=${2:-"blog"}
URL=${3:-"https://sps-security.com"}
QUALITY_SCORE=${4:-"0"}
WORD_COUNT=${5:-"0"}

# n8n webhook URL (configure this after setting up n8n)
N8N_WEBHOOK_URL="${N8N_CONTENT_WEBHOOK:-http://localhost:5678/webhook/content-published}"

# Send notification to n8n
curl -s -X POST "$N8N_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"event\": \"content_published\",
    \"timestamp\": \"$(date -Iseconds)\",
    \"content\": {
      \"title\": \"$TITLE\",
      \"type\": \"$TYPE\",
      \"url\": \"$URL\",
      \"quality_score\": $QUALITY_SCORE,
      \"word_count\": $WORD_COUNT
    }
  }"

echo "Notification sent for: $TITLE"
