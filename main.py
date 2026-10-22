import os, logging
from flask import Flask, jsonify, request
from dotenv import load_dotenv
load_dotenv()

from scheduler import jobs
from utils import state as st

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
app = Flask(__name__)
scheduler = None

JOBS = {
    "finance_post": lambda: jobs.job_post("finance"),
    "procurement_post": lambda: jobs.job_post("procurement"),
    "finance_reply": lambda: jobs.job_reply("finance"),
    "procurement_reply": lambda: jobs.job_reply("procurement"),
    "welcome": jobs.job_welcome,
}


def _auth():
    tok = os.getenv("RUN_TOKEN")
    return bool(tok) and request.headers.get("X-Run-Token") == tok


@app.route("/health")
def health():
    return jsonify({"status": "ok", "scheduler_running": bool(scheduler and scheduler.running), "auto_post": jobs.AUTO_POST})


@app.route("/jobs")
def list_jobs():
    if not _auth():
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({"jobs": [{"id": j.id, "name": j.name, "next_run": str(j.next_run_time)} for j in scheduler.get_jobs()]})


@app.route("/diag")
def diag():
    if not _auth():
        return jsonify({"error": "unauthorized"}), 401
    from utils import circle_api
    try:
        sp = circle_api.get_spaces()
        return jsonify({"circle_ok": True, "spaces": [
            {"id": x.get("id"), "name": x.get("name"), "slug": x.get("slug"), "url": x.get("url")}
            for x in sp if not request.args.get("q") or request.args["q"].lower() in f"{x.get('name','')} {x.get('slug','')} {x.get('url','')}".lower()]})
    except Exception as e:
        return jsonify({"circle_ok": False, "error": str(e)}), 200


@app.route("/drafts")
def drafts():
    if not _auth():
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({"drafts": st.load()["drafts"]})


@app.route("/run/<name>", methods=["POST"])
def run(name):
    if not _auth():
        return jsonify({"error": "unauthorized"}), 401
    if name not in JOBS:
        return jsonify({"error": "unknown job", "available": list(JOBS)}), 404
    try:
        JOBS[name]()
        return jsonify({"status": "success", "job": name, "auto_post": jobs.AUTO_POST})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500


def main():
    global scheduler
    need = ["CIRCLE_API_KEY", "GROQ_API_KEY", "FINANCE_BOT_EMAIL", "PROCUREMENT_BOT_EMAIL", "RUN_TOKEN"]
    missing = [v for v in need if not os.getenv(v)]
    if missing:
        log.error(f"Missing env vars: {missing}")
        raise SystemExit(1)
    try:
        jobs.load_spaces()
    except Exception as e:
        log.error(f"load_spaces failed (will retry at first job): {e}")
    scheduler = jobs.build_scheduler()
    scheduler.start()
    for j in scheduler.get_jobs():
        log.info(f"[{j.id}] next run {j.next_run_time}")
    log.info(f"AUTO_POST={jobs.AUTO_POST}")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))


if __name__ == "__main__":
    main()
