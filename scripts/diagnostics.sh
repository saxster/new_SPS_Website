#!/bin/bash
# diagnostics.sh - Gather system diagnostics for escalation alerts
# Returns comprehensive system state as JSON

set -e

PROJECT_DIR="/root/new_SPS_Website"  # Adjust to your VPS path

# Get disk usage
get_disk() {
    local usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    local available=$(df -h / | awk 'NR==2 {print $4}')
    echo "{\"percent_used\":$usage,\"available\":\"$available\"}"
}

# Get memory usage
get_memory() {
    local total=$(free -m | awk 'NR==2 {print $2}')
    local used=$(free -m | awk 'NR==2 {print $3}')
    local percent=$(( used * 100 / total ))
    echo "{\"total_mb\":$total,\"used_mb\":$used,\"percent_used\":$percent}"
}

# Get load average
get_load() {
    local load1=$(cat /proc/loadavg | awk '{print $1}')
    local load5=$(cat /proc/loadavg | awk '{print $2}')
    local load15=$(cat /proc/loadavg | awk '{print $3}')
    echo "{\"1min\":$load1,\"5min\":$load5,\"15min\":$load15}"
}

# Get container logs (last N lines)
get_container_logs() {
    local container=$1
    local lines=${2:-30}
    local logs=$(docker logs --tail "$lines" "$container" 2>&1 | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|$//')
    echo "$logs"
}

# Get recent git commits
get_recent_commits() {
    cd "$PROJECT_DIR" 2>/dev/null || return
    local commits=$(git log --oneline -5 2>/dev/null | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|$//')
    echo "$commits"
}

# Get Docker stats
get_docker_stats() {
    docker stats --no-stream --format '{"name":"{{.Name}}","cpu":"{{.CPUPerc}}","memory":"{{.MemUsage}}"}' 2>/dev/null | head -5 | tr '\n' ',' | sed 's/,$//'
}

# Get uptime
get_uptime() {
    uptime -p 2>/dev/null || uptime | awk -F'up ' '{print $2}' | awk -F',' '{print $1}'
}

# Get recovery log (last 10 entries)
get_recovery_log() {
    local log_file="/var/log/sps-recovery.log"
    if [ -f "$log_file" ]; then
        tail -10 "$log_file" | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|$//'
    else
        echo "No recovery log found"
    fi
}

# Main output
echo "{"
echo "  \"timestamp\": \"$(date -Iseconds)\","
echo "  \"hostname\": \"$(hostname)\","
echo "  \"uptime\": \"$(get_uptime)\","
echo "  \"disk\": $(get_disk),"
echo "  \"memory\": $(get_memory),"
echo "  \"load\": $(get_load),"
echo "  \"docker_stats\": [$(get_docker_stats)],"
echo "  \"recent_commits\": \"$(get_recent_commits)\","
echo "  \"recovery_log\": \"$(get_recovery_log)\","
echo "  \"container_logs\": {"
echo "    \"sps_website\": \"$(get_container_logs 'sps-website' 20)\","
echo "    \"sps_brain\": \"$(get_container_logs 'sps-brain' 20)\""
echo "  }"
echo "}"
