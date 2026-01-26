# 🚀 SPS Website Deployment Guide

**Your Domain:** `sukhi.in`  
**Your Server:** Hostinger KVM 4  
**Time Required:** ~45 minutes

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:
- [ ] Hostinger KVM 4 account with root password
- [ ] Access to wherever you bought `sukhi.in` (registrar)
- [ ] Your code pushed to GitHub
- [ ] A Google/Gemini API key

---

# PHASE 1: CLOUDFLARE SETUP
*This replaces AWS as your DNS provider and gives you free SSL + security*

---

## Step 1.1: Create Cloudflare Account

1. Open your browser and go to: **https://dash.cloudflare.com/sign-up**
2. Enter your email and create a password
3. Click **Create Account**
4. You'll be taken to the dashboard

---

## Step 1.2: Add Your Domain to Cloudflare

1. In Cloudflare dashboard, click **"Add a site"** (big blue button)
2. Type: `sukhi.in`
3. Click **Add site**
4. Select the **FREE** plan at the bottom, click **Continue**
5. Cloudflare will scan your existing DNS records - click **Continue**
6. You'll see **two nameservers** that look like:
   ```
   ada.ns.cloudflare.com
   bob.ns.cloudflare.com
   ```
   **WRITE THESE DOWN** - you need them for the next step

---

## Step 1.3: Point Your Domain to Cloudflare

Since `sukhi.in` is currently on AWS Route 53, you need to change the nameservers.

### If you bought the domain on AWS:
1. Go to **AWS Console** → **Route 53** → **Registered domains**
2. Click on `sukhi.in`
3. Click **Add or edit name servers**
4. Delete the AWS nameservers
5. Add the TWO Cloudflare nameservers you wrote down
6. Click **Update**

### If you bought it elsewhere (GoDaddy, Namecheap, etc.):
1. Log into your registrar
2. Find "DNS Settings" or "Nameservers"
3. Change to "Custom nameservers"
4. Enter the two Cloudflare nameservers
5. Save

⏱️ **Wait time:** This can take 5 minutes to 24 hours. Cloudflare will email you when it's active.

---

## Step 1.4: Create the Cloudflare Tunnel

This creates a secure connection between Cloudflare and your server. **No ports need to be opened on your server.**

1. In Cloudflare dashboard, click **Zero Trust** (left sidebar)
   - If first time, it will ask you to set up - use the Free plan
