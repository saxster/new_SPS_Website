# 🚀 The Server Farm: A Guide to Hosting Multiple Domains on a Single KVM Instance

**Version:** 1.0  
**Objective:** To understand the concept of "Virtual Hosting" and learn how to run multiple, completely separate websites on your single Hostinger KVM VPS.

---

## 📖 Part 1: The Core Concept - Your VPS is a Computer

It is crucial to stop thinking of your Hostinger KVM plan as "a website." **Your VPS is a full computer** that you are renting in a data center. It happens to be running Linux (Ubuntu 22.04), but it is a computer nonetheless.

Think about your own laptop or desktop:
*   Can it only run one application at a time? No.
*   Can it only show one website in the browser at a time? No.

Your VPS is the same. It has a single "address" on the internet (its IP Address), but it can run dozens of applications (websites, databases, AI models) simultaneously, limited only by its CPU and RAM.

**Analogy: The Apartment Building**
*   **Your KVM VPS** is an entire apartment building.
*   **The IP Address** is the building's street address (e.g., `123 Main Street`).
*   **Each Domain Name** (`sps-security.com`, `sukhi.in`) is a resident living in a specific apartment.
*   **Each Website's Code** is an "apartment" (a Docker Container).

When a visitor wants to see `sukhi.in`, their request goes to `123 Main Street`. But how does it get to the right apartment?

---

## ⚙️ Part 2: The Magic Behind It - The "Traffic Cop" (Reverse Proxy)

This is where the magic happens. A special piece of software acts as the building's **Doorman** or **Traffic Cop**. In our setup, this is **Cloudflare Tunnel**.

Every request that comes to your server has a hidden piece of information called a **Host Header**. It tells the server *which domain* the visitor is trying to reach.

Here is the flow:
1.  A user in London types `https://sukhi.in` into their browser.
2.  Their request travels across the internet to the **Cloudflare Network**.
3.  Cloudflare sends it down the secure **Tunnel** to your VPS. The request's "envelope" has the `Host: sukhi.in` header written on it.
4.  The `cloudflared` container on your VPS acts as the Traffic Cop. It reads the envelope:
    *   "Ah, this is for `sukhi.in`. According to my rules, I need to send this person to the `sukhi-website` container."
5.  Another user requests `sps-security.com`. The Traffic Cop reads the envelope:
    *   "This one is for `sps-security.com`. I'll send them to the `sps-website` container."

This process is called **Virtual Hosting**. One server, one IP address, but it *virtually hosts* many different sites.

---

## 🏗️ Part 3: A Practical Guide - Adding `sukhi.in` to Your Server

Let's assume you've built a second, simple website for `sukhi.in` and it also has a `Dockerfile`.

### Step 1: Organize Your Server
On your Hostinger VPS, you should have a clean folder structure.
```
/root/
└── sps-platform/       # <-- Your current project
    ├── docker-compose.prod.yml
    ├── agent_backend/
    └── website/
```
Now, you will add the new project alongside it:
```bash
# Go to your root directory
cd /root

# Clone the new project from GitHub
git clone https://github.com/your-username/sukhi-website.git
```
Your structure will now look like this:
```
/root/
├── sps-platform/
└── sukhi-website/
    ├── Dockerfile
    └── src/
```

### Step 2: Update Your Master Docker Compose File
Instead of having multiple `docker-compose` files, it's easier for a beginner to have **one master file** that controls everything. We will edit your `sps-platform/docker-compose.prod.yml` to also launch the new site.

Open the file on your server:
```bash
nano /root/sps-platform/docker-compose.prod.yml
```
Add the new website service to the **bottom** of the file:
```yaml
services:
  # ... all your existing services (sps-brain, sps-website, n8n, etc.)

  # --- ADD THIS NEW SERVICE ---
  sukhi-website:
    build:
      context: /root/sukhi-website  # Absolute path to the new project
    container_name: sukhi-website
    expose:
      - "3000" # Let's say this site runs on port 3000 internally
    restart: unless-stopped
    networks:
      - sps-network # Use the SAME network as your other services
```
*Save and Exit (Ctrl+O, Enter, Ctrl+X).*

### Step 3: Tell Cloudflare About the New Site
1.  Go to your **Cloudflare Dashboard**.
2.  Navigate to **Networks** -> **Tunnels**.
3.  Click on your `sps-vps` tunnel and then **Configure**.
4.  Go to the **Public Hostnames** tab.
5.  Click **Add a public hostname**.
    *   **Public Hostname:** `sukhi.in`
    *   **Service:** `HTTP`
    *   **URL:** `sukhi-website:3000` (The container name and internal port we just defined).
6.  Click **Save hostname**.

### Step 4: Deploy the New Stack
Now, from your `sps-platform` directory, run the deploy command. It will read the updated master file, build your new site, and launch it.
```bash
cd /root/sps-platform
./deploy.sh
```
The script will now build and launch both `sps-website` AND `sukhi-website`.

---

## 💡 The Power of KVM 8

You have a very powerful 8-CPU server. This is like owning a large apartment building. You can easily host:
*   Your two main corporate websites (`sps-security.com`, `sukhi.in`).
*   A Ghost blog for your personal writing.
*   A private WordPress instance for a family member.
*   A test environment for a new product.

Each of these would be a new service in your master `docker-compose.prod.yml` file and a new hostname in your Cloudflare Tunnel. You save a huge amount of money by consolidating everything onto one powerful, secure server.
