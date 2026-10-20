# SBM Agents — SchoolBusinessManager.uk Community Engine

Two AI personas that drive engagement in your Circle.so community:

- **Eleanor Finch** — CFO | Multi-Academy Trust (finance, compliance, DfE)
- **James Whitfield** — Procurement & Contracts Manager | Manchester (frameworks, suppliers, cost-saving)

---

## Schedule (UK Time, Mon–Fri)

| Time  | Action |
|-------|--------|
| 08:30 | Eleanor posts a new discussion thread |
| 09:00 | James posts a procurement thread (Tue & Thu) |
| 09:15 | Welcome new members (daily) |
| 11:00 | James replies to the latest post |
| 14:00 | Eleanor replies (Wed & Fri) |

---

## Setup

### 1. Clone & install

```bash
cd sbm-agents
pip install -r requirements.txt
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env`:

```
CIRCLE_API_KEY=your_circle_api_key
CIRCLE_COMMUNITY_ID=your_community_id
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 3. Run locally to test

```bash
python main.py
```

Manually trigger a job to test:

```bash
curl -X POST http://localhost:8080/run/eleanor_post
curl -X POST http://localhost:8080/run/james_reply
curl -X POST http://localhost:8080/run/welcome
```

Check scheduled jobs:

```bash
curl http://localhost:8080/jobs
```

---

## Deploy to Render

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set environment variables in Render dashboard:
   - `CIRCLE_API_KEY`
   - `CIRCLE_COMMUNITY_ID`
   - `ANTHROPIC_API_KEY`
5. Build command: `pip install -r requirements.txt`
6. Start command: `python main.py`
7. Deploy ✅

---

## Finding Your Circle Community ID

In your Circle admin, go to any space URL:
`https://app.circle.so/c/YOUR_COMMUNITY_SLUG/spaces`

Or use the API directly:
```bash
curl https://app.circle.so/api/v1/spaces \
  -H "Authorization: Token YOUR_API_KEY"
```

---

## Project Structure

```
sbm-agents/
├── agents/
│   ├── personas.py          # Eleanor & James persona definitions
│   └── content_generator.py # Claude-powered post/reply generation
├── scheduler/
│   └── jobs.py              # APScheduler jobs & Circle API calls
├── utils/
│   └── circle_api.py        # Circle.so API wrapper
├── main.py                  # Flask app + scheduler entrypoint
├── requirements.txt
├── Procfile                 # Render/Heroku process file
└── .env.example
```
