import logging
import random
import pytz
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from agents.personas import ELEANOR_PERSONA, JAMES_PERSONA
from agents.content_generator import (
    generate_post,
    generate_reply,
    generate_welcome_comment,
)
from utils.circle_api import (
    get_spaces,
    get_posts,
    get_new_members,
    create_post,
    create_comment,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

UK_TZ = pytz.timezone("Europe/London")

# ── Space targeting ──────────────────────────────────────────────────────────
# Set these to your actual Circle.so space IDs.
# You can find them via GET /spaces or from your community admin URLs.
TARGET_SPACE_IDS = []          # populated at startup from the API
WELCOME_SPACE_ID = None        # the "Introductions" or "Welcome" space


def load_spaces():
    """Fetch community spaces and cache IDs for use in jobs."""
    global TARGET_SPACE_IDS, WELCOME_SPACE_ID
    try:
        spaces = get_spaces()
        log.info(f"Found {len(spaces)} spaces")
        for s in spaces:
            log.info(f"  Space: {s['id']} — {s['name']}")
            slug = s.get("slug", "").lower()
            name = s.get("name", "").lower()
            if any(k in name or k in slug for k in ["welcome", "introduction", "intro", "new"]):
                WELCOME_SPACE_ID = s["id"]
            else:
                TARGET_SPACE_IDS.append(s["id"])
        if not TARGET_SPACE_IDS and spaces:
            TARGET_SPACE_IDS = [spaces[0]["id"]]
        log.info(f"Welcome space: {WELCOME_SPACE_ID} | Target spaces: {TARGET_SPACE_IDS}")
    except Exception as e:
        log.error(f"Failed to load spaces: {e}")


# ── Job: Eleanor posts a new discussion thread ────────────────────────────────
def job_eleanor_post():
    log.info("▶ JOB: Eleanor — new post")
    if not TARGET_SPACE_IDS:
        log.warning("No target spaces configured — skipping")
        return
    try:
        topic = random.choice(ELEANOR_PERSONA["post_topics"])
        space_id = random.choice(TARGET_SPACE_IDS)
        result = generate_post(ELEANOR_PERSONA, topic)
        post = create_post(space_id, result["title"], result["body"])
        log.info(f"✅ Eleanor posted: '{result['title']}' (post_id={post.get('id')})")
    except Exception as e:
        log.error(f"Eleanor post failed: {e}")


# ── Job: James replies to Eleanor's latest post ───────────────────────────────
def job_james_reply():
    log.info("▶ JOB: James — reply to recent post")
    if not TARGET_SPACE_IDS:
        return
    try:
        space_id = random.choice(TARGET_SPACE_IDS)
        posts_data = get_posts(space_id, per_page=5)
        posts = posts_data if isinstance(posts_data, list) else posts_data.get("posts", [])
        if not posts:
            log.warning("No posts found to reply to")
            return
        # Prefer the most recent post
        target = posts[0]
        post_id = target["id"]
        title = target.get("name", "")
        body = target.get("body", "")

        reply = generate_reply(JAMES_PERSONA, title, body)
        create_comment(post_id, reply)
        log.info(f"✅ James replied to post_id={post_id}: '{title}'")
    except Exception as e:
        log.error(f"James reply failed: {e}")


# ── Job: James posts a new procurement discussion ─────────────────────────────
def job_james_post():
    log.info("▶ JOB: James — new post")
    if not TARGET_SPACE_IDS:
        return
    try:
        topic = random.choice(JAMES_PERSONA["post_topics"])
        space_id = random.choice(TARGET_SPACE_IDS)
        result = generate_post(JAMES_PERSONA, topic)
        post = create_post(space_id, result["title"], result["body"])
        log.info(f"✅ James posted: '{result['title']}' (post_id={post.get('id')})")
    except Exception as e:
        log.error(f"James post failed: {e}")


# ── Job: Eleanor replies to James's latest post ───────────────────────────────
def job_eleanor_reply():
    log.info("▶ JOB: Eleanor — reply to recent post")
    if not TARGET_SPACE_IDS:
        return
    try:
        space_id = random.choice(TARGET_SPACE_IDS)
        posts_data = get_posts(space_id, per_page=5)
        posts = posts_data if isinstance(posts_data, list) else posts_data.get("posts", [])
        if not posts:
            return
        target = posts[0]
        reply = generate_reply(
            ELEANOR_PERSONA,
            target.get("name", ""),
            target.get("body", ""),
        )
        create_comment(target["id"], reply)
        log.info(f"✅ Eleanor replied to post_id={target['id']}")
    except Exception as e:
        log.error(f"Eleanor reply failed: {e}")


# ── Job: Welcome new members ──────────────────────────────────────────────────
def job_welcome_new_members():
    log.info("▶ JOB: Welcome new members")
    try:
        members_data = get_new_members(per_page=5)
        members = (
            members_data
            if isinstance(members_data, list)
            else members_data.get("community_members", [])
        )
        if not members:
            log.info("No new members to welcome")
            return

        space_id = WELCOME_SPACE_ID or (TARGET_SPACE_IDS[0] if TARGET_SPACE_IDS else None)
        if not space_id:
            log.warning("No space available for welcome posts")
            return

        # Alternate welcomes between Eleanor and James
        for i, member in enumerate(members[:3]):
            name = member.get("name", "") or member.get("full_name", "Unknown")
            role = member.get("headline", "") or member.get("bio", "")
            persona = ELEANOR_PERSONA if i % 2 == 0 else JAMES_PERSONA

            welcome = generate_welcome_comment(persona, name, role)
            # Post as a new thread in the welcome space
            create_post(
                space_id,
                f"Welcome to the community, {name}! 👋",
                welcome,
            )
            log.info(f"✅ {persona['name']} welcomed {name}")
    except Exception as e:
        log.error(f"Welcome job failed: {e}")


# ── Schedule setup ────────────────────────────────────────────────────────────
def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=UK_TZ)

    # Eleanor posts a new thread — Mon–Fri at 08:30 UK time
    scheduler.add_job(
        job_eleanor_post,
        CronTrigger(day_of_week="mon-fri", hour=8, minute=30, timezone=UK_TZ),
        id="eleanor_post",
        name="Eleanor — morning discussion post",
    )

    # James replies to the latest post — Mon–Fri at 11:00 UK time
    scheduler.add_job(
        job_james_reply,
        CronTrigger(day_of_week="mon-fri", hour=11, minute=0, timezone=UK_TZ),
        id="james_reply",
        name="James — mid-morning reply",
    )

    # James posts a new procurement thread — Tue & Thu at 09:00 UK time
    scheduler.add_job(
        job_james_post,
        CronTrigger(day_of_week="tue,thu", hour=9, minute=0, timezone=UK_TZ),
        id="james_post",
        name="James — procurement discussion post",
    )

    # Eleanor replies — Wed & Fri at 14:00 UK time
    scheduler.add_job(
        job_eleanor_reply,
        CronTrigger(day_of_week="wed,fri", hour=14, minute=0, timezone=UK_TZ),
        id="eleanor_reply",
        name="Eleanor — afternoon reply",
    )

    # Welcome new members — every day at 09:15 UK time
    scheduler.add_job(
        job_welcome_new_members,
        CronTrigger(hour=9, minute=15, timezone=UK_TZ),
        id="welcome_members",
        name="Welcome new members",
    )

    return scheduler
