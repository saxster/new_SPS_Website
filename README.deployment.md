# SPS: The Security Intelligence Platform

## 🚀 Deployment Guide (Hostinger VPS)

### Initial Setup
1. SSH into your server: `ssh root@<YOUR_IP>`
2. Clone repo: `git clone <YOUR_REPO_URL> sps-platform`
3. Enter folder: `cd sps-platform`
4. Setup Env: `cp .env.example .env` (Add your API Keys)

### How to Update (The Loop)
1. **Local:** Make changes and `git push`.
2. **Server:** SSH in and run:
   ```bash
   cd sps-platform
   ./deploy.sh
   ```

### Architecture
- **Port 4321:** Website (Astro)
- **Port 8000:** Brain API (FastAPI)
- **Port 5678:** Automation (n8n)

### Local Development
```bash
# Start everything
docker-compose up
```