2. Click **Networks** → **Tunnels**
3. Click **Create a tunnel**
4. Select **Cloudflared** → **Next**
5. Name your tunnel: `sps-server`
6. Click **Save tunnel**
7. Choose environment: **Docker**
8. You'll see a command with a long token that looks like:
   ```
   docker run cloudflare/cloudflared:latest tunnel --no-autoupdate run --token eyJhIjoiNjQ...
   ```
   **COPY THE TOKEN** (the part after `--token`, it's very long)
   - It starts with `eyJhIjoi` and is ~200 characters
   - Save this somewhere safe - you'll need it later

---

## Step 1.5: Configure Public Hostnames (Tell Cloudflare Where to Route Traffic)

Still in the tunnel setup:

1. Click **Next** after copying the token
2. You'll see "Public Hostnames" - click **Add a public hostname**
3. Add these FOUR entries (click "Add public hostname" after each one):

| Subdomain | Domain | Type | URL |
|-----------|--------|------|-----|
| *(leave empty)* | `sukhi.in` | HTTP | `sps-website:4321` |
| `www` | `sukhi.in` | HTTP | `sps-website:4321` |
| `api` | `sukhi.in` | HTTP | `sps-brain:8000` |
| `automator` | `sukhi.in` | HTTP | `n8n:5678` |

4. Click **Save tunnel**

✅ **Cloudflare setup complete!**

---

# PHASE 2: SERVER SETUP
*Setting up your Hostinger KVM*

---

## Step 2.1: Get Your Server's IP Address

1. Log into **Hostinger** → **VPS** section
2. Click on your KVM 4 server
3. Find and copy your **IP Address** (looks like `123.456.78.90`)

---

## Step 2.2: Connect to Your Server

Open **Terminal** on your Mac (press `Cmd + Space`, type "Terminal", press Enter)

Type this command (replace with YOUR IP):
```bash
ssh root@YOUR_IP_ADDRESS
```

Example:
```bash
ssh root@123.456.78.90
```

It will ask:
```
Are you sure you want to continue connecting (yes/no)?
```
Type: `yes` and press Enter

Then enter your **root password** (the one you created on Hostinger)

⚠️ **Note:** When typing the password, you won't see any characters - that's normal. Just type it and press Enter.

You're now connected when you see something like:
```
root@vps-12345:~#
```

---

## Step 2.3: Install Docker

Copy and paste this ENTIRE command (paste with `Cmd+V` or right-click):
```bash
curl -fsSL https://get.docker.com | sh
```

Wait ~2 minutes for it to finish. You'll see a lot of text scrolling.

When done, verify it worked:
```bash
docker --version
```
You should see something like: `Docker version 24.0.7`

---

## Step 2.4: Get Your Code

Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username:
```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/new_SPS_Website.git sps-platform
```

Then enter the folder:
```bash
cd sps-platform
```

---

## Step 2.5: Create Your Secrets File

This creates a file to store your API keys and tokens:
```bash
nano .env
```

This opens a text editor. Type these lines (replace with YOUR actual values):
```
GEMINI_API_KEY=your-gemini-api-key-here
GOOGLE_API_KEY=your-google-api-key-here
TUNNEL_TOKEN=eyJhIjoiNjQ...your-long-cloudflare-token-here
```

To save and exit:
1. Press `Ctrl + O` (that's the letter O, not zero)
2. Press `Enter` to confirm the filename
3. Press `Ctrl + X` to exit

---

# PHASE 3: LAUNCH
*Start your website*

---

## Step 3.1: Build and Start Everything

Run this command:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

This will take 5-10 minutes the first time. You'll see lots of download progress.

---

## Step 3.2: Verify Everything is Running

```bash
docker ps
```

You should see 5 containers running:
- `sps-brain`
- `sps-website`
- `n8n`
- `sps-chroma`
- `cloudflared`

---

## Step 3.3: Test Your Website!

Open your browser and go to:
- **https://sukhi.in** - Your website
- **https://api.sukhi.in** - Your API
- **https://automator.sukhi.in** - Your n8n automation panel

🎉 **You should see your website with a green lock icon (SSL)!**

---

# PHASE 4: SECURITY (Optional but Recommended)

---

## Step 4.1: Protect Your n8n Dashboard

1. Go to **Cloudflare Zero Trust** → **Access** → **Applications**
2. Click **Add an application**
3. Choose **Self-hosted**
4. Fill in:
   - Application name: `n8n Admin`
   - Session duration: `24 hours`
   - Domain: `automator.sukhi.in`
5. Click **Next**
6. Add a policy:
   - Policy name: `Only Me`
   - Include: `Emails` → your email (e.g., `amar.sukhi@spsindia.com`)
7. Click **Save**

Now only YOU can access the n8n login page!

---

# 🆘 TROUBLESHOOTING

## "Connection refused" when trying to SSH
- Check if SSH is enabled in Hostinger's VPS panel
- Make sure you're using the correct IP address

## Website not loading after deployment
- DNS propagation can take up to 24 hours
- Check if all containers are running: `docker ps`
- Check logs: `docker logs sps-website`

## "Permission denied" errors
- Make sure you're logged in as `root`

---

# 📞 Quick Reference

| What | Command |
|------|---------|
| Start everything | `docker compose -f docker-compose.prod.yml up -d` |
| Stop everything | `docker compose -f docker-compose.prod.yml down` |
| See running containers | `docker ps` |
| View website logs | `docker logs sps-website` |
| View API logs | `docker logs sps-brain` |
| Restart everything | `docker compose -f docker-compose.prod.yml restart` |
| Update from GitHub | `git pull && docker compose -f docker-compose.prod.yml up -d --build` |