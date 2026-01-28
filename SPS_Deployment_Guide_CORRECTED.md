

Check if services started correctly:

```bash
# Check website
docker logs sps-website --tail 50

# Check API
docker logs sps-brain --tail 50

# Check n8n
docker logs n8n --tail 50

# Check tunnel
docker logs cloudflared --tail 50
```

**Look for:**
- sps-website: "Server running on port 4321"
- sps-brain: "Uvicorn running on http://0.0.0.0:8000"
- cloudflared: "Connection established" or "Registered tunnel"

---

## Step 3.4: Test Your Live Website

Open browser and navigate to:

1. **https://sukhi.in** - Main website
2. **https://www.sukhi.in** - Should redirect or show same content
3. **https://api.sukhi.in** - API endpoint (may show "Not Found" - that's OK)
4. **https://automator.sukhi.in** - n8n login page

**Expected:**
- ✅ Green lock icon (SSL)
- ✅ No security warnings
- ✅ Fast load times (Cloudflare CDN)

---

# PHASE 4: SECURITY HARDENING

## Step 4.1: Protect n8n Admin Panel (CRITICAL)

Your n8n panel is currently PUBLIC. Lock it down:

1. Go to **Cloudflare Zero Trust** → **Access** → **Applications**
2. Click **Add an application**
3. Choose **Self-hosted**
4. Configure:
   - Name: `n8n Admin`
   - Session duration: `24 hours`
   - Subdomain: `automator`
   - Domain: `sukhi.in`
5. Click **Next**
6. Create policy:
   - Name: `Only Me`
   - Action: `Allow`
   - Include: `Emails` → `amar.sukhi@spsindia.com` (or your email)
7. Click **Next** → **Add application**

**Result:** Only your email can access `automator.sukhi.in`

---

## Step 4.2: Set Secure File Permissions

```bash
# Protect .env file
chmod 600 .env

# Verify
ls -la .env
# Should show: -rw------- (only root can read/write)
```

---

## Step 4.3: Enable UFW Firewall (Optional)

```bash
# Allow SSH (CRITICAL - don't lock yourself out)
ufw allow 22/tcp

# Enable firewall
ufw --force enable

# Check status
ufw status
```

**Note:** You don't need to open ports 4321, 8000, 5678 because Cloudflare Tunnel handles all traffic.

---

# PHASE 5: MAINTENANCE & MONITORING

## Step 5.1: View Logs

```bash
# Real-time logs (Ctrl+C to exit)
docker logs -f sps-website
docker logs -f sps-brain
docker logs -f n8n

# Last 100 lines
docker logs sps-website --tail 100
```

---

## Step 5.2: Restart Services

```bash
# Restart specific container
docker restart sps-website

# Restart all services
docker compose -f docker-compose.prod.yml restart

# Full rebuild (after code changes)
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Step 5.3: Update from GitHub

```bash
cd /root/sps-platform
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Step 5.4: Monitor Resource Usage

```bash
# Container stats (real-time)
docker stats

# Disk usage
df -h

# Memory usage
free -h
```

---

# 🆘 TROUBLESHOOTING

## Website shows "502 Bad Gateway"

**Cause:** Service not responding or tunnel disconnected

**Fix:**
```bash
# Check which container is down
docker ps

# Check tunnel connection
docker logs cloudflared --tail 20

# Restart all
docker compose -f docker-compose.prod.yml restart
```

---

## "Cannot connect to Docker daemon"

**Cause:** Docker not running

**Fix:**
```bash
# Start Docker
systemctl start docker

# Enable on boot
systemctl enable docker
```

---

## "Port already in use" error

**Cause:** Another service using internal ports

**Fix:**
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process (replace PID)
kill -9 PID
```

---

## Tunnel shows "Connection refused"

**Cause:** TUNNEL_TOKEN is wrong or tunnel deleted

**Fix:**
1. Go to Cloudflare Zero Trust → Networks → Tunnels
2. Find `sps-server` tunnel
3. Click **Configure** → Get new token
4. Update `.env` file with new token
5. Restart: `docker restart cloudflared`

---

## Out of disk space

**Check:**
```bash
df -h
```

**Clean up:**
```bash
# Remove unused images
docker system prune -a

# Remove old logs
docker system prune --volumes
```

---

# 📞 QUICK REFERENCE

## Common Commands

| Action | Command |
|--------|---------|
| Start all | `docker compose -f docker-compose.prod.yml up -d` |
| Stop all | `docker compose -f docker-compose.prod.yml down` |
| Restart all | `docker compose -f docker-compose.prod.yml restart` |
| View logs | `docker logs <container_name>` |
| Follow logs | `docker logs -f <container_name>` |
| List containers | `docker ps` |
| List all (including stopped) | `docker ps -a` |
| Container stats | `docker stats` |
| Update code | `git pull && docker compose -f docker-compose.prod.yml up -d --build` |
| Check tunnel | `docker logs cloudflared` |

---

## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Website | https://sukhi.in | Public-facing site |
| Website (www) | https://www.sukhi.in | Same as above |
| API | https://api.sukhi.in | Backend API |
| n8n Automation | https://automator.sukhi.in | Workflow automation |

---

## Container Names

| Container | Purpose | Internal Port |
|-----------|---------|---------------|
| sps-brain | Python API | 8000 |
| sps-website | Astro Frontend | 4321 |
| n8n | Automation | 5678 |
| sps-chroma | Vector DB | 8000 |
| cloudflared | Tunnel | N/A |

---

# 🎓 ARCHITECTURE OVERVIEW

```
Internet
   ↓
