# Professional AI Voice Agent (Advanced Starter)

This project gives you an efficient real-time voice agent with:

- Voice Activity Detection (WebRTC VAD) for low-latency turn detection
- Async producer/consumer audio pipeline
- OpenAI STT -> LLM -> TTS loop
- Tunable quality/latency parameters
- API/web mode for deployment
- Session-based chat memory
- Optional API-key auth and basic rate limiting

## 1) Setup

```powershell
cd "C:\Users\VISWA\ai-voice-agent-pro"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and add your `OPENAI_API_KEY`.

## 2) Run

```powershell
python main.py
```

Speak normally. The assistant detects end-of-turn using VAD and replies with synthesized voice.

## 3) Efficiency Tuning

- `vad_aggressiveness`: increase to reject more noise (0-3)
- `silence_timeout_ms`: lower for faster cutoffs
- `min_speech_ms`: increase to ignore short noise bursts
- `LLM_MODEL`: pick smaller model for faster response

## 4) Recommended Next Upgrades (Production)

- Add wake-word front-end (Porcupine/openWakeWord)
- Add barge-in cancellation while TTS is speaking
- Add local fallback STT/TTS when API is unavailable
- Add Redis-backed session memory + tool calling
- Package into desktop app (Electron or PySide)

## 5) Deploy (Render / Railway / Any Docker Host)

Important: live microphone capture only works on your local machine (`python main.py`).
Cloud deploy runs API mode via `server.py`.

### Render

1. Push this folder to GitHub.
2. In Render, create a new **Web Service** from that repo.
3. Render auto-detects `render.yaml` / Dockerfile.
4. Add `OPENAI_API_KEY` in environment variables.
5. Deploy.

Health URL:
- `https://<your-service>.onrender.com/health`

Chat endpoint:
- `POST https://<your-service>.onrender.com/chat`
- JSON body: `{"message":"Hello"}`

Web UI:
- Open `https://<your-service>.onrender.com/`

### Railway

1. New Project -> Deploy from GitHub repo.
2. Railway detects Dockerfile.
3. Add env var: `OPENAI_API_KEY`.
4. Deploy and open generated URL.
5. Open root URL `/` for web chat UI.

### Local container run

```powershell
docker build -t ai-voice-agent-pro .
docker run -p 8000:8000 --env OPENAI_API_KEY=your_key_here ai-voice-agent-pro
```

## 6) Make It Client-Ready

Set these in `.env` before sales demos or production:

- `APP_NAME` and `COMPANY_NAME` for branding in web UI
- `LOGO_URL` to show your company logo in hero section
- `ACCENT_COLOR` and `ACCENT_COLOR_2` for custom theme colors
- `WHATSAPP_URL` and `CALENDLY_URL` for conversion CTAs
- `CLIENT_API_KEY` to protect `/chat` from unauthorized usage
- `ADMIN_KEY` to protect `/admin/metrics`
- `RATE_LIMIT_PER_MINUTE` to control abuse
- `MAX_HISTORY_TURNS` for conversation continuity/cost control

If `CLIENT_API_KEY` is set, call `/chat` with header:

```text
x-api-key: your_client_key
```

### Minimal API example

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "x-api-key: your_client_key" \
  -d "{\"message\":\"hello\",\"session_id\":null}"
```

## 7) Business Packaging Suggestions

- Create 3 plans: Starter / Growth / Enterprise
- Include SLA, monthly token limit, support response times
- Add your logo and domain, then deploy behind HTTPS
- Move in-memory sessions/rate-limits to Redis for scale

## 8) New Built-In Sales UI

The root URL (`/`) now includes:

- Live demo chat for prospects
- Pricing section
- Contact sales (lead capture) form
- Admin metrics dashboard

New endpoints:

- `POST /leads` stores sales inquiries
- `GET /admin/metrics` shows usage KPIs (supports `x-admin-key`)
