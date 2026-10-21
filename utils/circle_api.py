"""Circle Admin API v2 client (Bearer token). Base: https://app.circle.so/api/admin/v2"""
import os, re, html, logging, requests
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)
BASE = os.getenv("CIRCLE_API_BASE", "https://app.circle.so/api/admin/v2")
if "/api/v1" in BASE:           # old env value left over from v1
    BASE = "https://app.circle.so/api/admin/v2"


def _h():
    return {"Authorization": f"Bearer {os.getenv('CIRCLE_API_KEY')}", "Content-Type": "application/json"}


def _raise(r):
    if not r.ok:
        raise RuntimeError(f"Circle {r.request.method} {r.request.path_url.split('?')[0]} -> {r.status_code}: {r.text[:400]}")


def _get(path, **params):
    r = requests.get(f"{BASE}/{path}", headers=_h(), params=params, timeout=30)
    _raise(r)
    return r.json()


def _post(path, payload):
    r = requests.post(f"{BASE}/{path}", headers=_h(), json=payload, timeout=30)
    _raise(r)
    return r.json()


def _records(d):
    return d if isinstance(d, list) else d.get("records", d.get("spaces", d.get("posts", d.get("comments", d.get("community_members", [])))))


def get_spaces():
    out, page = [], 1
    while page <= 5:
        d = _get("spaces", page=page, per_page=100)
        out += _records(d)
        if not (isinstance(d, dict) and d.get("has_next_page")):
            break
        page += 1
    return out


def get_posts(space_id, per_page=10):
    return _records(_get("posts", space_id=space_id, page=1, per_page=per_page, status="published"))


def get_comments(post_id, per_page=20):
    return _records(_get("comments", post_id=post_id, page=1, per_page=per_page))


def get_new_members(per_page=10):
    try:
        return _records(_get("community_members", page=1, per_page=per_page, sort="latest"))
    except RuntimeError:
        return _records(_get("community_members", page=1, per_page=per_page))


def _tiptap(text):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return {"body": {"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": p.replace("\n", " ")}]} for p in paras]}}


def _html(text):
    return "".join(f"<p>{html.escape(p.strip()).replace(chr(10), '<br>')}</p>" for p in re.split(r"\n\s*\n", text) if p.strip())


def _try(path, variants):
    errs = []
    for v in variants:
        try:
            return _post(path, v)
        except RuntimeError as e:
            errs.append(str(e)); log.warning(f"payload variant failed: {e}")
    raise RuntimeError(" | ".join(errs))


def create_post(space_id, name, body, user_email):
    base = {"space_id": space_id, "name": name, "user_email": user_email, "status": "published"}
    return _try("posts", [{**base, "tiptap_body": _tiptap(body)}, {**base, "body": _html(body)}, {**base, "internal_custom_html": _html(body)}])


def create_comment(post_id, body, user_email):
    base = {"post_id": post_id, "user_email": user_email}
    return _try("comments", [{**base, "tiptap_body": _tiptap(body)}, {**base, "body": _html(body)}])