Cloudflare (SSL + CDN + Security)
   ↓
Cloudflare Tunnel (Encrypted)
   ↓
Your Server (Hostinger KVM 4)
   ↓
Docker Network (sps-network)
   ├── sps-website:4321 (Astro frontend)
   ├── sps-brain:8000 (FastAPI backend)
   ├── n8n:5678 (Automation)
   ├── chroma:8000 (Vector DB)
   └── cloudflared (Tunnel client)
```

**Key Points:**
- No ports exposed to internet (tunnel handles everything)
- All services communicate via Docker network
- Cloudflare provides SSL, CDN, DDoS protection
- Zero Trust access for n8n admin panel

---

# 🔒 SECURITY NOTES

## What's Protected

✅ SSL/TLS encryption (Cloudflare)
✅ DDoS protection (Cloudflare)
✅ No exposed ports (Cloudflare Tunnel)
✅ n8n admin panel (Zero Trust)
✅ .env file permissions (600)

## What You Should Do

- [ ] Set strong n8n password on first login
- [ ] Enable 2FA on Cloudflare account
- [ ] Regularly update server: `apt update && apt upgrade`
- [ ] Monitor logs for suspicious activity
- [ ] Backup `.env` file securely
- [ ] Backup n8n workflows regularly

---

# 📊 MONITORING & ALERTS

## Cloudflare Analytics

1. Go to **Cloudflare Dashboard** → **sukhi.in**
2. Click **Analytics & Logs** → **Traffic**
3. Monitor:
   - Requests per day
   - Bandwidth usage
   - Threats blocked
   - Response codes

## Set Up Alerts

1. Go to **Notifications** in Cloudflare
2. Create alerts for:
   - Tunnel down
   - High error rates (5xx codes)
   - DDoS attacks
   - SSL certificate expiry

---

# 🚀 PERFORMANCE OPTIMIZATION

## Enable Cloudflare Performance Features

1. Go to **Speed** → **Optimization**
2. Enable:
   - [x] Auto Minify (JavaScript, CSS, HTML)
   - [x] Brotli compression
   - [x] Early Hints
   - [x] Rocket Loader (test with your site)

## Monitor Performance

```bash
# Check container resource usage
docker stats --no-stream

# Check API response time
curl -w "@-" -o /dev/null -s https://api.sukhi.in/health <<'EOF'
   time_namelookup:  %{time_namelookup}
      time_connect:  %{time_connect}
   time_appconnect:  %{time_appconnect}
  time_pretransfer:  %{time_pretransfer}
     time_redirect:  %{time_redirect}
time_starttransfer:  %{time_starttransfer}
                   ----------
        time_total:  %{time_total}
EOF
```

---

# ✅ POST-DEPLOYMENT CHECKLIST

## Immediate (Day 1)

- [ ] All URLs load with SSL
- [ ] No 502/503 errors
- [ ] n8n login works
- [ ] API responds (test with curl/Postman)
- [ ] Cloudflare tunnel shows "healthy"
- [ ] All 5 containers running
- [ ] Set n8n admin password
- [ ] Test main website functionality

## Within 1 Week

- [ ] Enable Cloudflare Zero Trust for n8n
- [ ] Set up monitoring alerts
- [ ] Document any custom configurations
- [ ] Create first workflow in n8n
- [ ] Test API endpoints thoroughly
- [ ] Monitor resource usage patterns
- [ ] Set up automated backups

## Ongoing

- [ ] Weekly: Check logs for errors
- [ ] Monthly: Update server packages
- [ ] Monthly: Review Cloudflare analytics
- [ ] Quarterly: Test disaster recovery
- [ ] Quarterly: Update Docker images

---

# 📝 BACKUP STRATEGY

## What to Backup

1. **Code** - Already on GitHub ✅
2. **.env file** - Contains secrets
3. **n8n workflows** - Via n8n export
4. **Chroma vector DB** - Data persistence

## Manual Backup

```bash
# Backup .env
cp .env .env.backup-$(date +%Y%m%d)

# Backup n8n data
docker exec n8n n8n export:workflow --all --output=/data/backup.json

# Backup Chroma data
docker exec sps-chroma tar czf /chroma/backup-$(date +%Y%m%d).tar.gz /chroma/chroma
```

---

# 🎉 SUCCESS CRITERIA

Your deployment is successful when:

1. ✅ https://sukhi.in loads with green padlock
2. ✅ https://api.sukhi.in responds (even if 404)
3. ✅ https://automator.sukhi.in shows n8n login
4. ✅ All 5 containers show "Up" status
5. ✅ No errors in `docker logs`
6. ✅ Cloudflare tunnel status: Connected
7. ✅ SSL certificate valid (Cloudflare-issued)
8. ✅ Fast load times (<2 seconds)

---

**Guide Version:** 2.0 - Corrected & Complete
**Last Updated:** January 27, 2026
**Status:** Cloudflare ✅ | Server Deployment ⏳
