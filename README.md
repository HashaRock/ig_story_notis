# ig-story-notis

Polls an Instagram account for new Stories and forwards each one to a Discord channel — image/video embed, timestamp, and a direct story link — within 1–5 minutes of posting.

**Stack:** Python 3.12 · instaloader · Discord webhooks · Docker Compose

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Create a Discord Webhook](#2-create-a-discord-webhook)
3. [Set Up a Google Cloud VM (Free Tier)](#3-set-up-a-google-cloud-vm-free-tier)
4. [Install Docker on the VPS](#4-install-docker-on-the-vps)
5. [Deploy the App](#5-deploy-the-app)
6. [First-Time Instagram Login](#6-first-time-instagram-login)
7. [Start the Daemon](#7-start-the-daemon)
8. [Day-to-Day Commands (Makefile)](#8-day-to-day-commands-makefile)
9. [Maintenance & Troubleshooting](#9-maintenance--troubleshooting)

---

## 1. Prerequisites

Before you start, have the following ready:

| Item | Notes |
|---|---|
| **Burner Instagram account** | A separate IG account used only by this bot. Do **not** use your personal account. |
| **@zero2sudo followed** | Log into the burner account on your phone and follow @zero2sudo before deploying. Stories from accounts you don't follow won't appear. |
| **Google Cloud account** | Free at console.cloud.google.com. Requires a credit card for verification but the Always Free e2-micro is not charged. |
| **Discord server** with a dedicated channel | e.g. `#swe-job-alerts` |

---

## 2. Create a Discord Webhook

A webhook is a simple URL — no bot, no OAuth, no permissions setup.

1. Open Discord and go to the channel you want notifications in (e.g. `#swe-job-alerts`).
2. Click the gear icon next to the channel name → **Edit Channel**.
3. Select **Integrations** in the left sidebar.
4. Click **Webhooks** → **New Webhook**.
5. Give it a name (e.g. `IG Story Bot`) and optionally upload an avatar.
6. Click **Copy Webhook URL** — it looks like:
   ```
   https://discord.com/api/webhooks/1234567890123456789/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
7. Keep this URL private — anyone with it can post to your channel.

Paste this URL into your `.env` as `DISCORD_WEBHOOK_URL` in a later step.

---

## 3. Set Up a Google Cloud VM (Free Tier)

GCP's Always Free tier includes one **e2-micro** VM per month permanently — no trial, no expiry. It comes with 1 GB of outbound data transfer per month (to most destinations), which is more than enough for this bot (~44 MB/month).

> **Region constraint**: the free e2-micro is only available in `us-central1`, `us-east1`, or `us-west1`. Pick whichever is closest to you.

### 3a. Create an account

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and sign in with a Google account.
2. Create a new project (e.g. `ig-story-bot`) — or use an existing one.
3. Enable billing on the project (required even for free tier — you will not be charged for Always Free resources).

### 3b. Launch a VM instance

1. In the console, open the **navigation menu** (hamburger top-left) → **Compute Engine** → **VM instances**.
2. Click **Create instance**.
3. **Name**: e.g. `ig-story-bot`
4. **Region**: choose `us-central1`, `us-east1`, or `us-west1` (required for free tier). Zone within the region doesn't matter.
5. **Machine configuration**:
   - Series: **E2**
   - Machine type: **e2-micro** (2 vCPU, 1 GB RAM) — this is the Always Free machine type.
6. **Boot disk**: click **Change**:
   - Operating system: **Ubuntu**
   - Version: **Ubuntu 22.04 LTS**
   - Boot disk type: **Standard persistent disk**
   - Size: `30 GB` (the free tier includes 30 GB standard disk)
   - Click **Select**.
7. **Firewall**: check both **Allow HTTP traffic** and **Allow HTTPS traffic** (not strictly required for this bot, but useful if you ever want to add a web UI).
8. **SSH keys** (under *Advanced options* → *Security* → *Manage access*):
   - Click **Add item** and paste your public key (`~/.ssh/id_rsa.pub` or `~/.ssh/id_ed25519.pub`).
   - The username embedded in the key becomes your SSH login name.
   - If you don't have a key pair, generate one locally first: `ssh-keygen -t ed25519`
9. Click **Create**. The instance status will change to a green checkmark within ~30 seconds.
10. Copy the **External IP** from the VM instances list.

### 3c. Open port 22 (SSH) in the firewall

GCP's default VPC already allows SSH (port 22) from any IP via the `default-allow-ssh` firewall rule. No changes needed.

If you ever can't SSH in, verify the rule exists:

**Console → VPC network → Firewall → default-allow-ssh**

It should allow TCP port 22 from source `0.0.0.0/0`.

### 3d. SSH into the VM

```bash
ssh <YOUR_USERNAME>@<YOUR_EXTERNAL_IP>
```

Replace `<YOUR_USERNAME>` with the username embedded in your SSH public key (usually the output of `whoami` on your local machine). On first connection, type `yes` to accept the host fingerprint.

Alternatively, use the **SSH** button in the GCP console to open a browser-based terminal without needing a local key.

---

## 4. Install Docker on the VPS

Run all of the following commands after SSH-ing into the VPS.

### 4a. Update packages

```bash
sudo apt-get update && sudo apt-get upgrade -y
```

### 4b. Install Docker (official method)

```bash
# Install prerequisites
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker's GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the Docker apt repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine + Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 4c. Allow your user to run Docker without sudo

```bash
sudo usermod -aG docker $USER
newgrp docker          # apply group change without logging out
```

### 4d. Verify

```bash
docker --version        # e.g. Docker version 26.x.x
docker compose version  # e.g. Docker Compose version v2.x.x
```

### 4e. Install make

```bash
sudo apt-get install -y make
```

---

## 5. Deploy the App

### 5a. Copy the project to the VPS

**Option A — Git (recommended):**
```bash
# On the VPS
git clone https://github.com/YOUR_USERNAME/ig_story_notis.git
cd ig_story_notis
```

**Option B — scp from your local machine:**
```bash
# On your local machine
scp -r /path/to/ig_story_notis <YOUR_USERNAME>@<YOUR_EXTERNAL_IP>:~/ig_story_notis
```
Then SSH in and `cd ~/ig_story_notis`.

### 5b. Create your `.env` file

```bash
cp .env.example .env
nano .env
```

Fill in every value:

```
IG_USERNAME=your_burner_ig_username
IG_PASSWORD=your_burner_ig_password
IG_TARGET_ACCOUNT=zero2sudo
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
POLL_INTERVAL_SECONDS=120
DATA_DIR=./data
LOG_LEVEL=INFO
```

Save and exit nano: `Ctrl+O`, `Enter`, `Ctrl+X`.

### 5c. Build the Docker image

```bash
make build
```

This pulls `python:3.12-slim` and installs the three dependencies. Takes ~30 seconds on first run.

---

## 6. First-Time Instagram Login

Instagram may trigger a checkpoint (email/SMS verification) the first time you log in from a new IP. This step handles it interactively so the session is saved before the daemon starts.

```bash
make login
```

**What to expect:**

- **Normal case:** You'll see `Session saved successfully.` and be returned to the shell.
- **Checkpoint / two-factor case:** instaloader will print a prompt asking for the code sent to your email or phone. Enter it and the session will be saved.
- **"Please wait a few minutes" error:** Instagram is rate-limiting the login. Wait 5–10 minutes and run `make login` again.

Once the session is saved it persists in `./data/ig_session` and survives container restarts. You should not need to re-run this unless the session expires (see [Maintenance](#9-maintenance--troubleshooting)).

---

## 7. Start the Daemon

```bash
make up
```

The container starts in the background with `restart: unless-stopped` — it will automatically restart after crashes or VPS reboots.

Check that it's running:

```bash
make status
```

Watch the live logs:

```bash
make logs
```

You should see lines like:
```
2026-04-21T18:00:01 [INFO] ig_client: Loaded existing Instagram session from file.
2026-04-21T18:00:03 [INFO] poller: Polling @zero2sudo every 120s. Press Ctrl+C to stop.
2026-04-21T18:00:05 [DEBUG] ig_client: Fetched 3 story items from @zero2sudo.
```

When a new story is detected:
```
2026-04-21T18:02:06 [INFO] poller: Notified: story 3012345678901234567.
```

And a Discord embed will appear in your channel with the story image/video, timestamp, and a link.

---

## 8. Day-to-Day Commands (Makefile)

All common operations are wrapped in `make` targets so you never need to remember raw Docker commands.

| Command | What it does |
|---|---|
| `make build` | Build (or rebuild) the Docker image |
| `make up` | Start the daemon in the background |
| `make down` | Stop the daemon |
| `make restart` | Restart without rebuilding (picks up `.env` changes) |
| `make logs` | Tail live container logs |
| `make status` | Show container running state |
| `make login` | Interactive Instagram login — saves session to `./data/` |
| `make refresh` | Force re-authenticate and overwrite the saved session |
| `make shell` | Open a bash shell inside the container for debugging |
| `make clean` | Remove the image and delete all persisted data (**destructive**) |

---

## 9. Maintenance & Troubleshooting

### Session expiry

Instagram sessions typically last 60–90 days. When the session expires you'll see log lines like:
```
[WARNING] ig_client: Session expired — re-authenticating.
```
The poller will attempt an automatic refresh. If it fails (e.g. Instagram demands a checkpoint again):

```bash
make down
rm data/ig_session
make login
make up
```

### No stories showing up

1. Confirm the burner account follows @zero2sudo — stories are invisible to non-followers.
2. Check `make logs` for any errors.
3. Verify @zero2sudo has active stories posted in the last 24 hours.

### Discord embed shows a broken image

CDN-signed story image URLs from Instagram expire after ~6 hours. Discord caches the image when the embed first renders, so this only affects you if you view a very old notification. Not fixable — it's an Instagram limitation.

### Rebuilding after code changes

```bash
make down
make build
make up
```

If you only changed `.env`, a `make restart` (no rebuild) is sufficient.

### VPS reboots

`restart: unless-stopped` means Docker will bring the container back up automatically after any reboot. No action needed.

### Checking GCP VM resource usage

```bash
# CPU and memory
top

# Disk
df -h

# Docker image/container sizes
docker system df
```

The container uses roughly 200 MB disk and under 100 MB RAM at runtime — well within the e2-micro Always Free limits (30 GB disk, 1 GB RAM).

To monitor outbound data transfer against your 1 GB/month free quota, go to **Console → Compute Engine → VM instances → your instance → Observability** and check the network egress metric. At ~44 MB/month this bot uses about 4% of the free allowance.
