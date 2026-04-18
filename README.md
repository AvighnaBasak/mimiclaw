<p align="center">
  <a href="https://github.com/AvighnaBasak/mimiclaw">
    <img src="dashboard/static/mimiclaw_logo_long.png" alt="MimiClaw" width="400" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/node.js-18+-339933?style=for-the-badge&logo=node.js&logoColor=white" alt="Node.js" />
  <img src="https://img.shields.io/badge/electron-29-47848F?style=for-the-badge&logo=electron&logoColor=white" alt="Electron" />
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue?style=for-the-badge" alt="License" />
</p>

<p align="center"><b>Personal AI-powered Telegram assistant for Google Classroom.</b></p>

MimiClaw monitors your Google Classroom, automatically completes assignments using AI, uploads finished work to Google Drive, and sends everything back to you on Telegram. It comes with an Electron desktop dashboard for tracking all your assignments at a glance.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Python Dependencies](#2-python-dependencies)
  - [3. Environment Variables](#3-environment-variables)
  - [4. Google Cloud Setup](#4-google-cloud-setup)
  - [5. Google OAuth Authentication](#5-google-oauth-authentication)
  - [6. Telegram Bot Setup](#6-telegram-bot-setup)
  - [7. AI API Keys](#7-ai-api-keys)
  - [8. Dashboard Setup (Optional)](#8-dashboard-setup-optional)
- [Usage](#usage)
  - [Starting the Bot](#starting-the-bot)
  - [Telegram Commands](#telegram-commands)
  - [Assignment Workflow](#assignment-workflow)
  - [Launching the Dashboard](#launching-the-dashboard)
- [Project Structure](#project-structure)
- [AI Model Configuration](#ai-model-configuration)
- [Scheduler Jobs](#scheduler-jobs)
- [Database Schema](#database-schema)
- [Hosting on Railway (Free Tier)](#hosting-on-railway-free-tier)
  - [Step 1: Prepare the Repository](#step-1-prepare-the-repository)
  - [Step 2: Create a Railway Project](#step-2-create-a-railway-project)
  - [Step 3: Configure Environment Variables](#step-3-configure-environment-variables)
  - [Step 4: Add a Procfile](#step-4-add-a-procfile)
  - [Step 5: Handle Google OAuth Tokens](#step-5-handle-google-oauth-tokens)
  - [Step 6: Deploy](#step-6-deploy)
  - [Step 7: Persistent Storage](#step-7-persistent-storage)
  - [Monitoring](#monitoring)
- [Hosting Alternatives](#hosting-alternatives)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)
- [License](#license)

---

## Features

- **Automatic Classroom Monitoring** — Polls Google Classroom every 15 minutes for new assignments and notifies you on Telegram.
- **AI-Powered Assignment Completion** — Reads assignment descriptions and attached PDFs, determines the required deliverables (e.g., `server.c` and `client.c`), generates each file individually, and produces clean source code or written work with no fluff.
- **Multi-File Support** — If an assignment requires multiple files, each is generated in a separate AI call with its own full token budget, ensuring nothing gets truncated.
- **Correct File Formats** — AI detects the required file type from the assignment (`.c`, `.py`, `.java`, `.cpp`, `.txt`, etc.) and uses the correct extension.
- **Google Drive Upload** — Completed files are organized into folders by course and assignment on your Google Drive.
- **Telegram Delivery** — Every generated file is sent back to you as a document in the Telegram chat, along with Drive links.
- **Custom Prompts** — Before completing an assignment, the bot asks if you have specific instructions (e.g., "write in a human tone", "keep it under 500 words", "use APA format").
- **PDF Attachment Handling** — Downloads and sends assignment PDF attachments to you in Telegram, and extracts their text for AI context.
- **Smart Status Tracking** — Assignments stay "pending" until actually submitted on Google Classroom. The bot checks submission states every 15 minutes.
- **Drive Link Validation** — If you delete output files/folders from Drive, the dashboard automatically detects this and removes dead links.
- **Due Date Reminders** — Daily reminders at 9 AM for upcoming assignments that haven't been completed.
- **Electron Desktop Dashboard** — A clean, modern desktop app showing all assignments, stats, pending work, completed files with Drive links, and reminders.
- **Multi-Model AI Fallback** — Primary model (Gemma 4 via Gemini API) with automatic fallback to Groq models if the primary fails.
- **Single-User Security** — Only responds to your Telegram account; all other users are silently ignored.

---

## Architecture

```
+------------------+       +------------------+       +------------------+
|   Telegram App   | <---> |     bot.py       | <---> |     ai.py        |
|   (Your Phone)   |       |  (Entry Point)   |       |  (AI Client)     |
+------------------+       +--------+---------+       +--+----------+----+
                                    |                    |          |
                            +-------+-------+      Gemini API   Groq API
                            |               |
                    +-------+----+   +------+-------+
                    | classroom  |   |   drive.py   |
                    |    .py     |   | (Upload/DL)  |
                    +-------+----+   +------+-------+
                            |               |
                    Google Classroom   Google Drive
                        API               API
                            |               |
                    +-------+---------------+-------+
                    |          db.py                 |
                    |   (SQLAlchemy + SQLite)        |
                    +-------+-----------------------+
                            |
                    +-------+-------+
                    | db_bridge.py  |  <--- child_process --->  Electron Dashboard
                    | (JSON bridge) |                           (dashboard/)
                    +---------------+
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Bot Framework | python-telegram-bot 21.6 |
| AI Backend | Gemini API (Google AI Studio), Groq API |
| AI Models | Gemma 4 31B, GPT-OSS 120B, Qwen3 32B |
| Classroom API | google-api-python-client |
| Drive API | google-api-python-client |
| Database | SQLite via SQLAlchemy 2.0 |
| PDF Parsing | PyMuPDF (fitz) |
| Scheduling | APScheduler 3.10 |
| Dashboard | Electron 29 (Node.js) |
| Language | Python 3.10+, JavaScript |

---

## Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **Node.js 18+** — [Download](https://nodejs.org/) (only for the desktop dashboard)
- **Google Account** — With access to Google Classroom
- **Telegram Account** — To interact with the bot
- **API Keys** — Gemini (Google AI Studio) and Groq (free tier)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YourUsername/mimiclaw.git
cd mimiclaw
```

### 2. Python Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies installed:**
| Package | Purpose |
|---------|---------|
| `python-telegram-bot` | Telegram bot framework |
| `python-dotenv` | Load `.env` file |
| `sqlalchemy` | ORM for SQLite database |
| `google-api-python-client` | Google Classroom & Drive APIs |
| `google-auth-httplib2` | Google API authentication |
| `google-auth-oauthlib` | Google OAuth flow |
| `apscheduler` | Background job scheduling |
| `requests` | HTTP client for AI APIs |
| `pymupdf` | PDF text extraction |

### 3. Environment Variables

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ALLOWED_USER_ID=your_telegram_user_id
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
```

### 4. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the following APIs:
   - **Google Classroom API**
   - **Google Drive API**
4. Go to **APIs & Services > Credentials**
5. Click **Create Credentials > OAuth 2.0 Client ID**
6. Select **Desktop app** as the application type
7. Download the JSON file
8. Save it as `credentials/google_credentials.json`

```
mimiclaw/
  credentials/
    google_credentials.json   <-- place it here
```

> **Important:** When configuring the OAuth consent screen, add your Google account as a test user if the app is in "Testing" mode.

### 5. Google OAuth Authentication

Run the one-time setup script:

```bash
python setup_auth.py
```

This opens two browser windows:
1. **Google Classroom** — grants read access to courses, assignments, and submissions
2. **Google Drive** — grants read/write access for uploading completed work and reading attachments

Tokens are saved to:
- `credentials/token_classroom.json`
- `credentials/token_drive.json`

These tokens auto-refresh and don't need to be regenerated unless you revoke access.

### 6. Telegram Bot Setup

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts to create your bot
3. Copy the **bot token** and add it to `.env` as `TELEGRAM_BOT_TOKEN`
4. To find your Telegram user ID:
   - Search for **@userinfobot** on Telegram
   - Send it any message
   - It will reply with your user ID
5. Add your user ID to `.env` as `TELEGRAM_ALLOWED_USER_ID`

### 7. AI API Keys

**Gemini API (Primary — Google AI Studio):**
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Click **Get API Key**
3. Create a key and add it to `.env` as `GEMINI_API_KEY`

**Groq API (Fallback):**
1. Go to [Groq Console](https://console.groq.com/)
2. Sign up and create an API key
3. Add it to `.env` as `GROQ_API_KEY`

Both services offer free tiers sufficient for personal use.

### 8. Dashboard Setup (Optional)

The desktop dashboard requires Node.js:

```bash
cd dashboard
npm install
cd ..
```

---

## Usage

### Starting the Bot

```bash
python bot.py
```

The bot will:
- Connect to Telegram and start polling for messages
- Start the scheduler (Classroom polling every 15 min, reminders at 9 AM daily)
- Log all activity to the console

### Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and command list |
| `/help` | Same as `/start` |
| `/assignments` | List pending assignments with clickable buttons |
| `/check` | Poll Google Classroom immediately for new assignments |
| `/done <id>` | Manually mark an assignment as done |
| `/remind <text>` | Save a personal reminder |
| `/reminders` | List all saved reminders |
| `/drive` | Show recent files saved to Drive |

### Assignment Workflow

1. **Send `/assignments`** — the bot lists all pending assignments with inline buttons
2. **Tap an assignment** — the bot shows the full details (title, course, due date, description)
3. **Attachments are sent** — any PDF or file attachments from the assignment are sent as Telegram documents
4. **Custom prompt** — the bot asks: *"Do you have any specific instructions I should follow?"*
   - Reply with your instructions (e.g., "write it in a human tone", "focus on section 3")
   - Or send `none` to proceed without custom instructions
5. **AI generates files** — the bot:
   - Analyzes the assignment and plans what files are needed
   - Sends a message: *"Will generate 2 file(s): tftpclient.c, tftpserver.c"*
   - Generates each file individually with progress updates
   - Sends each file as a Telegram document as soon as it's ready
6. **Drive upload** — all files are uploaded to a structured Drive folder:
   ```
   MimiClaw Assignments/
     Computer Network Lab/
       File transfer application using UDP/
         tftpclient.c
         tftpserver.c
   ```
7. **Drive link** — the bot sends the folder link at the end
8. **Status stays pending** — the assignment remains "pending" until you actually submit it on Google Classroom

### Launching the Dashboard

```bash
python launch_dashboard.py
```

Or manually:

```bash
cd dashboard
npm start
```

The dashboard shows:
- **Stats** — total, pending, completed, overdue counts
- **Pending assignments** — sorted by due date with days-left indicators and Drive links
- **All assignments** — filterable table (All / Pending / Completed / Skipped)
- **Recently completed** — with file links to Drive
- **Reminders** — all saved reminders
- **Auto-refresh** — updates every 60 seconds

---

## Project Structure

```
mimiclaw/
  bot.py              # Telegram bot entry point — run this to start
  ai.py               # Multi-provider AI client with fallback chain
  classroom.py        # Google Classroom API client
  drive.py            # Google Drive API client (upload, download, validate)
  db.py               # SQLAlchemy models and query helpers (SQLite)
  db_bridge.py        # JSON bridge — Electron calls this to query the DB
  scheduler.py        # APScheduler jobs (polling, reminders, sync, cleanup)
  pdf_reader.py       # PDF text extraction via PyMuPDF
  setup_auth.py       # One-time Google OAuth browser flow
  launch_dashboard.py # Launches the Electron dashboard
  requirements.txt    # Python dependencies
  .env                # API keys and config (git-ignored)
  .gitignore          # Git ignore rules
  credentials/        # Google OAuth credentials and tokens (git-ignored)
  data/               # SQLite database (git-ignored, auto-created)
    mimiclaw.db
  dashboard/          # Electron desktop app
    main.js           # Electron main process
    preload.js        # Context bridge (IPC)
    renderer.js       # Frontend logic
    index.html        # Dashboard UI
    style.css         # Styles
    package.json      # Node.js dependencies
    static/           # Static assets (profile picture, etc.)
```

---

## AI Model Configuration

The AI client (`ai.py`) uses a fallback chain — if the primary model fails (timeout, rate limit, error), it automatically tries the next one:

| Priority | Model | Provider | Endpoint |
|----------|-------|----------|----------|
| 1 (Primary) | Gemma 4 31B IT | Google AI Studio (Gemini API) | `generativelanguage.googleapis.com` |
| 2 (Fallback) | GPT-OSS 120B | Groq | `api.groq.com` |
| 3 (Fallback) | Qwen3 32B | Groq | `api.groq.com` |

Both Gemini and Groq expose OpenAI-compatible `/chat/completions` endpoints, keeping the code clean.

**Assignment completion uses a two-step process:**
1. **Plan** — a lightweight call asks the AI to determine what files are needed and returns a JSON list of filenames with correct extensions
2. **Generate** — each file gets its own dedicated API call with a full 8192-token budget, ensuring multi-file assignments are never truncated

Thinking/reasoning tags (`<think>`, `<thought>`) are automatically stripped from model outputs.

---

## Scheduler Jobs

| Job | Interval | Description |
|-----|----------|-------------|
| `_poll_classroom` | Every 15 min | Checks Google Classroom for new assignments and sends Telegram notifications |
| `_due_date_reminders` | Daily at 9:00 AM | Sends reminders for upcoming pending assignments (max once per 24h per assignment) |
| `_sync_submission_states` | Every 15 min | Checks Classroom submission states; marks assignments as "completed" only when actually `TURNED_IN` or `RETURNED` |
| `_verify_drive_links` | Every 30 min | Validates Drive folder URLs still exist; clears dead links and file records from the DB |

---

## Database Schema

SQLite database at `data/mimiclaw.db` with the following tables:

**assignments**
| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT (PK) | Google Classroom assignment ID |
| `course_id` | TEXT | Google Classroom course ID |
| `course_name` | TEXT | Course display name |
| `title` | TEXT | Assignment title |
| `description` | TEXT | Assignment description |
| `due_date` | DATE | Due date (nullable) |
| `status` | TEXT | `pending`, `in_progress`, `completed`, `skipped` |
| `drive_folder_url` | TEXT | Google Drive folder URL (nullable) |
| `created_at` | DATETIME | When the assignment was first seen |
| `last_pinged_at` | DATETIME | Last time a reminder was sent |

**completed_files**
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-increment ID |
| `assignment_id` | TEXT (FK) | References assignments.id |
| `filename` | TEXT | Output filename (e.g., `server.c`) |
| `drive_url` | TEXT | Google Drive file URL |
| `created_at` | DATETIME | Upload timestamp |

**reminders**
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-increment ID |
| `text` | TEXT | Reminder content |
| `created_at` | DATETIME | Creation timestamp |

**chat_history**
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-increment ID |
| `role` | TEXT | `user` or `assistant` |
| `content` | TEXT | Message content |
| `created_at` | DATETIME | Message timestamp |

---

## Hosting on Railway (Free Tier)

[Railway](https://railway.app/) offers a free tier with 500 hours/month of execution time — enough to run the bot 24/7 for ~20 days, or indefinitely if you use their sleep/wake features.

> **Note:** The Electron dashboard is a desktop app and cannot be hosted on a server. Only the Telegram bot (`bot.py`) needs to be hosted. You run the dashboard locally on your computer.

### Step 1: Prepare the Repository

Make sure your code is pushed to GitHub. The following files should be git-ignored (check `.gitignore`):
- `.env`
- `credentials/*.json`
- `data/`
- `dashboard/node_modules/`

### Step 2: Create a Railway Project

1. Go to [railway.app](https://railway.app/) and sign in with GitHub
2. Click **New Project > Deploy from GitHub repo**
3. Select your MimiClaw repository
4. Railway auto-detects Python and installs dependencies from `requirements.txt`

### Step 3: Configure Environment Variables

In the Railway dashboard, go to **Variables** and add:

```
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_ALLOWED_USER_ID=your_user_id
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
```

### Step 4: Add a Procfile

Create a `Procfile` in the project root:

```
worker: python bot.py
```

> Use `worker` instead of `web` because the bot uses long-polling, not HTTP.

### Step 5: Handle Google OAuth Tokens

Google OAuth requires a one-time browser flow, which can't run on a server. Do this locally first:

1. Run `python setup_auth.py` locally to generate tokens
2. The tokens are saved in `credentials/token_classroom.json` and `credentials/token_drive.json`
3. **Option A: Environment Variables (Recommended)**
   ```bash
   # On your local machine, encode the tokens:
   python -c "import base64; print(base64.b64encode(open('credentials/token_classroom.json','rb').read()).decode())"
   python -c "import base64; print(base64.b64encode(open('credentials/token_drive.json','rb').read()).decode())"
   python -c "import base64; print(base64.b64encode(open('credentials/google_credentials.json','rb').read()).decode())"
   ```
   Add these as Railway environment variables:
   ```
   GOOGLE_CREDENTIALS_B64=<base64 string>
   TOKEN_CLASSROOM_B64=<base64 string>
   TOKEN_DRIVE_B64=<base64 string>
   ```
   Then add a startup script (`start.sh`):
   ```bash
   #!/bin/bash
   mkdir -p credentials
   echo "$GOOGLE_CREDENTIALS_B64" | base64 -d > credentials/google_credentials.json
   echo "$TOKEN_CLASSROOM_B64" | base64 -d > credentials/token_classroom.json
   echo "$TOKEN_DRIVE_B64" | base64 -d > credentials/token_drive.json
   python bot.py
   ```
   Update your `Procfile`:
   ```
   worker: bash start.sh
   ```

4. **Option B: Commit tokens directly (less secure)**
   Remove `credentials/*.json` from `.gitignore` and commit them. Not recommended for public repos.

### Step 6: Deploy

1. Push your changes to GitHub
2. Railway auto-deploys on every push
3. Check the deploy logs in the Railway dashboard to verify the bot started
4. You should see:
   ```
   Application started
   HTTP Request: POST .../getUpdates "HTTP/1.1 200 OK"
   ```

### Step 7: Persistent Storage

Railway containers are ephemeral — the SQLite database resets on each deploy. To persist data:

1. In Railway, add a **Volume**
2. Mount it at `/app/data`
3. The bot already uses `data/mimiclaw.db`, so it will automatically use the persistent volume

### Monitoring

- **Railway Logs** — real-time logs in the Railway dashboard
- **Bot Health** — send `/start` on Telegram; if the bot responds, it's running
- **Automatic Restarts** — Railway auto-restarts crashed processes

---

## Hosting Alternatives

| Platform | Free Tier | Pros | Cons |
|----------|-----------|------|------|
| **Railway** | 500 hrs/month | Easy GitHub deploy, volumes, env vars | Limited free hours |
| **Render** | 750 hrs/month | Generous free tier, auto-deploy | Spins down after 15 min inactivity |
| **Fly.io** | 3 shared VMs | Persistent volumes, global edge | More complex setup (Dockerfile needed) |
| **Oracle Cloud** | Always free VM | Full Linux VM, no limits | Manual setup, complex signup |
| **PythonAnywhere** | Always free | Simple Python hosting | No long-running processes on free tier |
| **Home Server / Raspberry Pi** | Free | Full control, no limits | Requires always-on hardware |

**For Render**, use the same approach as Railway but note the free tier spins down after 15 minutes of inactivity. You can use an external cron service (like [cron-job.org](https://cron-job.org/)) to ping your app and keep it alive, but this only works for web services, not workers.

**For a Raspberry Pi or home server:**
```bash
# Clone and set up
git clone https://github.com/YourUsername/mimiclaw.git
cd mimiclaw
pip install -r requirements.txt
python setup_auth.py

# Run with systemd for auto-restart
sudo nano /etc/systemd/system/mimiclaw.service
```

```ini
[Unit]
Description=MimiClaw Telegram Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/mimiclaw
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=10
EnvironmentFile=/home/pi/mimiclaw/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable mimiclaw
sudo systemctl start mimiclaw
sudo journalctl -u mimiclaw -f   # view logs
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Bot doesn't respond on Telegram** | Make sure `python bot.py` is running. Check for `409 Conflict` errors — means another instance is running. Kill all Python processes and wait 30 seconds before restarting. |
| **"All AI models failed to respond"** | Check your API keys in `.env`. Test them manually: `curl -H "Authorization: Bearer YOUR_KEY" https://generativelanguage.googleapis.com/v1beta/models`. Check Groq/Gemini status pages. |
| **Google auth fails / token expired** | Delete `credentials/token_classroom.json` and `credentials/token_drive.json`, then run `python setup_auth.py` again. |
| **"Couldn't download attachment"** | The Drive token may not have `drive.readonly` scope. Delete `credentials/token_drive.json` and re-auth. |
| **Assignment shows "completed" but not submitted** | Run `/check` to force a sync. The scheduler checks submission states every 15 minutes. |
| **Dashboard shows stale Drive links** | The scheduler cleans dead links every 30 minutes. Click Refresh or wait for the next cycle. |
| **PDF text extraction fails** | Make sure `pymupdf` is installed: `pip install pymupdf`. Some PDFs are image-based and can't be extracted. |
| **Electron dashboard won't start** | Make sure Node.js is installed: `node --version`. Run `cd dashboard && npm install` to install Electron. |
| **409 Conflict error** | Only one bot instance can poll Telegram at a time. Kill all `python.exe` processes: `taskkill /F /IM python.exe` (Windows) or `pkill python` (Linux/Mac). Wait 30 seconds, then restart. |

---

## Security Notes

- **Never commit `.env` or credential files** — they contain API keys and tokens. The `.gitignore` is already configured to exclude them.
- **Single-user access** — the bot only responds to the Telegram user ID specified in `TELEGRAM_ALLOWED_USER_ID`. All other users are silently ignored.
- **OAuth tokens** — stored locally in `credentials/`. These grant access to your Google Classroom and Drive. Treat them like passwords.
- **AI API keys** — Gemini and Groq keys are sent to their respective APIs over HTTPS. They are not logged or stored anywhere besides `.env`.
- **SQLite database** — stored locally in `data/mimiclaw.db`. Contains assignment metadata and chat history. No passwords or tokens are stored in the database.

---

## License

This project is licensed under the [Apache License 2.0](LICENSE). See the [LICENSE](LICENSE) file for details.

---

<p align="center">Made by <b>Avighna Basak</b></p>
