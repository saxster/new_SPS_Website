# SPS Self-Healing & Notification System Setup Guide

## Overview

This system provides:
1. **Automatic site recovery** - Detects outages and attempts self-healing
2. **Content notifications** - Alerts when new articles are published
3. **Escalation** - Notifies you when auto-recovery fails

## Architecture

```
Health Check (every 5 min)
         │
         ▼
    Site Down?
         │
    ├── No → Log success
    │
    └── Yes → Wait 30s → Retry
                   │
              Still down?
                   │
              └── Yes → Level 1: Restart container
                             │
                        Wait 3 minutes
                             │
                        Still down?
                             │
                        └── Yes → Level 2: Full stack restart
                                       │
                                  Wait 5 minutes
                                       │
                                  Still down?
                                       │
                                  └── Yes → ESCALATE TO HUMAN
                                            (Telegram + Email)
```

## Step 1: Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. Name your bot (e.g., "SPS Alert Bot")
4. Save the **Bot Token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Create a channel or group for alerts
6. Add your bot to the channel as admin
7. Get the **Chat ID**:
   - Send a message to the channel
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find the `chat.id` in the response

## Step 2: Configure Environment Variables

Add to your `.env` file on the VPS:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Email (use your SMTP provider)
SMTP_HOST=smtp.gmail.com
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
ALERT_EMAIL=your_alert_email@example.com
```

## Step 3: Update Docker Compose

The `docker-compose.prod.yml` has been updated to:
- Give n8n access to Docker socket (for self-healing commands)
- Mount recovery scripts
- Pass environment variables for notifications

## Step 4: Deploy to VPS

```bash
# SSH into VPS
ssh user@your-vps-ip

# Navigate to project
cd /path/to/new_SPS_Website

# Pull latest changes
git pull origin main

# Make scripts executable
chmod +x scripts/*.sh

# Restart stack with new configuration
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

## Step 5: Import n8n Workflows

1. Access n8n at `https://automator.sukhi.in`
2. Go to **Workflows** → **Import from File**
3. Import `scripts/n8n-workflows/self-healing-monitor.json`
4. Import `scripts/n8n-workflows/content-notification.json`
5. Configure credentials:
   - Add Telegram credential with your bot token
   - Add SMTP credential for email
6. **Activate both workflows**

## Step 6: Test the System

### Test Telegram Notifications
```bash
# Send test message
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "<YOUR_CHAT_ID>", "text": "Test: SPS Alert System Active"}'
```

### Test Content Webhook
```bash
curl -X POST "https://automator.sukhi.in/webhook/content-published" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "content_published",
    "content": {
      "title": "Test Article",
      "type": "blog",
      "url": "https://sps-security.com/blog/test",
      "quality_score": 85,
      "word_count": 1500
    }
  }'
```

### Test Self-Healing (Careful!)
```bash
# Simulate failure by stopping website container
docker stop sps-website

# Watch n8n execute recovery
# Check Telegram for notifications
```

## Recovery Levels

| Level | Action | Wait Time | Trigger |
|-------|--------|-----------|---------|
| 1 | Restart container | 3 minutes | First failure |
| 2 | Full stack restart | 5 minutes | L1 failed |
| 3 | Escalate to human | - | L2 failed |

## Safety Features

- **Rate limiting**: Max 3 auto-restarts per hour
- **Lock file**: Prevents overlapping recovery attempts
- **Audit log**: All actions logged to `/var/log/sps-recovery.log`
- **Cooldown**: 10-minute lock after recovery attempt

## Troubleshooting

### n8n can't execute Docker commands
```bash
# Check Docker socket permissions
ls -la /var/run/docker.sock

# Ensure n8n container has access
docker exec -it n8n docker ps
```

### Telegram messages not sending
1. Verify bot token is correct
2. Check bot is admin in channel
3. Verify chat ID (negative for channels)

### Scripts not executing
```bash
# Check script permissions
ls -la /path/to/scripts/

# Test manually
docker exec -it n8n /app/scripts/health_check.sh
```

## File Locations

| File | Purpose |
|------|---------|
| `scripts/health_check.sh` | Check all service health |
| `scripts/recover.sh` | Execute recovery actions |
| `scripts/diagnostics.sh` | Gather system info for escalation |
| `scripts/notify_content.sh` | Trigger content notification |
| `scripts/n8n-workflows/*.json` | Importable n8n workflows |

## Customization

### Change health check interval
Edit `self-healing-monitor.json`, node "Every 5 Minutes":
```json
"minutesInterval": 10  // Change to 10 minutes
```

### Add more services to monitor
Edit `health_check.sh` to add more container checks.

### Adjust recovery wait times
Edit `self-healing-monitor.json`:
- "Wait 3 Minutes" node: `"amount": 3`
- "Wait 5 Minutes" node: `"amount": 5`

## Security Notes

1. **Docker socket access** gives n8n full control of Docker. This is necessary for self-healing but powerful.
2. **Keep bot token secret** - anyone with it can send messages as your bot.
3. **Rate limiting** prevents runaway restart loops.
4. **Audit log** helps with post-incident analysis.
