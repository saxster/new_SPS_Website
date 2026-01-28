#!/bin/bash
# health_check.sh - Check health status of all SPS services
# Returns JSON array with container statuses

set -e

check_container() {
    local name=$1
    local status=$(docker inspect --format='{{.State.Status}}' "$name" 2>/dev/null || echo "missing")
    local health=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "none")
    local uptime=$(docker inspect --format='{{.State.StartedAt}}' "$name" 2>/dev/null || echo "unknown")
    local restarts=$(docker inspect --format='{{.RestartCount}}' "$name" 2>/dev/null || echo "0")

    echo "{\"name\":\"$name\",\"status\":\"$status\",\"health\":\"$health\",\"started\":\"$uptime\",\"restarts\":$restarts}"
}

# Check if site responds
check_http() {
    local url=$1
    local timeout=${2:-10}
    local start=$(date +%s%N)
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$timeout" "$url" 2>/dev/null || echo "000")
    local end=$(date +%s%N)
    local duration=$(( (end - start) / 1000000 ))

    echo "{\"url\":\"$url\",\"status_code\":$http_code,\"response_time_ms\":$duration}"
}

echo "{"
echo "  \"timestamp\": \"$(date -Iseconds)\","
echo "  \"containers\": ["
echo "    $(check_container 'sps-website'),"
echo "    $(check_container 'sps-brain'),"
echo "    $(check_container 'sps-chroma'),"
echo "    $(check_container 'cloudflared'),"
echo "    $(check_container 'n8n')"
echo "  ],"
echo "  \"endpoints\": ["
echo "    $(check_http 'http://localhost:4321' 15),"
echo "    $(check_http 'http://localhost:8000/health' 10)"
echo "  ]"
echo "}"
