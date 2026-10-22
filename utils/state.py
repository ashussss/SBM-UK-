import json, os, threading
PATH = os.getenv("STATE_PATH", "data/state.json")
_lock = threading.Lock()
_DEFAULT = {"titles": [], "welcomed": [], "replied": [], "drafts": [], "seeded_members": False}

def load():
    try:
        with open(PATH) as f:
            return {**_DEFAULT, **json.load(f)}
    except Exception:
        return dict(_DEFAULT)

def save(state):
    global PATH
    try:
        os.makedirs(os.path.dirname(PATH) or ".", exist_ok=True)
        with _lock, open(PATH, "w") as f:
            json.dump(state, f, indent=1)
    except OSError as e:           # e.g. /data without a Render disk: fall back to local file
        import logging
        logging.getLogger(__name__).warning(f"STATE_PATH {PATH} not writable ({e}); using data/state.json")
        PATH = "data/state.json"
        os.makedirs("data", exist_ok=True)
        with _lock, open(PATH, "w") as f:
            json.dump(state, f, indent=1)
