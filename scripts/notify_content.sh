#!/bin/bash
# notify_content.sh - Notify when new content is published
#
# Usage:
#   Basic: ./notify_content.sh "<title>" "<type>" "<url>" "<quality_score>" "<word_count>"
#   From file: ./notify_content.sh --from-file <path-to-markdown-file>
#   From git: ./notify_content.sh --from-git (detects changed content files)
#
# Environment:
#   N8N_CONTENT_WEBHOOK - n8n webhook URL (default: http://localhost:5678/webhook/content-published)
#   SITE_URL - Base site URL (default: https://sukhi.in)

set -e

# Configuration
N8N_WEBHOOK_URL="${N8N_CONTENT_WEBHOOK:-http://localhost:5678/webhook/content-published}"
SITE_URL="${SITE_URL:-https://sukhi.in}"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$(dirname "$(realpath "$0")")")/website}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Extract frontmatter value from markdown file
extract_frontmatter() {
    local file="$1"
    local key="$2"

    # Use awk to parse YAML frontmatter between --- markers
    awk -v key="$key" '
        /^---$/ { in_frontmatter = !in_frontmatter; next }
        in_frontmatter && $0 ~ "^" key ":" {
            # Remove the key and colon, trim whitespace and quotes
            sub("^" key ":[[:space:]]*", "")
            gsub(/^["'\'']|["'\'']$/, "")
            print
            exit
        }
    ' "$file"
}

# Extract tags array from frontmatter
extract_tags() {
    local file="$1"

    # Parse YAML array format: tags: [tag1, tag2] or tags:\n  - tag1\n  - tag2
    awk '
        /^---$/ { in_frontmatter = !in_frontmatter; next }
        in_frontmatter && /^tags:/ {
            if ($0 ~ /\[/) {
                # Inline array format: tags: [tag1, tag2]
                sub(/^tags:[[:space:]]*\[/, "")
                sub(/\].*$/, "")
                gsub(/[[:space:]]*,[[:space:]]*/, ",")
                gsub(/["'\'']/, "")
                print
                exit
            }
            # Start of block array
            in_tags = 1
            next
        }
        in_frontmatter && in_tags {
            if (/^[[:space:]]*-[[:space:]]/) {
                sub(/^[[:space:]]*-[[:space:]]*/, "")
                gsub(/["'\'']/, "")
                tags = (tags == "" ? $0 : tags "," $0)
            } else if (/^[[:alpha:]]/) {
                # New key, end of tags
                print tags
                exit
            }
        }
        END { if (in_tags) print tags }
    ' "$file"
}

# Determine content type from file path
get_content_type() {
    local file="$1"

    if [[ "$file" == *"/intelligence/"* ]]; then
        echo "intelligence"
    elif [[ "$file" == *"/news/"* ]]; then
        echo "news"
    elif [[ "$file" == *"/blog/"* ]]; then
        echo "blog"
    else
        echo "content"
    fi
}

# Get slug from filename
get_slug() {
    local file="$1"
    basename "$file" .md
}

# Count words in markdown content (excluding frontmatter)
count_words() {
    local file="$1"

    awk '
        /^---$/ { in_frontmatter = !in_frontmatter; next }
        !in_frontmatter { content = content " " $0 }
        END {
            gsub(/[^[:alnum:][:space:]]/, "", content)
            n = split(content, words)
            print n
        }
    ' "$file"
}

# Build URL from content type and slug
build_url() {
    local type="$1"
    local slug="$2"

    case "$type" in
        intelligence)
            echo "${SITE_URL}/intelligence/${slug}"
            ;;
        news)
            echo "${SITE_URL}/news/${slug}"
            ;;
        blog)
            echo "${SITE_URL}/blog/${slug}"
            ;;
        *)
            echo "${SITE_URL}/${slug}"
            ;;
    esac
}

# Send notification to n8n webhook
send_notification() {
    local title="$1"
    local type="$2"
    local url="$3"
    local quality_score="$4"
    local word_count="$5"
    local severity="$6"
    local sector="$7"
    local tags="$8"
    local slug="$9"
    local consensus_score="${10}"
    local files="${11}"

    # Build JSON payload
    local payload=$(cat <<EOF
{
    "event": "content_published",
    "timestamp": "$(date -Iseconds)",
    "files": "$files",
    "content": {
        "title": "$title",
        "type": "$type",
        "url": "$url",
        "slug": "$slug",
        "quality_score": ${quality_score:-null},
        "word_count": ${word_count:-null},
        "severity": "$severity",
        "sector": "$sector",
        "tags": [$(echo "$tags" | sed 's/,/","/g' | sed 's/^/"/' | sed 's/$/"/' | sed 's/^""$//')],
        "consensus_score": ${consensus_score:-null}
    }
}
EOF
)

    log_info "Sending notification for: $title"
    log_info "  Type: $type"
    log_info "  Severity: $severity"
    log_info "  Sector: $sector"
    log_info "  URL: $url"

    # Send to n8n
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$N8N_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>&1)

    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "201" ]]; then
        log_info "Notification sent successfully (HTTP $http_code)"
    else
        log_warn "Notification may have failed (HTTP $http_code)"
        log_warn "Response: $body"
    fi
}

