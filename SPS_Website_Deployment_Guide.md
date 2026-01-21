# 🚀 SPS Website Deployment Guide: The "Oracle" System

**Version:** 1.0  
**Target Audience:** Non-Technical / Semi-Technical Operators  
**Objective:** Deploy the SPS Intelligence Platform to a Hostinger VPS and learn how to update it securely.

---

## 📖 Introduction: What are we building?

Your system is not just a standard website. It is a "Headless Intelligence Platform" consisting of three parts that run together:

1.  **The Face (Website):** This is what the public sees (Port 4321).
2.  **The Brain (Python API):** This does the math, risk calculations, and fact-checking (Port 8000).
3.  **The Nervous System (n8n):** This is the robot that patrols the internet for news and alerts you (Port 5678).

To run all three at once, we use a technology called **Docker**. This guide explains how to put that Docker "container" onto a Hostinger server.

---

## 🛒 Part 1: Purchasing the Server

You cannot use standard "Shared Hosting" (the cheap $2.99 WordPress plans) for this. You need a **VPS (Virtual Private Server)**.

1.  Log in to **Hostinger**.
2.  Go to **VPS** -> **Order Now**.
3.  **Select Plan:** **KVM 2** (Recommended).
    *   *Why?* We need 4GB of RAM to run the AI Brain and Automation tools simultaneously.
4.  **Operating System:** Select **Ubuntu 22.04 64bit**.
5.  Complete the purchase. Hostinger will give you an **IP Address** (e.g., `192.168.1.50`) and a **Root Password**. Write these down!

---

## 🛠️ Part 2: Connecting to Your Server

You will control your server using a "Terminal" on your computer. It looks like a hacker movie, but it's just typing commands.

1.  Open **Terminal** (Mac) or **Command Prompt** (Windows).
2.  Type the following command and hit Enter:
    ```bash
    ssh root@YOUR_SERVER_IP_ADDRESS
    ```
    *(Replace `YOUR_SERVER_IP_ADDRESS` with the number Hostinger gave you).*
3.  It will ask for your password. Type the **Root Password** you created.
    *   *Note: You won't see the cursor move while typing the password. This is normal security. Just type it and hit Enter.*

**Success:** If you see a welcome message like `root@ubuntu:~#`, you are inside your server.

---

## 🏗️ Part 3: Installing the Engine (One-Time Setup)

We need to install **Docker**. This is the engine that runs your code.

**Copy and paste these commands into your server terminal one by one:**

**Step 1: Install Docker**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

**Step 2: Get Your Code**
We will download your code from GitHub.
```bash
# 1. Clone the repository (Replace URL with your actual GitHub URL)
git clone https://github.com/YOUR_USERNAME/new_SPS_Website.git sps-platform

# 2. Enter the project folder
cd sps-platform
```

**Step 3: Add Your Secrets**
We need to tell the server your API keys (Google/Gemini).
```bash
# Open a text editor
nano .env
```

A blank screen will open. Paste your keys like this:
```env
GOOGLE_API_KEY=AIzaSyD2bfD6... (Paste your real key here)
```

**To Save & Exit:**
1.  Press `Ctrl + O` (Letter O) then `Enter` (to save).
2.  Press `Ctrl + X` (to exit).

---

## 🚀 Part 4: Launching the Oracle

Now we turn the key.

Run this command inside the `sps-platform` folder:
```bash
./deploy.sh
```

**What will happen:**
1.  The screen will scroll lots of text (Building containers...).
2.  This might take 2-3 minutes the first time.
3.  Eventually, it will stop and say **"Done"**.

**Verify it works:**
Open your browser and type your server's IP address:
*   **Website:** `http://YOUR_IP:4321` (e.g., `http://192.168.1.50:4321`)
*   **Automation:** `http://YOUR_IP:5678`
*   **Brain:** `http://YOUR_IP:8000/health`

---

## 🔄 Part 5: How to Make Changes (The Daily Loop)

You **never** edit code directly on the server. You edit on your laptop, then "push" it to the server.

### Step 1: Edit on Your Laptop 💻
1.  Open the code on your computer.
2.  Make your changes (e.g., update the Home Page text, change a color).
3.  Test it locally (`npm run dev`).

### Step 2: Save to Cloud ☁️
Open your local terminal and save the changes to GitHub:
```bash
git add .
git commit -m "Updated homepage text"
git push origin main
```

### Step 3: Update the Server 🚀
1.  Connect to your server: `ssh root@YOUR_IP`
2.  Go to the folder: `cd sps-platform`
3.  Run the magic script:
    ```bash
    ./deploy.sh
    ```

**That's it!** The script will automatically:
1.  Download your new code from GitHub.
2.  Rebuild only the parts that changed.
3.  Restart the website instantly.

---

## 🆘 Troubleshooting

**Q: The deployment failed!**
A: Check if you are in the right folder. Type `ls` and make sure you see `deploy.sh`. If not, type `cd sps-platform`.

**Q: I changed the Python code but nothing happened.**
A: The Python "Brain" takes longer to rebuild than the website. Wait 1 minute after deploying.

**Q: I want to use a real domain name (sps-security.com) instead of an IP.**
A: This requires setting up "Nginx Proxy Manager" or pointing your DNS A-Record to this IP. For now, focus on getting the IP version working perfectly.

**Q: How do I see the logs?**
A: Run this command on the server: `docker compose -f docker-compose.prod.yml logs -f` (Press `Ctrl + C` to stop watching).
