import os
import time
import logging
from flask import Flask, jsonify
from dotenv import load_dotenv

from scheduler.jobs import build_scheduler, load_spaces
from scheduler.jobs import (
    job_eleanor_post,
    job_james_post,
    job_james_reply,
    job_eleanor_reply,
    job_welcome_new_members,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

app = Flask(__name__)
scheduler = None


@app.route("/health")
def health():
    return jsonify({"status": "ok", "scheduler_running": scheduler.running if scheduler else False})


@app.route("/run/<job_name>", methods=["POST"])
def run_job_manually(job_name: str):
    """Manually trigger a specific job — useful for testing."""
    jobs = {
        "eleanor_post": job_eleanor_post,
        "james_post": job_james_post,
        "james_reply": job_james_reply,
        "eleanor_reply": job_eleanor_reply,
        "welcome": job_welcome_new_members,
    }
    if job_name not in jobs:
        return jsonify({"error": f"Unknown job: {job_name}", "available": list(jobs.keys())}), 404
    try:
        jobs[job_name]()
        return jsonify({"status": "success", "job": job_name})
    except Exception as e:
        log.error(f"Manual job '{job_name}' failed: {e}")
        return jsonify({"status": "error", "detail": str(e)}), 500


@app.route("/jobs")
def list_jobs():
    """List all scheduled jobs and their next run times."""
    if not scheduler:
        return jsonify({"error": "Scheduler not initialised"}), 500
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time),
        })
    return jsonify({"jobs": jobs})


def main():
    global scheduler

    required_vars = ["CIRCLE_API_KEY", "CIRCLE_COMMUNITY_ID", "ANTHROPIC_API_KEY"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        log.error(f"Missing required environment variables: {missing}")
        raise SystemExit(1)

    log.info("Loading community spaces...")
    load_spaces()

    log.info("Starting scheduler...")
    scheduler = build_scheduler()
    scheduler.start()

    log.info("All jobs scheduled. Starting Flask server...")
    for job in scheduler.get_jobs():
        log.info(f"  [{job.id}] next run: {job.next_run_time}")

    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