# Process a single markdown file
process_file() {
    local file="$1"

    if [[ ! -f "$file" ]]; then
        log_error "File not found: $file"
        return 1
    fi

    log_info "Processing: $file"

    # Extract metadata from frontmatter
    local title=$(extract_frontmatter "$file" "title")
    local severity=$(extract_frontmatter "$file" "severity")
    local sector=$(extract_frontmatter "$file" "sector")
    local tags=$(extract_tags "$file")
    local consensus_score=$(extract_frontmatter "$file" "consensus_score")

    # Derive other values
    local type=$(get_content_type "$file")
    local slug=$(get_slug "$file")
    local url=$(build_url "$type" "$slug")
    local word_count=$(count_words "$file")

    # Defaults
    title="${title:-Untitled}"
    severity="${severity:-Medium}"
    sector="${sector:-General}"

    send_notification "$title" "$type" "$url" "" "$word_count" "$severity" "$sector" "$tags" "$slug" "$consensus_score" "$file"
}

# Process git changes to detect new/modified content
process_git_changes() {
    log_info "Detecting content changes from git..."

    cd "$PROJECT_DIR" 2>/dev/null || {
        log_error "Could not change to project directory: $PROJECT_DIR"
        return 1
    }

    # Get changed content files from the last commit
    local changed_files
    changed_files=$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null | grep "src/content/" | grep ".md$" || true)

    if [[ -z "$changed_files" ]]; then
        log_info "No content files changed in the last commit"
        return 0
    fi

    log_info "Found changed content files:"
    echo "$changed_files" | while read -r file; do
        log_info "  - $file"
    done

    # Process each changed file
    echo "$changed_files" | while read -r file; do
        if [[ -n "$file" && -f "$file" ]]; then
            process_file "$file"
        fi
    done
}

# Main entry point
main() {
    case "${1:-}" in
        --from-file)
            if [[ -z "${2:-}" ]]; then
                log_error "Usage: $0 --from-file <path-to-markdown-file>"
                exit 1
            fi
            process_file "$2"
            ;;
        --from-git)
            process_git_changes
            ;;
        --help|-h)
            echo "Usage:"
            echo "  $0 \"<title>\" \"<type>\" \"<url>\" [quality_score] [word_count]"
            echo "  $0 --from-file <path-to-markdown-file>"
            echo "  $0 --from-git"
            echo ""
            echo "Environment variables:"
            echo "  N8N_CONTENT_WEBHOOK - Webhook URL (default: http://localhost:5678/webhook/content-published)"
            echo "  SITE_URL - Site base URL (default: https://sukhi.in)"
            echo "  PROJECT_DIR - Project directory (auto-detected)"
            ;;
        *)
            # Legacy mode: positional arguments
            local title="${1:-New Article}"
            local type="${2:-blog}"
            local url="${3:-$SITE_URL}"
            local quality_score="${4:-}"
            local word_count="${5:-}"

            send_notification "$title" "$type" "$url" "$quality_score" "$word_count" "Medium" "General" "" "" "" ""
            ;;
    esac
}

main "$@"
