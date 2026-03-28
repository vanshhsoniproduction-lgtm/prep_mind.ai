# PrepMind AI — Next Generation AI Technical Interview SaaS

PrepMind AI is a state-of-the-art mock interview platform designed originally for software engineers. It simulates realistic, high-pressure FAANG-style technical interviews utilizing advanced large language models for real-time conversation parsing and high-fidelity text-to-speech architectures for human-like auditory feedback.

## 🚀 Platform Architecture & Tech Stack

- **Backend:** Python + Django (Monolithic, easily scales to microservices)
- **Frontend Engine:** Vanilla HTML/CSS + Modern JS with a custom 'Google Pixel'-inspired design system and scroll-reveal interactions.
- **AI Brain:** Google Gemini API (`gemini-3-flash-preview` / `gemini-1.5-pro`) — Handles the complex reasoning, coding evaluations, and multi-turn interview persona retention.
- **Voice Synthesis:** ElevenLabs API — Generates extremely realistic, low-latency conversational audio.
- **Speech-to-Text (STT):** Browser-native Web Speech API / MediaRecorder constraints.
- **Database:** SQLite (dev) / PostgreSQL (production-ready).
- **Authentication:** Django Allauth (Google OAuth2 + Guest Sessions).

---

## 🔑 Core Features

1. **Fully Interactive Voice Sessions:** Candidates speak directly into their microphone, and the AI responds via voice instantly, replicating a real human interviewer.
2. **Integrated IDE Ecosystem:** Side-by-side terminal and code editor built seamlessly into the interview room, allowing instantaneous transitions between behavioral dialogue and algorithmic problem solving.
3. **Deep Diagnostics Engine:** Post-interview dashboards provide granular, actionable feedback alongside specific metrics (`Technical Score`, `Communication Clarity`, and `Confidence Matrix`).
4. **Resume Contextualization:** Instructs the AI system to read parsed text from an uploaded resume and query the candidate on past microservice architectures, scaling challenges, and specific tech-stack choices.
5. **API Key Rotation Pool:** Unique system built to seamlessly bypass strict preview-model API Quotas (`429 RESOURCE_EXHAUSTED`). If the main API key dies mid-interview, the engine seamlessly rotates to the next available `.env` key array without interrupting the user.

---

## 🔄 User Workflow

1. **Authentication:** User logs in via Google OAuth or tries the fast-lane Guest Demo.
2. **Dashboard Configuration:** User configures their target (e.g., "Senior Python Developer at Meta", "Mid-Level Frontend at Stripe").
3. **Interview Initiation:** The session allocates isolated database models counting question iterations, score trajectories, and current stage pointers (`intro`, `behavioral`, `coding`, `feedback`).
4. **The Round:** The agent utilizes `generate_content` dynamically. As conversation history scales, the model maintains context across behavioral answers and code execution outputs.
5. **Termination:** Upon finalization, the AI evaluates the entire chat transcript against FAANG rubrics, yielding numerical scores. The DB state transitions to `COMPLETED` and instantly paints a "Green Box" on the user's dashboard calendar.

---

## 💰 SaaS Unit Economics & Cost Analysis

If deploying **PrepMind AI** as a commercial Software-as-a-Service (SaaS), here is the estimated per-interview raw processing cost.

### 1. Large Language Model Cost (Google Gemini)
The prompt length grows continuously as the interview progresses due to history retention.
- **Average Input Tokens per interview:** ~15,000 to 30,000 tokens (across 10-15 conversational turns).
- **Average Output Tokens per interview:** ~3,000 to 5,000 tokens.
- **Pricing (`Gemini 1.5 Flash` benchmark):** $0.075 per 1M Input / $0.30 per 1M Output.
- **Cost Estimate:** **~$0.003 - $0.01 per interview.** (Extremely cheap due to Flash architecture).

### 2. Audio Synthesis Cost (ElevenLabs)
ElevenLabs is premium text-to-speech. Costs scale directly with character count.
- **Average Characters Synthesized per interview:** ~2,500 to 4,000 characters.
- **Pricing:** ~$0.30 per 1,000 characters (Creator Tier).
- **Cost Estimate:** **~$0.75 - $1.20 per interview.**

### 3. Speech-to-Text Cost
- **Pricing:** **$0.00**. Relying entirely on the highly-accurate built-in Browser Native web-speech API to reduce backend transcription pipeline loads.

### 4. Infrastructure (VPS / Database)
- Standard $15 - $30/month DigitalOcean Droplet + Managed Postgres.
- At 1,000 interviews a month, infrastructure overhead is **~$0.03 per interview**.

### 📊 Total Cost of Goods Sold (COGS)
- **Total Cost per Full Interview:** **≈ $0.80 to $1.25**
- **Suggested Retail Price for SaaS Users:** $3.00 - $5.00 per interview credit, or an unlimited subscription gated by fair-use policies at $29/mo.

---

## ⚙️ Local Development Setup

### 1. Requirements
Ensure you have `python 3.10+` and `pip` installed.

### 2. Environment Setup
Create a `.env` file in the root directory and populate it with your keys:
```env
# Essential
DJANGO_SECRET_KEY=your-secret...
GEMINI_API_KEY=AIzaSy...
ELEVENLABS_API_KEY=sk_...

# Google OAuth (For Google Login)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# (Optional) Key Rotation Pool for Preview Models
GEMINI_API_KEY_1=...
GEMINI_API_KEY_2=...
```

### 3. DB & Start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

> **A project crafted for ambitious engineers, by ambitious engineers.**
