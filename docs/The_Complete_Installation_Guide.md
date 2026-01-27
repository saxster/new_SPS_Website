# The Complete SPS Platform Installation Guide

**Production Deployment to Hostinger KVM via Cloudflare Tunnel**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Part 1: Cloudflare Configuration](#part-1-cloudflare-configuration)
5. [Part 2: Server Setup](#part-2-server-setup)
6. [Part 3: Docker Installation](#part-3-docker-installation)
7. [Part 4: Repository Deployment](#part-4-repository-deployment)
8. [Part 5: Environment Configuration](#part-5-environment-configuration)
9. [Part 6: Container Deployment](#part-6-container-deployment)
10. [Part 7: Verification & Testing](#part-7-verification--testing)
11. [Part 8: Troubleshooting](#part-8-troubleshooting)
12. [Part 9: Maintenance](#part-9-maintenance)

---

## Overview

This guide documents the complete production deployment of the SPS Platform to a Hostinger KVM server using Cloudflare Tunnel for secure, encrypted connectivity. The deployment includes:

- **Frontend**: Astro-based website
- **Backend**: Python FastAPI with AI capabilities
- **Automation**: n8n workflow engine
- **Database**: ChromaDB vector database
- **Infrastructure**: Docker containerized architecture
- **Security**: Cloudflare Tunnel with SSL/TLS encryption

**Deployment Date**: January 27, 2026  
**Server**: Hostinger KVM 4 (srv1298636.hstgr.cloud)  
**Domain**: sukhi.in

---

## Architecture

```
Internet
    ↓
Cloudflare CDN/DDoS Protection
    ↓
Cloudflare Tunnel (Encrypted)
    ↓
Hostinger KVM 4 Server (72.61.172.188)
    ├─ cloudflared (tunnel connector)
    ├─ sps-website:4321 (Astro frontend)
    ├─ sps-brain:8000 (Python FastAPI)
    ├─ n8n:5678 (automation)
    └─ chroma:8000 (vector database)
```

**Routing Configuration**:
- `https://sukhi.in` → sps-website (port 4321)
- `https://www.sukhi.in` → sps-website (port 4321)
- `https://api.sukhi.in` → sps-brain (port 8000)
- `https://automator.sukhi.in` → n8n (port 5678)

---

## Prerequisites

### Required Accounts
- [x] Cloudflare account with domain added
- [x] Hostinger VPS/KVM account
- [x] GitHub account with repository access
- [x] Google AI Studio account (Gemini API)

### Required API Keys
1. **Gemini API Key**: https://aistudio.google.com/app/apikey
2. **Cloudflare Tunnel Token**: From Cloudflare Zero Trust dashboard
3. **Optional but Recommended**:
   - Serper/SerpAPI key (web search)
   - News API key (news aggregation)
   - Anthropic API key (Claude, for multi-LLM fact checking)
   - OpenAI API key (GPT models, for multi-LLM fact checking)
   - Brave Search API key (alternative search)

### Technical Requirements
- Domain name with nameservers pointed to Cloudflare
- VPS/KVM server running Ubuntu 24.04 LTS
- Minimum 8GB RAM, 200GB disk space
- Root or sudo access to server

---

## Part 1: Cloudflare Configuration

### Step 1.1: Domain Setup

1. **Add Domain to Cloudflare**:
   - Login to Cloudflare dashboard
   - Click "Add Site"
   - Enter your domain (e.g., `sukhi.in`)
   - Select Free plan
   - Cloudflare will provide nameservers

2. **Update Nameservers at Registrar**:
   - Go to your domain registrar (e.g., GoDaddy, Namecheap)
   - Replace existing nameservers with Cloudflare's:
     ```
     Example:
     ns1.cloudflare.com
     ns2.cloudflare.com
     ```
   - Wait 24-48 hours for propagation (usually faster)

3. **Verify Domain Active**:
   - Return to Cloudflare dashboard
   - Check for "Active" status on domain
   - Green checkmark indicates successful activation

### Step 1.2: SSL/TLS Configuration

1. **Navigate to SSL/TLS Settings**:
   - Select your domain in Cloudflare
   - Click "SSL/TLS" in left sidebar

2. **Set Encryption Mode**:
   - Select "Full" encryption mode
   - This enables encryption between:
     * Visitor ↔ Cloudflare (Edge certificate)
     * Cloudflare ↔ Your server (via tunnel)

3. **Verify Edge Certificates**:
   - Go to "SSL/TLS" → "Edge Certificates"
   - Confirm "Universal SSL" is Active
   - Should show certificate covering:
     * `sukhi.in`
     * `*.sukhi.in` (wildcard)
   - Auto-renews before expiration

**Result**: All your URLs (sukhi.in, www.sukhi.in, api.sukhi.in, automator.sukhi.in) will automatically have HTTPS with valid certificates.

### Step 1.3: Cloudflare Tunnel Creation

1. **Access Zero Trust Dashboard**:
   - From Cloudflare main dashboard
   - Click "Zero Trust" in left sidebar
   - Or visit: https://one.dash.cloudflare.com/

2. **Create New Tunnel**:
   ```
   Navigate: Zero Trust → Networks → Tunnels
   Click: "Create a tunnel"
   Select: "Cloudflared"
   Name: sps-server (or your preferred name)
   Click: "Save tunnel"
   ```

3. **Save Tunnel Token**:
   - After creation, you'll see a token string
   - **CRITICAL**: Copy this token immediately
   - Format: `eyJhIjoiXXXXXXX...` (long base64 string)
   - Save securely - you'll need it for deployment

4. **Configure Public Hostnames**:

   Click "Public Hostname" tab, then add each route:

   **Route 1: Main Website**
   ```
   Subdomain: [leave blank]
   Domain: sukhi.in
   Service Type: HTTP
   URL: sps-website:4321
   ```

   **Route 2: WWW Subdomain**
   ```
   Subdomain: www
   Domain: sukhi.in
   Service Type: HTTP
   URL: sps-website:4321
   ```

   **Route 3: API Subdomain**
   ```
   Subdomain: api
   Domain: sukhi.in
   Service Type: HTTP
   URL: sps-brain:8000
   ```

   **Route 4: Automation Subdomain**
   ```
   Subdomain: automator
   Domain: sukhi.in
   Service Type: HTTP
   URL: n8n:5678
   ```

5. **Verify Tunnel Configuration**:
   - Tunnel status shows "Inactive" (normal - will activate when cloudflared connects)
   - All 4 routes listed under "Public Hostname"
   - Tunnel ID and token saved

### Step 1.4: DNS Configuration

Cloudflare automatically creates DNS records when you configure tunnel routes, but verify:

1. **Check DNS Records**:
   ```
   Navigate: DNS → Records
   
   Expected records (all should be CNAME with Proxy enabled):
   
   Type    Name        Target                  Proxy Status
   CNAME   sukhi.in    xxx.cfargotunnel.com   Proxied (orange cloud)
   CNAME   www         xxx.cfargotunnel.com   Proxied (orange cloud)
   CNAME   api         xxx.cfargotunnel.com   Proxied (orange cloud)
   CNAME   automator   xxx.cfargotunnel.com   Proxied (orange cloud)
   ```

2. **Ensure Proxy Enabled**:
   - All records must show orange cloud icon
   - This enables Cloudflare CDN, DDoS protection, and SSL

3. **Wait for Propagation**:
   - DNS changes propagate in 1-5 minutes
   - Test with: `dig sukhi.in` or online DNS checkers

**✅ Cloudflare Configuration Complete**

---

## Part 2: Server Setup

### Step 2.1: Access Hostinger Panel

1. **Login to Hostinger**:
   - URL: https://hpanel.hostinger.com
   - Navigate to "VPS" section
   - Select your KVM instance

2. **Server Information**:
   ```
   Example from our deployment:
   Hostname: srv1298636.hstgr.cloud
   IP Address: 72.61.172.188
   OS: Ubuntu 24.04 LTS
   Type: KVM 4
   RAM: 8GB
   Disk: 200GB
   Bandwidth: 16TB/month
   ```

### Step 2.2: Access Web Terminal

**Option A: Web Terminal (Recommended)**:
1. In Hostinger panel, click "Terminal" button (top right)
2. New browser tab opens with terminal session
3. Already logged in as root - no password needed
4. Terminal URL format: `https://mum.hostingervps.com/2688/?token=...`

**Option B: SSH Access** (if preferred):
1. Get root password:
   - Click "Change" button in Hostinger panel
   - View or reset password
2. Connect via SSH:
   ```bash
   ssh root@72.61.172.188
   ```
3. Enter password when prompted

**We used Option A (Web Terminal) for this deployment.**

### Step 2.3: Verify Server Status

Once in terminal:

```bash
# Check system info
uname -a
# Ubuntu 24.04 LTS

# Check resources
free -h
# Should show ~8GB RAM with 97% available

df -h
# Should show ~200GB disk with 197GB free

# Check network
ip addr show
# Should show your server IP
```

---

## Part 3: Docker Installation

### Step 3.1: Update System

```bash
# Update package list
apt update -y

# Optional: Apply security updates (takes 2-3 minutes)
# apt upgrade -y
```

**Note**: We skipped `apt upgrade` for speed since security updates weren't critical for immediate deployment. Run it later during maintenance.

### Step 3.2: Install Docker

```bash
# Install Docker using official convenience script
curl -fsSL https://get.docker.com | sh
```

**This command**:
- Downloads Docker installation script from get.docker.com
- Installs Docker Engine, CLI, containerd, and Docker Compose
- Takes 2-3 minutes to complete
- Automatically configures Docker daemon

**Expected output (end of installation)**:
```
================================================================================
To run Docker as a non-privileged user, consider setting up the
Docker daemon in rootless mode for your user:

    dockerd-rootless-setuptool.sh install

Visit https://docs.docker.com/go/rootless/ to learn about rootless mode.
================================================================================
```

### Step 3.3: Verify Docker Installation

```bash
# Check Docker version
docker --version
# Expected: Docker version 29.2.0, build 0b9d198

# Verify Docker Compose
docker compose version
# Expected: Docker Compose version v2.x.x

# Test Docker
docker run hello-world
# Should download and run test container successfully
```

**✅ Docker Installation Complete**

---

## Part 4: Repository Deployment

### Step 4.1: Clone GitHub Repository

```bash
# Clone repository to /root/sps-platform
git clone https://github.com/Saxster/new_SPS_Website.git sps-platform

# Expected output:
# Cloning into 'sps-platform'...
# remote: Enumerating objects: 614, done.
# remote: Counting objects: 100% (614/614), done.
# remote: Compressing objects: 100% (501/501), done.
# remote: Total 614 (delta 158), reused 546 (delta 90), pack-reused 0
# Receiving objects: 100% (614/614), 2.29 MiB | 26.39 MiB/s, done.
# Resolving deltas: 100% (158/158), done.
```

### Step 4.2: Navigate to Project Directory

```bash
cd sps-platform

# Verify location
pwd
# Expected: /root/sps-platform

# List contents
ls -la
# Should see:
# - docker-compose.prod.yml
# - Dockerfile
# - agent_backend/
# - website/
# - scripts/
# - requirements.txt
# etc.
```

---

## Part 5: Environment Configuration

### Step 5.1: Create .env File

```bash
# Open nano editor
nano .env
```

### Step 5.2: Add Environment Variables

**CRITICAL**: Use `GOOGLE_API_KEY` (NOT `GEMINI_API_KEY`) as the primary key name. While the Python code supports both, `docker-compose.prod.yml` expects `GOOGLE_API_KEY`.

**Complete .env Template**:

```env
# === REQUIRED KEYS ===

# Your Gemini API Key (from https://aistudio.google.com/app/apikey)
GOOGLE_API_KEY=your-gemini-api-key-here

# Your Cloudflare Tunnel Token (from Cloudflare Zero Trust)
TUNNEL_TOKEN=your-cloudflare-tunnel-token-here

# === OPTIONAL KEYS (Recommended) ===

# Search API (Serper or SerpAPI - both work)
SERPAPI_API_KEY=your-serper-or-serpapi-key-here

# News API (from https://newsapi.org)
NEWS_API_KEY=your-newsapi-key-here

# === OPTIONAL KEYS (Multi-LLM Fact Checking) ===

# Anthropic Claude API
ANTHROPIC_API_KEY=your-anthropic-key-here

# OpenAI GPT API
OPENAI_API_KEY=your-openai-key-here

# Brave Search API
BRAVE_SEARCH_API_KEY=your-brave-search-key-here
```

**Important Notes**:
- Replace all `your-xxx-key-here` with actual API keys
- No quotes needed around values
- No spaces around `=` sign
- Keep this file secure - never commit to Git

### Step 5.3: Save and Exit

```bash
# In nano editor:
# 1. Press Ctrl+O (save)
# 2. Press Enter (confirm filename)
# 3. Press Ctrl+X (exit)
```

### Step 5.4: Verify .env File

```bash
# Check file exists
ls -lh .env
# Should show file with size (e.g., 891 bytes)

# Verify GOOGLE_API_KEY is set (don't show actual key)
cat .env | grep GOOGLE_API_KEY
# Should show: GOOGLE_API_KEY=xxx...

# DO NOT run 'cat .env' as it would display sensitive keys in terminal
```

---

## Part 6: Container Deployment

### Step 6.1: Build and Deploy Containers

```bash
# Build images and start all containers in detached mode
docker compose -f docker-compose.prod.yml up -d --build
```

**Expected Build Process** (5-7 minutes total):

```
[+] Building 316.1s (27/27) FINISHED
 => Building sps-brain (Python API)
    => Installing system dependencies (apt-get)
    => Installing Python packages (pip) - SLOWEST STEP (2-3 min)
    => Copying application code
    => Exporting image layers (2-3 min)
    
 => Building sps-website (Astro frontend)
    => Installing Node packages (npm install)
    => Running build (npm run build)
    => Exporting image
    
 => Pulling external images
    => chromadb/chroma:latest
    => docker.n8n.io/n8nio/n8n:latest
    => cloudflare/cloudflared:latest

[+] Running 10/10
 ✔ Network sps-platform_sps-network  Created
 ✔ Volume sps-platform_chroma_data   Created
 ✔ Volume sps-platform_n8n_data      Created
 ✔ Container sps-chroma              Started
 ✔ Container sps-brain               Started
 ✔ Container sps-website             Started
 ✔ Container n8n                     Started
 ✔ Container cloudflared             Started
```

**Warnings You Can Ignore**:
- `The attribute 'version' is obsolete` - Cosmetic warning, Docker Compose v2 doesn't need version field
- `Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using GOOGLE_API_KEY` - Expected if you set both

### Step 6.2: Verify Container Status

```bash
# List running containers
docker ps
```

**Expected Output** (all 5 containers):
```
CONTAINER ID   IMAGE                           COMMAND                  STATUS          PORTS      NAMES
xxxxxxxxxx     sps-platform-sps-website        "docker-entrypoint..."   Up 30 seconds   4321/tcp   sps-website
xxxxxxxxxx     docker.n8n.io/n8nio/n8n         "tini -- /docker-e..."   Up 30 seconds   5678/tcp   n8n
xxxxxxxxxx     cloudflare/cloudflared:latest   "cloudflared --no-..."   Up 30 seconds              cloudflared
xxxxxxxxxx     sps-platform-sps-brain          "uvicorn agent_bac..."   Up 30 seconds   8000/tcp   sps-brain
xxxxxxxxxx     chromadb/chroma:latest          "dumb-init -- chro..."   Up 30 seconds   8000/tcp   sps-chroma
```

**All containers should show**:
- ✅ STATUS: "Up X seconds" or "Up X minutes"
- ✅ No "Restarting" or "Exited" status

### Step 6.3: Check Container Logs

```bash
# View logs from all services (last 20 lines)
docker compose -f docker-compose.prod.yml logs --tail=20
```

**Expected Healthy Logs**:

**sps-brain**:
```
sps-brain  | INFO:     Started server process [1]
sps-brain  | INFO:     Application startup complete.
sps-brain  | INFO:     Uvicorn running on http://0.0.0.0:8000
```

**sps-website**:
```
sps-website  | Server listening on 
sps-website  |   local: http://localhost:4321 
sps-website  |   network: http://172.18.0.6:4321
```

**cloudflared**:
```
cloudflared  | INF Registered tunnel connection connIndex=0
cloudflared  | INF Updated to new configuration
cloudflared  | (Shows all 4 route configurations)
```

**n8n**:
```
n8n  | Editor is now accessible via:
n8n  | https://automator.sukhi.in
```

**chroma**:
```
sps-chroma  | Connect to Chroma at: http://localhost:8000
```

### Step 6.4: Check Specific Service Logs

```bash
# Check Python API logs
docker compose -f docker-compose.prod.yml logs sps-brain --tail=20

# Check website logs
docker compose -f docker-compose.prod.yml logs sps-website --tail=20

# Check tunnel logs
docker compose -f docker-compose.prod.yml logs cloudflared --tail=20

# Follow logs in real-time (Ctrl+C to exit)
docker compose -f docker-compose.prod.yml logs -f
```

**✅ Container Deployment Complete**

---

## Part 7: Verification & Testing

### Step 7.1: Test Main Website

**URL**: https://sukhi.in

**Expected**:
- ✅ Page loads immediately
- ✅ Green padlock in browser (valid SSL certificate)
- ✅ Shows SPS Security Services homepage
- ✅ All assets load (images, CSS, JS)

**Browser Developer Tools Check**:
- Open DevTools (F12)
- Network tab: All requests should show "200 OK"
- Console tab: No errors (warnings are OK)
- Security tab: "Connection is secure" with valid certificate

### Step 7.2: Test WWW Subdomain

**URL**: https://www.sukhi.in

**Expected**:
- ✅ Same content as main domain
- ✅ SSL certificate valid for wildcard (*.sukhi.in)
- ✅ No redirect loops

### Step 7.3: Test API Endpoint

**URL**: https://api.sukhi.in

**Expected Responses**:

**Root endpoint**: https://api.sukhi.in/
```json
{
  "message": "SPS Brain API",
  "version": "1.0.0",
  "status": "healthy"
}
```

**Health check**: https://api.sukhi.in/health
```json
{
  "status": "healthy",
  "timestamp": "2026-01-27T06:15:00Z"
}
```

**Using curl from terminal**:
```bash
# Test API from server
curl https://api.sukhi.in/health
```

### Step 7.4: Test Automation Dashboard

**URL**: https://automator.sukhi.in

**Expected**:
- ✅ n8n login/setup screen loads
- ✅ SSL certificate valid
- ✅ First-time setup wizard appears

**Setup n8n** (optional, for automation features):
1. Create owner account (email + password)
2. Skip usage survey
3. Dashboard loads with "Add first workflow" prompt

### Step 7.5: Verify Cloudflare Tunnel

**Check Cloudflare Dashboard**:
1. Go to: Zero Trust → Networks → Tunnels
2. Find your tunnel (e.g., "sps-server")
3. Status should show: ✅ **HEALTHY**
4. Should show "4 connections" (Mumbai data centers)
5. Traffic metrics should start showing after site visits

**Check from Server**:
```bash
# View cloudflared logs
docker compose -f docker-compose.prod.yml logs cloudflared

# Should show:
# - "Registered tunnel connection" (4 times)
# - "Updated to new configuration"
# - All ingress rules listed
```

### Step 7.6: Performance Testing

**Using curl to test response times**:
```bash
# Test main site
time curl -o /dev/null -s -w "Time: %{time_total}s\n" https://sukhi.in

# Test API
time curl -o /dev/null -s -w "Time: %{time_total}s\n" https://api.sukhi.in/health
```

**Expected**:
- First request: ~1-2 seconds (cold start)
- Subsequent requests: <500ms (cached)

**Using browser DevTools**:
- Network tab → Reload page
- Check "Load" time at bottom
- Should be under 2 seconds for full page load

### Step 7.7: SSL Certificate Verification

**Using SSL Labs** (comprehensive test):
1. Visit: https://www.ssllabs.com/ssltest/
2. Enter: sukhi.in
3. Wait for test to complete (~2 minutes)

**Expected Grade**: A or A+

**Using Browser**:
1. Click padlock icon in address bar
2. Click "Connection is secure"
3. Click "Certificate is valid"
4. Verify:
   - Issued by: Cloudflare
   - Valid for: sukhi.in, *.sukhi.in
   - Expires: ~3 months from now
   - Encryption: TLS 1.3

**Using openssl** (command line):
```bash
# Check certificate details
openssl s_client -connect sukhi.in:443 -servername sukhi.in < /dev/null | openssl x509 -noout -text
```

**✅ All Services Verified and Working**

---

## Part 8: Troubleshooting

### Issue 1: Containers Not Starting

**Symptom**:
```bash
docker ps
# Shows no containers or containers constantly restarting
```

**Diagnosis**:
```bash
# View all containers including stopped
docker ps -a

# Check logs for errors
docker compose -f docker-compose.prod.yml logs --tail=100

# Check specific container
docker compose -f docker-compose.prod.yml logs sps-brain
```

**Common Causes**:

1. **Missing .env file or incorrect API keys**
   ```bash
   # Verify .env exists
   ls -lh .env
   
   # Check GOOGLE_API_KEY is set (without showing value)
   grep "GOOGLE_API_KEY=" .env | cut -d'=' -f1
   ```
   
   **Fix**: Recreate .env file with correct keys

2. **Port conflicts**
   ```bash
   # Check if ports already in use
   ss -tlnp | grep -E ':(4321|8000|5678)'
   ```
   
   **Fix**: Stop conflicting services or modify ports in docker-compose.prod.yml

3. **Insufficient disk space**
   ```bash
   df -h
   # Check if disk usage > 90%
   ```
   
   **Fix**: Clean up old Docker images/containers
   ```bash
   docker system prune -a
   ```

4. **Memory issues**
   ```bash
   free -h
   # Check if RAM usage > 90%
   ```
   
   **Fix**: Restart server or upgrade to higher RAM plan

**Resolution**:
```bash
# Stop all containers
docker compose -f docker-compose.prod.yml down

# Remove volumes (if needed - WARNING: deletes data)
# docker compose -f docker-compose.prod.yml down -v

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build
```

### Issue 2: "Connection closed" During Build

**Symptom**: Terminal disconnects during `docker compose up -d --build`

**This is Normal**: Build takes 5-7 minutes and terminal sessions may timeout.

**Solution**:
1. Wait 10 minutes from when you started the build
2. Reconnect to terminal
3. Check status:
   ```bash
   cd /root/sps-platform
   docker ps
   ```
4. If containers are running: ✅ Build completed successfully
5. If no containers: Restart build

**Alternative** (prevents disconnection):
```bash
# Run build in background with logging
nohup docker compose -f docker-compose.prod.yml up -d --build > build.log 2>&1 &

# Check progress
tail -f build.log

# Press Ctrl+C to stop watching (build continues)
```

### Issue 3: Cloudflare Tunnel Not Connecting

**Symptom**:
- Containers running but website shows "502 Bad Gateway"
- Cloudflare dashboard shows tunnel as "Inactive"

**Diagnosis**:
```bash
# Check cloudflared logs
docker compose -f docker-compose.prod.yml logs cloudflared

# Look for errors like:
# - "failed to register connection"
# - "unauthorized"
# - "tunnel token invalid"
```

**Common Causes**:

1. **Invalid Tunnel Token**
   ```bash
   # Check if TUNNEL_TOKEN is set
   grep "TUNNEL_TOKEN=" .env | cut -d'=' -f1
   ```
   
   **Fix**: 
   - Get new token from Cloudflare Zero Trust → Tunnels
   - Update .env file
   - Restart: `docker compose -f docker-compose.prod.yml restart cloudflared`

2. **Network connectivity issues**
   ```bash
   # Test outbound connectivity from container
   docker exec cloudflared ping -c 4 1.1.1.1
   ```
   
   **Fix**: Check firewall rules, ensure port 443 outbound is open

3. **Incorrect hostname mappings**
   - Check Cloudflare tunnel configuration
   - Ensure hostnames match: `sukhi.in`, `api.sukhi.in`, etc.
   - Ensure service names match: `sps-website:4321`, `sps-brain:8000`

**Resolution**:
```bash
# Restart tunnel
docker compose -f docker-compose.prod.yml restart cloudflared

# Check logs
docker compose -f docker-compose.prod.yml logs cloudflared

# Should see: "Registered tunnel connection" messages
```

### Issue 4: API Returning Errors

**Symptom**: https://api.sukhi.in shows 500 errors or timeout

**Diagnosis**:
```bash
# Check sps-brain logs
docker compose -f docker-compose.prod.yml logs sps-brain --tail=50

# Look for Python errors, missing imports, API key errors
```

**Common Causes**:

1. **Missing API keys**
   ```
   Error: "GOOGLE_API_KEY not set"
   ```
   
   **Fix**: Add/verify GOOGLE_API_KEY in .env, restart containers

2. **Python dependency issues**
   ```
   Error: "ModuleNotFoundError: No module named 'xxx'"
   ```
   
   **Fix**: Check requirements.txt, rebuild
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build sps-brain
   ```

3. **ChromaDB connection issues**
   ```
   Error: "Could not connect to chroma"
   ```
   
   **Fix**: Ensure chroma container is running
   ```bash
   docker ps | grep chroma
   docker compose -f docker-compose.prod.yml restart sps-chroma sps-brain
   ```

### Issue 5: Website Shows 502 Bad Gateway

**Symptom**: https://sukhi.in shows Cloudflare 502 error

**Possible Causes**:

1. **sps-website container not running**
   ```bash
   docker ps | grep sps-website
   ```
   
   **Fix**: Restart container
   ```bash
   docker compose -f docker-compose.prod.yml restart sps-website
   ```

2. **Cloudflare tunnel not connected**
   - Check Issue 3 above

3. **Astro build failed**
   ```bash
   docker compose -f docker-compose.prod.yml logs sps-website
   ```
   
   **Fix**: Check for build errors, rebuild
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build sps-website
   ```

### Issue 6: High Memory Usage

**Symptom**:
```bash
free -h
# Shows RAM usage > 80%
```

**Diagnosis**:
```bash
# Check container memory usage
docker stats --no-stream

# Shows memory per container
```

**Resolution**:
1. **Restart containers** (frees leaked memory):
   ```bash
   docker compose -f docker-compose.prod.yml restart
   ```

2. **Set memory limits** in docker-compose.prod.yml:
   ```yaml
   services:
     sps-brain:
       deploy:
         resources:
           limits:
             memory: 2G
     sps-website:
       deploy:
         resources:
           limits:
             memory: 1G
   ```

3. **Upgrade server** if consistently high usage

### Issue 7: DNS Not Resolving

**Symptom**: Domain doesn't resolve to Cloudflare

**Diagnosis**:
```bash
# Check DNS from external location
dig sukhi.in

# Should show Cloudflare IPs (104.x.x.x or 172.x.x.x range)
```

**Resolution**:
1. Verify nameservers at registrar point to Cloudflare
2. Wait 24-48 hours for full propagation
3. Clear DNS cache locally:
   - Mac: `sudo dscacheutil -flushcache`
   - Windows: `ipconfig /flushdns`
   - Linux: `sudo systemd-resolve --flush-caches`

### Getting Help

**Collect Debug Information**:
```bash
# Create debug bundle
cd /root/sps-platform

echo "=== System Info ===" > debug.txt
uname -a >> debug.txt
free -h >> debug.txt
df -h >> debug.txt

echo -e "\n=== Docker Version ===" >> debug.txt
docker --version >> debug.txt

echo -e "\n=== Running Containers ===" >> debug.txt
docker ps >> debug.txt

echo -e "\n=== Container Logs ===" >> debug.txt
docker compose -f docker-compose.prod.yml logs --tail=100 >> debug.txt

echo -e "\n=== .env File (sanitized) ===" >> debug.txt
cat .env | sed 's/=.*/=***HIDDEN***/' >> debug.txt

cat debug.txt
```

---

## Part 9: Maintenance

### Daily Operations

**Check Container Health**:
```bash
# Quick status check
docker ps

# Check for any restarting containers
docker ps | grep -v "Up"
```

**View Recent Logs**:
```bash
# Last hour of logs
docker compose -f docker-compose.prod.yml logs --since 1h

# Follow logs in real-time
docker compose -f docker-compose.prod.yml logs -f
```

### Weekly Maintenance

**Update Docker Images**:
```bash
cd /root/sps-platform

# Pull latest images (n8n, chroma, cloudflared)
docker compose -f docker-compose.prod.yml pull

# Restart with new images
docker compose -f docker-compose.prod.yml up -d
```

**Clean Up Old Images**:
```bash
# Remove unused images/containers
docker system prune -a

# Check disk usage
docker system df
```

**Backup Important Data**:
```bash
# Backup n8n workflows
docker exec n8n n8n export:workflow --backup --output=/data/backups/

# Backup chroma database
docker exec sps-chroma tar -czf /data/backup.tar.gz /data/

# Copy backups to local machine (from your Mac/PC)
scp root@72.61.172.188:/root/sps-platform/backups/* ./local-backups/
```

### Monthly Maintenance

**Update System Packages**:
```bash
# Update Ubuntu packages
apt update && apt upgrade -y

# Reboot if kernel updated
reboot
```

**Review Logs for Issues**:
```bash
# Check for errors in last 30 days
docker compose -f docker-compose.prod.yml logs --since 30d | grep -i error

# Check API errors
docker compose -f docker-compose.prod.yml logs sps-brain --since 30d | grep -i error
```

**Update Application Code**:
```bash
cd /root/sps-platform

# Pull latest code from GitHub
git pull origin main

# Rebuild containers with new code
docker compose -f docker-compose.prod.yml up -d --build
```

**Monitor Resource Usage**:
```bash
# Check disk space
df -h

# Check memory
free -h

# Check CPU load
uptime

# Container resource usage
docker stats --no-stream
```

### Security Maintenance

**Rotate API Keys** (every 3-6 months):
```bash
# Update keys in .env
nano .env

# Restart affected services
docker compose -f docker-compose.prod.yml restart
```

**Review Cloudflare Security**:
- Check Zero Trust → Logs for suspicious activity
- Review firewall rules
- Update tunnel token if compromised

**Update Docker Images** (security patches):
```bash
# Pull security updates for base images
docker compose -f docker-compose.prod.yml pull

# Rebuild custom images
docker compose -f docker-compose.prod.yml build

# Restart with updated images
docker compose -f docker-compose.prod.yml up -d
```

### Monitoring Setup (Optional)

**Enable n8n Monitoring Workflow**:
1. Login to https://automator.sukhi.in
2. Import workflow from: `/root/sps-platform/n8n_sentinel_workflow.json`
3. Configure notifications (email, Slack, etc.)
4. Activate workflow

**Set up Uptime Monitoring**:
- Use Cloudflare → Analytics for basic metrics
- Consider: UptimeRobot, Pingdom, or StatusCake for alerts

### Disaster Recovery

**Complete Backup**:
```bash
# Stop containers
docker compose -f docker-compose.prod.yml down

# Backup entire platform
cd /root
tar -czf sps-platform-backup-$(date +%Y%m%d).tar.gz sps-platform/

# Restart containers
cd sps-platform
docker compose -f docker-compose.prod.yml up -d
```

**Restore from Backup**:
```bash
# Stop and remove existing deployment
cd /root/sps-platform
docker compose -f docker-compose.prod.yml down -v

# Restore from backup
cd /root
tar -xzf sps-platform-backup-YYYYMMDD.tar.gz

# Restart
cd sps-platform
docker compose -f docker-compose.prod.yml up -d
```

---

## Appendix A: Key Files Reference

### docker-compose.prod.yml
Main orchestration file defining all 5 services and their configuration.

**Key sections**:
- Services: sps-brain, sps-website, n8n, chroma, cloudflared
- Networks: sps-network (internal Docker network)
- Volumes: chroma_data, n8n_data (persistent storage)
- Environment: Loaded from .env file

### .env File
Contains all sensitive configuration and API keys.

**Required variables**:
- `GOOGLE_API_KEY`: Gemini API key
- `TUNNEL_TOKEN`: Cloudflare tunnel authentication

**Optional variables**:
- `SERPAPI_API_KEY`, `NEWS_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `BRAVE_SEARCH_API_KEY`

### Dockerfile (for sps-brain)
Builds Python API container with all dependencies.

**Base**: python:3.11-slim  
**Key steps**:
1. Install system dependencies
2. Copy requirements.txt
3. Install Python packages
4. Copy application code
5. Expose port 8000
6. Run uvicorn server

### Dockerfile (for sps-website)
Builds Astro frontend container.

**Base**: node:18-alpine  
**Key steps**:
1. Copy package files
2. Install npm dependencies
3. Copy source code
4. Build static site
5. Expose port 4321
6. Run Node server

---

## Appendix B: Port Reference

| Service | Internal Port | External Access | Purpose |
|---------|---------------|-----------------|---------|
| sps-website | 4321 | https://sukhi.in | Astro frontend |
| sps-brain | 8000 | https://api.sukhi.in | Python API |
| n8n | 5678 | https://automator.sukhi.in | Workflow automation |
| sps-chroma | 8000 | Internal only | Vector database |
| cloudflared | N/A | N/A | Tunnel connector |

**Note**: All external access goes through Cloudflare Tunnel (encrypted). No ports are directly exposed to the internet.

---

## Appendix C: Useful Commands Reference

### Container Management
```bash
# Start all containers
docker compose -f docker-compose.prod.yml up -d

# Stop all containers
docker compose -f docker-compose.prod.yml down

# Restart all containers
docker compose -f docker-compose.prod.yml restart

# Restart specific container
docker compose -f docker-compose.prod.yml restart sps-brain

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build

# View container status
docker ps

# View all containers (including stopped)
docker ps -a
```

### Logs and Debugging
```bash
# View logs (all services)
docker compose -f docker-compose.prod.yml logs

# View logs (specific service)
docker compose -f docker-compose.prod.yml logs sps-brain

# Follow logs in real-time
docker compose -f docker-compose.prod.yml logs -f

# View last N lines
docker compose -f docker-compose.prod.yml logs --tail=50

# View logs since time
docker compose -f docker-compose.prod.yml logs --since 1h
```

### Resource Monitoring
```bash
# Real-time container stats
docker stats

# Disk usage
docker system df

# Image list
docker images

# Container list with sizes
docker ps --size
```

### Cleanup
```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Clean everything unused
docker system prune -a --volumes
```

### Backup and Restore
```bash
# Backup volumes
docker run --rm -v sps-platform_chroma_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/chroma-backup.tar.gz /data

# Restore volumes
docker run --rm -v sps-platform_chroma_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/chroma-backup.tar.gz -C /
```

---

## Appendix D: Environment Variables Reference

### Required Variables

| Variable | Source | Purpose |
|----------|--------|---------|
| GOOGLE_API_KEY | Google AI Studio | Gemini API authentication |
| TUNNEL_TOKEN | Cloudflare Zero Trust | Tunnel authentication |

### Optional Variables

| Variable | Source | Purpose |
|----------|--------|---------|
| SERPAPI_API_KEY | SerpAPI/Serper | Web search functionality |
| NEWS_API_KEY | NewsAPI.org | News aggregation |
| ANTHROPIC_API_KEY | Anthropic Console | Claude API for multi-LLM fact checking |
| OPENAI_API_KEY | OpenAI Platform | GPT models for multi-LLM fact checking |
| BRAVE_SEARCH_API_KEY | Brave Search | Alternative search provider |

### How Application Uses Keys

**sps-brain (Python API)**:
- Loads environment variables on startup
- Validates required keys (GOOGLE_API_KEY)
- Optional keys enable additional features
- Falls back gracefully if optional keys missing

**Code reference**:
```python
# agent_backend/skills/gemini_client.py
self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
```

---

## Appendix E: Cloudflare Tunnel Configuration

### Tunnel Details
- **Tunnel ID**: Unique identifier (e.g., 910627df-e666-45d1-9a09-5ae3f79f70a1)
- **Tunnel Token**: Authentication token (base64 encoded)
- **Protocol**: QUIC (with HTTP/2 fallback)
- **Connections**: 4 redundant connections to nearest data centers

### Ingress Rules (docker-compose.prod.yml)
```yaml
tunnel:
  ingress:
    - hostname: sukhi.in
      service: http://sps-website:4321
    - hostname: www.sukhi.in
      service: http://sps-website:4321
    - hostname: api.sukhi.in
      service: http://sps-brain:8000
    - hostname: automator.sukhi.in
      service: http://n8n:5678
    - service: http_status:404  # Catch-all
```

### Connection Flow
```
1. User visits https://sukhi.in
2. DNS resolves to Cloudflare IP
3. Request hits Cloudflare edge
4. Cloudflare applies security (DDoS, WAF, etc.)
5. Tunnel forwards to server (encrypted)
6. cloudflared container receives request
7. Routes to sps-website:4321
8. Response flows back through tunnel
9. Cloudflare adds SSL certificate
10. User receives HTTPS response
```

---

## Appendix F: Deployment Checklist

### Pre-Deployment
- [ ] Domain added to Cloudflare
- [ ] Nameservers updated and propagated
- [ ] Cloudflare tunnel created
- [ ] Tunnel token saved securely
- [ ] All API keys obtained
- [ ] Server access verified
- [ ] Git repository accessible

### Deployment
- [ ] System packages updated
- [ ] Docker installed
- [ ] Repository cloned
- [ ] .env file created with all keys
- [ ] GOOGLE_API_KEY (not GEMINI_API_KEY) used
- [ ] Containers built successfully
- [ ] All 5 containers running

### Post-Deployment
- [ ] https://sukhi.in loads with SSL
- [ ] https://api.sukhi.in responds
- [ ] https://automator.sukhi.in accessible
- [ ] Cloudflare tunnel shows "Healthy"
- [ ] All 4 routes show traffic
- [ ] Logs show no errors
- [ ] Performance acceptable (<2s load time)

### Optional
- [ ] n8n configured with owner account
- [ ] Monitoring workflows imported
- [ ] Uptime monitoring configured
- [ ] Backup strategy implemented
- [ ] Documentation reviewed

---

## Appendix G: Common Error Messages

### "The GEMINI_API_KEY variable is not set"
**Cause**: docker-compose.prod.yml expects GOOGLE_API_KEY but .env has GEMINI_API_KEY

**Fix**:
```bash
nano .env
# Change GEMINI_API_KEY to GOOGLE_API_KEY
# Save and exit
docker compose -f docker-compose.prod.yml restart
```

### "failed to register connection"
**Cause**: Invalid Cloudflare tunnel token

**Fix**:
1. Get new token from Cloudflare Zero Trust
2. Update TUNNEL_TOKEN in .env
3. Restart: `docker compose -f docker-compose.prod.yml restart cloudflared`

### "Connection closed: token expired or not found"
**Cause**: Terminal session timeout (normal during long builds)

**Fix**:
- Wait for build to complete (10 minutes)
- Reconnect to terminal
- Check: `docker ps`

### "502 Bad Gateway"
**Causes**: Container not running, tunnel not connected, or network issue

**Fix**:
```bash
# Check containers
docker ps

# Check tunnel logs
docker compose -f docker-compose.prod.yml logs cloudflared

# Restart all
docker compose -f docker-compose.prod.yml restart
```

---

## Success Metrics

### Deployment Success Indicators

**Infrastructure**:
- ✅ All 5 containers running (sps-brain, sps-website, n8n, chroma, cloudflared)
- ✅ Cloudflare tunnel shows "Healthy" with 4 connections
- ✅ No containers in "Restarting" status
- ✅ Logs show no critical errors

**Accessibility**:
- ✅ https://sukhi.in loads in <2 seconds
- ✅ Green padlock (valid SSL)
- ✅ All subdomains accessible (www, api, automator)
- ✅ No 502 or 504 errors

**Functionality**:
- ✅ Website navigation works
- ✅ API endpoints return valid JSON
- ✅ n8n dashboard accessible
- ✅ AI features respond (if implemented)

**Security**:
- ✅ SSL Labs grade A or A+
- ✅ All traffic encrypted (HTTPS)
- ✅ No direct port exposure (all via tunnel)
- ✅ API keys not exposed in logs

---

## Conclusion

**Deployment completed successfully on January 27, 2026.**

The SPS Platform is now running in production with:
- Cloudflare CDN, DDoS protection, and SSL/TLS
- Secure tunnel connectivity (no exposed ports)
- Multi-container architecture with Docker
- AI-powered backend with multiple LLM providers
- Automated workflows via n8n
- Vector database for embeddings

**Live URLs**:
- Main Site: https://sukhi.in
- API: https://api.sukhi.in
- Automation: https://automator.sukhi.in

**Next Steps**:
1. Configure n8n workflows for automation
2. Set up monitoring and alerts
3. Implement backup schedule
4. Review and optimize performance
5. Add custom features as needed

For questions or issues, refer to the Troubleshooting section or container logs.

---

**Document Version**: 1.0  
**Last Updated**: January 27, 2026  
**Author**: Deployment team  
**Server**: Hostinger KVM 4 (srv1298636)  
**Status**: ✅ Production Active
