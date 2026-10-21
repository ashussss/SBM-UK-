import os, requests
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("CIRCLE_API_BASE", "https://app.circle.so/api/v1")
CID = os.getenv("CIRCLE_COMMUNITY_ID")


def _h():
    return {"Authorization": f"Token {os.getenv('CIRCLE_API_KEY')}", "Content-Type": "application/json"}


def _get(path, **params):
    r = requests.get(f"{BASE}/{path}", headers=_h(), params={"community_id": CID, **params}, timeout=30)
    r.raise_for_status()
    return r.json()


def _post(path, payload):
    r = requests.post(f"{BASE}/{path}", headers=_h(), json={"community_id": CID, **payload}, timeout=30)
    r.raise_for_status()
    return r.json()


def get_spaces():
    return _get("spaces")


def get_posts(space_id, per_page=10):
    d = _get("posts", space_id=space_id, per_page=per_page, sort="latest")
    return d if isinstance(d, list) else d.get("posts", d.get("records", []))


def get_comments(post_id, per_page=20):
    d = _get("comments", post_id=post_id, per_page=per_page)
    return d if isinstance(d, list) else d.get("comments", d.get("records", []))


def get_new_members(per_page=10):
    d = _get("community_members", per_page=per_page, sort="latest")
    return d if isinstance(d, list) else d.get("community_members", d.get("records", []))


def create_post(space_id, name, body, user_email):
    return _post("posts", {"space_id": space_id, "name": name, "body": body, "user_email": user_email})


def create_comment(post_id, body, user_email):
    return _post("comments", {"post_id": post_id, "body": body, "user_email": user_email})
