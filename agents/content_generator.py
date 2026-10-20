import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Best free Groq model for this use case
GROQ_MODEL = "llama-3.3-70b-versatile"


def generate_post(persona: dict, topic: str, context: str = "") -> dict:
    """
    Generate a new discussion post for a persona on a given topic.
    Returns dict with 'title' and 'body'.
    """
    prompt = f"""
You are posting a new discussion thread in a UK school business management community called SchoolBusinessManager.uk.

Topic to discuss: {topic}

{f"Additional context: {context}" if context else ""}

Generate a discussion post with:
1. A compelling, specific thread TITLE (not generic — make it feel like a real professional posted it)
2. A BODY of 150-250 words that opens the discussion, shares a perspective or challenge, and ends with a question to invite replies

Format your response as:
TITLE: [your title here]
BODY: [your body here]

Remember you are {persona['name']}, {persona['role']}.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=500,
        messages=[
            {"role": "system", "content": persona["system_prompt"]},
            {"role": "user", "content": prompt},
        ],
    )

    raw = response.choices[0].message.content.strip()
    lines = raw.split("\n")

    title = ""
    body_lines = []
    in_body = False

    for line in lines:
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("BODY:"):
            in_body = True
            body_lines.append(line.replace("BODY:", "").strip())
        elif in_body:
            body_lines.append(line)

    return {
        "title": title,
        "body": "\n".join(body_lines).strip(),
        "persona": persona["name"],
    }


def generate_reply(
    persona: dict,
    post_title: str,
    post_body: str,
    existing_replies: list = None,
    tag_member_name: str = None,
) -> str:
    """
    Generate a reply to an existing post.
    Optionally tags a real community member by name.
    """
    replies_context = ""
    if existing_replies:
        replies_context = "\n\nExisting replies in this thread:\n" + "\n---\n".join(
            existing_replies[-3:]
        )

    tag_instruction = ""
    if tag_member_name:
        tag_instruction = f"\nStart your reply by welcoming or acknowledging @{tag_member_name} naturally within your response."

    prompt = f"""
You are replying to a discussion thread in a UK school business management community called SchoolBusinessManager.uk.

Thread title: {post_title}

Original post:
{post_body}

{replies_context}

{tag_instruction}

Write a reply of 100-180 words that:
- Directly engages with the post content
- Adds value (a new angle, a practical tip, a challenge, a supporting point)
- Ends with either a follow-up question OR an invitation for others to share their experience
- Feels like a natural professional reply, not a summary

Remember you are {persona['name']}, {persona['role']}.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=400,
        messages=[
            {"role": "system", "content": persona["system_prompt"]},
            {"role": "user", "content": prompt},
        ],
    )

    return response.choices[0].message.content.strip()


def generate_welcome_comment(
    persona: dict, new_member_name: str, new_member_role: str = ""
) -> str:
    """
    Generate a welcome comment tagging a new member.
    """
    role_context = (
        f"They've listed their role as: {new_member_role}." if new_member_role else ""
    )

    prompt = f"""
A new member has just joined the SchoolBusinessManager.uk community on Circle.

New member name: {new_member_name}
{role_context}

Write a warm, genuine welcome message of 60-90 words that:
- Tags them by name (@{new_member_name})
- References something specific about the community that would be useful to them
- Asks them one specific question about their current role or a challenge they're facing
- Feels professional but friendly — not corporate or robotic

Remember you are {persona['name']}, {persona['role']}.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=200,
        messages=[
            {"role": "system", "content": persona["system_prompt"]},
            {"role": "user", "content": prompt},
        ],
    )

    return response.choices[0].message.content.strip()
