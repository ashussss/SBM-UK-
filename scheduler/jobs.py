import logging, os
import pytz
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from agents.personas import DESKS
from agents.content_generator import generate_post, generate_reply, generate_welcome
from utils import circle_api as circle
from utils import state as st

log = logging.getLogger(__name__)
UK_TZ = pytz.timezone("Europe/London")

AUTO_POST = os.getenv("AUTO_POST", "false").lower() == "true"   # false = save drafts only
DAYS = os.getenv("POST_DAYS", "mon-fri")
EXCLUDE = ["supplier", "marketplace", "announce", "welcome", "intro", "event", "resource", "admin", "procurement hub", "newsletter"]
INCLUDE = ["discussion", "general", "community", "finance", "procurement", "chat", "ask"]

TARGET_SPACE_IDS = []
WELCOME_SPACE_ID = None


def email_for(desk):
    e = os.getenv(desk["email_env"])
    if not e:
        raise RuntimeError(f"{desk['email_env']} not set")
    return e


def load_spaces():
    """Choose spaces safely. Prefer explicit POST_SPACE_IDS; otherwise match names, never post in excluded spaces."""
    global TARGET_SPACE_IDS, WELCOME_SPACE_ID
    TARGET_SPACE_IDS = []
    raw = circle.get_spaces()
    spaces = raw if isinstance(raw, list) else raw.get("spaces", raw.get("records", []))
    if not spaces:
        log.error(f"Circle returned no spaces. Response type={type(raw).__name__} "
                  f"keys={list(raw.keys()) if isinstance(raw, dict) else len(raw)} "
                  f"snippet={str(raw)[:300]}")
    explicit = [x.strip() for x in os.getenv("POST_SPACE_IDS", "").split(",") if x.strip()]
    for s in spaces:
        log.info(f"Space {s['id']}: {s.get('name')}")
        name = (s.get("name", "") + " " + s.get("slug", "")).lower()
        if "welcome" in name or "introduc" in name:
            WELCOME_SPACE_ID = os.getenv("WELCOME_SPACE_ID") and int(os.getenv("WELCOME_SPACE_ID")) or s["id"]
        if explicit:
            if str(s["id"]) in explicit:
                TARGET_SPACE_IDS.append(s["id"])
        elif any(k in name for k in INCLUDE) and not any(k in name for k in EXCLUDE):
            TARGET_SPACE_IDS.append(s["id"])
    log.info(f"Target spaces: {TARGET_SPACE_IDS} | welcome space: {WELCOME_SPACE_ID}")
    if not TARGET_SPACE_IDS:
        log.error("No safe target space found. Set POST_SPACE_IDS in the environment.")


def _pick_space(desk):
    """Each desk has its own fixed space (FINANCE_SPACE_ID / PROCUREMENT_SPACE_ID).
    Falls back to POST_SPACE_IDS rotation if the per-desk variable is not set."""
    fixed = os.getenv(f"{desk['key'].upper()}_SPACE_ID")
    if fixed:
        return int(fixed)
    if not TARGET_SPACE_IDS:
        load_spaces()
    if not TARGET_SPACE_IDS:
        raise RuntimeError("No target space configured (set FINANCE_SPACE_ID / PROCUREMENT_SPACE_ID)")
    return TARGET_SPACE_IDS[datetime.now(UK_TZ).toordinal() % len(TARGET_SPACE_IDS)]


def _publish_or_draft(kind, desk, payload, publish_fn):
    s = st.load()
    if AUTO_POST:
        res = publish_fn()
        return res
    s["drafts"].append({"kind": kind, "desk": desk["name"], "at": datetime.now(UK_TZ).isoformat(), **payload})
    s["drafts"] = s["drafts"][-100:]
    st.save(s)
    log.info(f"DRAFT saved ({kind}, {desk['name']}). Set AUTO_POST=true to publish.")
    return {"draft": True}


def _make_images(desk, out):
    mode = os.getenv("IMAGE_MODE", "off").lower()
    if mode == "off" or len(out.get("points", [])) < 2:
        return []
    from utils import visuals
    base = os.getenv("PUBLIC_URL", "https://sbm-uk.onrender.com").rstrip("/")
    try:
        if mode == "carousel":
            names = visuals.carousel(out["title"], out["points"], out["question"], desk["name"])
        else:
            names = [visuals.infographic(out["title"], out["points"], desk["name"])]
        return [f"{base}/img/{n}" for n in names]
    except Exception as e:
        log.error(f"Image generation failed, posting text only: {e}")
        return []


