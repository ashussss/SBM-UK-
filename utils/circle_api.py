import os
import requests
from dotenv import load_dotenv

load_dotenv()

CIRCLE_API_KEY = os.getenv("CIRCLE_API_KEY")
CIRCLE_COMMUNITY_ID = os.getenv("CIRCLE_COMMUNITY_ID")
CIRCLE_API_BASE = os.getenv("CIRCLE_API_BASE", "https://app.circle.so/api/v1")

HEADERS = {
    "Authorization": f"Token {CIRCLE_API_KEY}",
    "Content-Type": "application/json",
}


def get_spaces():
    """Fetch all spaces in the community."""
    url = f"{CIRCLE_API_BASE}/spaces"
    params = {"community_id": CIRCLE_COMMUNITY_ID}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def get_posts(space_id: int, per_page: int = 10):
    """Fetch recent posts from a space."""
    url = f"{CIRCLE_API_BASE}/posts"
    params = {
        "community_id": CIRCLE_COMMUNITY_ID,
        "space_id": space_id,
        "per_page": per_page,
        "sort": "latest",
    }
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def get_new_members(per_page: int = 5):
    """Fetch recently joined community members."""
    url = f"{CIRCLE_API_BASE}/community_members"
    params = {
        "community_id": CIRCLE_COMMUNITY_ID,
        "per_page": per_page,
        "sort": "latest",
    }
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def create_post(space_id: int, name: str, body: str, user_email: str = None):
    """Create a new post in a space."""
    url = f"{CIRCLE_API_BASE}/posts"
    payload = {
        "community_id": CIRCLE_COMMUNITY_ID,
        "space_id": space_id,
        "name": name,
        "body": body,
    }
    if user_email:
        payload["user_email"] = user_email

    response = requests.post(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json()


def create_comment(post_id: int, body: str, user_email: str = None):
    """Post a comment/reply on an existing post."""
    url = f"{CIRCLE_API_BASE}/comments"
    payload = {
        "community_id": CIRCLE_COMMUNITY_ID,
        "post_id": post_id,
        "body": body,
    }
    if user_email:
        payload["user_email"] = user_email

    response = requests.post(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json()


def get_community_members(per_page: int = 50):
    """Fetch community members list."""
    url = f"{CIRCLE_API_BASE}/community_members"
    params = {
        "community_id": CIRCLE_COMMUNITY_ID,
        "per_page": per_page,
    }
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def create_or_get_member(email: str, name: str, bio: str = ""):
    """Create a new member account or get existing one by email."""
    url = f"{CIRCLE_API_BASE}/community_members"
    payload = {
        "community_id": CIRCLE_COMMUNITY_ID,
        "email": email,
        "name": name,
    }
    if bio:
        payload["bio"] = bio

    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        # If account already exists, try to fetch it
        if e.response.status_code == 409 or e.response.status_code == 400:
            # Account might already exist, return the email
            return {"email": email, "name": name}
        raise

