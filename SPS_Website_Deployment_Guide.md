# 🚀 SPS Website Deployment Guide: The "Oracle" System

**Version:** 2.0 (Cloudflare Zero Trust Edition)  
**Objective:** Deploy the SPS Intelligence Platform to a Hostinger VPS behind a Cloudflare Tunnel.

---

## 🛡️ Part 1: Cloudflare Setup (Do this first)

1.  **Create Account:** Go to [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) and sign up (Free).
2.  **Add Domain:** Add your domain (`sps-security.com`) to Cloudflare and update your Nameservers on Hostinger/GoDaddy.
3.  **Create Tunnel:**
    *   Go to **Networks** > **Tunnels**.
    *   Click **Create a Tunnel**.
    *   Name it: `sps-vps`.
    *   Choose environment: **Docker**.
    *   **COPY THE TOKEN:** It will look like `eyJhIjoi...`. You need this for the next step.

4.  **Configure Public Hostnames (Routing):**
    In the Tunnel settings, add these Public Hostnames:

    | Domain | Service | URL |
    | :--- | :--- | :--- |
    | `sps-security.com` | HTTP | `sps-website:4321` |
    | `www.sps-security.com` | HTTP | `sps-website:4321` |
    | `api.sps-security.com` | HTTP | `sps-brain:8000` |
    | `automator.sps-security.com` | HTTP | `n8n:5678` |

    *Note: "Service URL" refers to the Docker container names.*

---

## 🛒 Part 2: The Server

1.  **Hostinger VPS:** KVM 2 Plan (Ubuntu 22.04).
2.  **Connect:** `ssh root@YOUR_IP`.

---

## 🏗️ Part 3: Installation

**Step 1: Install Docker**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

**Step 2: Get Code**
```bash
git clone https://github.com/YOUR_USERNAME/new_SPS_Website.git sps-platform
cd sps-platform
```

**Step 3: Secrets**
```bash
nano .env
```
Paste this (Right-click to paste):
```env
GOOGLE_API_KEY=AIzaSy... (Your Gemini Key)
TUNNEL_TOKEN=eyJhIjoi... (Your Cloudflare Tunnel Token)
```
*Save: Ctrl+O, Enter, Ctrl+X*

---

## 🚀 Part 4: Launch

Run the deployment script:
```bash
./deploy.sh
```

**Verification:**
Go to `https://sps-security.com`. It should load instantly with SSL (Lock icon) provided by Cloudflare.

---

## 🔒 Part 5: Security Hardening (Optional but Recommended)

In Cloudflare Zero Trust Dashboard -> **Access** -> **Applications**:
1.  **Add an Application:** Self-hosted.
2.  **Domain:** `automator.sps-security.com`.
3.  **Policy:** Allow only `your-email@gmail.com`.

**Result:** Now, nobody can even *see* your n8n login page without authenticating via Cloudflare first. Total invincibility.