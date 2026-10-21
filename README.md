# SBM UK Community Desks (AI)

Two openly-labelled AI accounts post in the SBM UK Circle community:

- **SBM UK Finance Desk (AI)** - academy trust and school finance
- **SBM UK Procurement Desk (AI)** - procurement, tenders, frameworks, contracts

Every post and reply ends with an AI disclosure line. Rename the two Circle member profiles to match, and say "AI assistant" in their bios.

## Daily schedule (UK time, Mon-Fri)
| Time | Job |
|---|---|
| 09:00 | Finance Desk new post |
| 11:30 | Procurement Desk replies to a member post (not its own, once per post) |
| 15:00 | Procurement Desk new post |
| 16:30 | Finance Desk replies to a member post |
| 10:00 | Welcome one new member (never twice; first run only records existing members) |

## Trendy topics
Edit `config/topics.py` weekly. Posts may only state dates and figures that appear in those hooks. Titles already used are never repeated.

## Safe-launch checklist
1. Get Peter's OK and rename the two Circle profiles as AI accounts.
2. Set env vars (see `.env.example`). `AUTO_POST=false` first: posts are saved as drafts, view with `GET /drafts` (header `X-Run-Token`).
3. Test: `curl -X POST $URL/run/finance_post -H "X-Run-Token: $RUN_TOKEN"` then `GET /drafts`.
4. When happy, set `AUTO_POST=true`.

## Deploy on Render
Web Service, build `pip install -r requirements.txt`, start `python main.py`. Use a paid always-on instance (free instances sleep and miss scheduled jobs). State is saved in `data/state.json`; add a Render disk and set `STATE_PATH` to it, otherwise duplicate-protection resets on each deploy.
