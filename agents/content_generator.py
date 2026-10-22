import os, random, re
from datetime import datetime
import pytz
from groq import Groq
from dotenv import load_dotenv
from config.topics import HOOKS
from agents.personas import DISCLOSURE

load_dotenv()
_client = None
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def _chat(system, user, max_tokens):
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    kwargs = {}
    if "gpt-oss" in GROQ_MODEL:
        # reasoning model: keep thinking short and leave room for the answer
        kwargs["extra_body"] = {"reasoning_effort": "low"}
        max_tokens = max_tokens * 3
    r = _client.chat.completions.create(
        model=GROQ_MODEL, max_tokens=max_tokens, temperature=0.8,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        **kwargs,
    )
    if not (r.choices[0].message.content or "").strip():
        raise RuntimeError(f"Empty model output from {GROQ_MODEL}")
    return r.choices[0].message.content.strip()


def footer(desk):
    return "\n\n" + DISCLOSURE.format(desk=desk["short"])


def pick_hooks(desk, n=3):
    return random.sample(HOOKS[desk["key"]], k=min(n, len(HOOKS[desk["key"]])))


def generate_post(desk, recent_titles):
    today = datetime.now(pytz.timezone("Europe/London")).strftime("%A %d %B %Y")
    hooks = pick_hooks(desk)
    avoid = "\n".join(f"- {t}" for t in recent_titles[-30:]) or "- (none)"
    prompt = f"""
Today is {today}. Write a new discussion thread for the SBM UK community.

Current hooks (choose ONE angle; these are the only dates/figures you may state):
{chr(10).join('- ' + h for h in hooks)}

Do NOT repeat or closely echo these recent titles:
{avoid}

Write a specific, useful thread:
- TITLE: concrete, under 90 characters, no clickbait
- BODY: 140-220 words. Start with the practical issue, give 2-3 useful pointers, end with ONE question inviting members to share what they do.
- Do not say "as a CFO/manager" or claim experience. You are an AI desk.

Format exactly:
TITLE: ...
BODY: ...
"""
    raw = _chat(desk["system_prompt"], prompt, 600)
    m = re.search(r"TITLE:\s*(.+)", raw)
    b = re.search(r"BODY:\s*(.+)", raw, re.S)
    title = (m.group(1).strip().strip('*"') if m else "")[:120]
    body = (b.group(1).strip() if b else "")
    if not title or len(body) < 200:
        raise ValueError("Model output missing title/body; skipping post")
    return {"title": title, "body": body + footer(desk)}


def generate_reply(desk, post_title, post_body):
    prompt = f"""
Reply to this thread started by a community member.

Title: {post_title}
Post: {post_body[:1500]}

Write 80-140 words that engage with what they actually said, add one practical pointer, and end with a question or invitation. Do not invent facts or figures. You are an AI desk; no claimed experience.
"""
    return _chat(desk["system_prompt"], prompt, 350) + footer(desk)


def generate_welcome(desk, name, role=""):
    prompt = f"""
Write a warm 50-80 word welcome for new member {name}. {('Their stated role: ' + role + '.') if role else ''}
Mention one useful thing in the community (Supplier Marketplace, Procurement Hub or discussion spaces) and ask one simple question about what they are working on. No invented facts.
"""
    return _chat(desk["system_prompt"], prompt, 220) + footer(desk)
