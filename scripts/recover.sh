#!/bin/bash
# recover.sh - Auto-recovery script for SPS services
# Usage: ./recover.sh <service_name> <level>
# Levels: 1 = restart container, 2 = full stack restart, 3 = rebuild and restart

set -e

SERVICE=${1:-"sps-website"}
LEVEL=${2:-1}
PROJECT_DIR="/root/new_SPS_Website"  # Adjust to your VPS path
COMPOSE_FILE="docker-compose.prod.yml"
LOG_FILE="/var/log/sps-recovery.log"
LOCK_FILE="/tmp/sps-recovery.lock"
MAX_RESTARTS_PER_HOUR=3

# Logging function
log() {
    local level=$1
    local message=$2
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" | tee -a "$LOG_FILE"
}

# Check if recovery is locked (during deployment or cooldown)
check_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local lock_age=$(( $(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0) ))
        if [ $lock_age -lt 600 ]; then  # 10 minute lock
            log "WARN" "Recovery locked. Lock age: ${lock_age}s"
            echo '{"success":false,"reason":"recovery_locked","lock_age":'$lock_age'}'
            exit 1
        else
            rm -f "$LOCK_FILE"
        fi
    fi
}

# Rate limiting - max 3 restarts per hour
check_rate_limit() {
    local count=$(grep -c "$(date '+%Y-%m-%d %H')" "$LOG_FILE" 2>/dev/null | grep -c "RECOVERY" || echo 0)
    if [ "$count" -ge "$MAX_RESTARTS_PER_HOUR" ]; then
        log "WARN" "Rate limit exceeded: $count restarts this hour"
        echo '{"success":false,"reason":"rate_limit_exceeded","restarts_this_hour":'$count'}'
        exit 1
    fi
}

# Create lock
create_lock() {
    touch "$LOCK_FILE"
    log "INFO" "Recovery lock created"
}

# Remove lock
remove_lock() {
    rm -f "$LOCK_FILE"
    log "INFO" "Recovery lock removed"
}

# Level 1: Restart single container
level1_restart() {
    log "RECOVERY" "Level 1: Restarting container $SERVICE"
    docker restart "$SERVICE"
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Container $SERVICE restarted successfully"
        echo '{"success":true,"level":1,"action":"container_restart","service":"'$SERVICE'","wait_seconds":180}'
    else
        log "ERROR" "Failed to restart container $SERVICE"
        echo '{"success":false,"level":1,"action":"container_restart","service":"'$SERVICE'","error_code":'$exit_code'}'
    fi
}

# Level 2: Full stack restart
level2_stack_restart() {
    log "RECOVERY" "Level 2: Full stack restart"
    cd "$PROJECT_DIR"

    docker-compose -f "$COMPOSE_FILE" down
    sleep 5
    docker-compose -f "$COMPOSE_FILE" up -d
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Full stack restarted successfully"
        echo '{"success":true,"level":2,"action":"stack_restart","wait_seconds":300}'
    else
        log "ERROR" "Failed to restart stack"
        echo '{"success":false,"level":2,"action":"stack_restart","error_code":'$exit_code'}'
    fi
}

# Level 3: Rebuild and restart (for content updates or code changes)
level3_rebuild() {
    log "RECOVERY" "Level 3: Rebuild and restart $SERVICE"
    cd "$PROJECT_DIR"

    # Pull latest changes
    git pull origin main

    # Rebuild specific service
    docker-compose -f "$COMPOSE_FILE" up -d --build "$SERVICE"
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Service $SERVICE rebuilt and restarted"
        echo '{"success":true,"level":3,"action":"rebuild","service":"'$SERVICE'"}'
    else
        log "ERROR" "Failed to rebuild $SERVICE"
        echo '{"success":false,"level":3,"action":"rebuild","service":"'$SERVICE'","error_code":'$exit_code'}'
    fi
}

# Main execution
main() {
    log "INFO" "Recovery initiated: service=$SERVICE level=$LEVEL"

    check_lock
    check_rate_limit
    create_lock

    case $LEVEL in
        1)
            level1_restart
            ;;
        2)
            level2_stack_restart
            ;;
        3)
            level3_rebuild
            ;;
        *)
            log "ERROR" "Invalid level: $LEVEL"
            echo '{"success":false,"reason":"invalid_level"}'
            remove_lock
            exit 1
            ;;
    esac

    # Keep lock for cooldown period (will auto-expire)
    log "INFO" "Recovery complete. Lock will expire in 10 minutes."
}

main