def job_post(desk_key):
    desk = DESKS[desk_key]
    log.info(f"JOB post: {desk['name']}")
    try:
        s = st.load()
        space_id = _pick_space(desk)
        out = generate_post(desk, s["titles"])
        images = _make_images(desk, out)
        res = _publish_or_draft("post", desk, {"space_id": space_id, "title": out["title"], "body": out["body"], "images": images},
                                lambda: circle.create_post(space_id, out["title"], out["body"], email_for(desk), image_urls=images))
        s = st.load()
        s["titles"].append(out["title"])
        s["titles"] = s["titles"][-200:]
        if isinstance(res, dict) and res.get("id"):
            s.setdefault("own_posts", []).append(res["id"])
        st.save(s)
        log.info(f"Post done: {out['title']}")
        return out["title"]
    except Exception as e:
        log.error(f"Post failed ({desk_key}): {e}")
        raise


def job_reply(desk_key):
    desk = DESKS[desk_key]
    log.info(f"JOB reply: {desk['name']}")
    try:
        s = st.load()
        space_id = _pick_space(desk)
        own = set(s.get("own_posts", []))
        for p in circle.get_posts(space_id, per_page=10):
            pid = p["id"]
            au = p.get("author") or {}
            author = f"{au.get('name', '')} {au.get('email', '')}" if isinstance(au, dict) else str(au)
            if pid in own or pid in s["replied"] or "SBM UK" in author or "(AI)" in author:
                continue
            b = p.get("body")
            text = (b.get("html") or b.get("body") or "") if isinstance(b, dict) else str(b or "")
            reply = generate_reply(desk, p.get("name", ""), text)
            _publish_or_draft("reply", desk, {"post_id": pid, "body": reply},
                              lambda: circle.create_comment(pid, reply, email_for(desk)))
            s = st.load(); s["replied"].append(pid); s["replied"] = s["replied"][-300:]; st.save(s)
            log.info(f"Replied to post {pid}")
            return pid
        log.info("No suitable post to reply to")
    except Exception as e:
        log.error(f"Reply failed ({desk_key}): {e}")
        raise


def job_welcome():
    log.info("JOB welcome")
    try:
        s = st.load()
        members = circle.get_new_members(per_page=10)
        if not s["seeded_members"]:      # first run: remember existing members, welcome nobody
            s["welcomed"] = [m["id"] for m in members]
            s["seeded_members"] = True
            st.save(s)
            log.info("Seeded existing members; no welcomes sent on first run")
            return
        space_id = WELCOME_SPACE_ID
        if not space_id:
            log.warning("No welcome space found; skipping")
            return
        desk = DESKS["finance"]
        for m in members:
            if m["id"] in s["welcomed"]:
                continue
            name = m.get("name") or m.get("full_name") or "there"
            body = generate_welcome(desk, name, m.get("headline", "") or "")
            _publish_or_draft("welcome", desk, {"space_id": space_id, "title": f"Welcome, {name}", "body": body},
                              lambda: circle.create_post(space_id, f"Welcome, {name}", body, email_for(desk)))
            s = st.load(); s["welcomed"].append(m["id"]); st.save(s)
            return  # one welcome per run keeps it light
    except Exception as e:
        log.error(f"Welcome failed: {e}")
        raise


def build_scheduler():
    """Only the two weekly posts are scheduled by default.
    Replies and welcomes are OFF unless REPLIES_ENABLED / WELCOME_ENABLED are set to true."""
    sch = BackgroundScheduler(timezone=UK_TZ)
    t = lambda h, m, days=DAYS: CronTrigger(day_of_week=days, hour=h, minute=m, timezone=UK_TZ)
    # Two posts a week: Tuesday 10:00 UK (Finance Desk), Thursday 14:00 UK (Procurement Desk)
    sch.add_job(job_post, t(10, 0, "tue"), args=["finance"], id="finance_post", name="Finance Desk post Tue 10:00", misfire_grace_time=3600)
    sch.add_job(job_post, t(14, 0, "thu"), args=["procurement"], id="procurement_post", name="Procurement Desk post Thu 14:00", misfire_grace_time=3600)
    if os.getenv("REPLIES_ENABLED", "false").lower() == "true":
        sch.add_job(job_reply, t(11, 30), args=["procurement"], id="procurement_reply", name="Procurement reply 11:30", misfire_grace_time=1800)
        sch.add_job(job_reply, t(16, 30), args=["finance"], id="finance_reply", name="Finance reply 16:30", misfire_grace_time=1800)
    if os.getenv("WELCOME_ENABLED", "false").lower() == "true":
        sch.add_job(job_welcome, CronTrigger(hour=10, minute=0, timezone=UK_TZ), id="welcome", name="Welcome new members 10:00", misfire_grace_time=1800)
    return sch
