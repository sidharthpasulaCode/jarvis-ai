import base64, pickle
from aiogoogle import Aiogoogle
from .contacts import resolve_contact
from .config import CONTACT_CACHE, PLACEHOLDER_RE
from .planner import plan_tasks
from .users import ACTIVE, build_user_context
from .tts import speak
from .planner import (
    plan_tasks,
    _safe_task,            
    build_contact_prompt  
)
def has_placeholder(txt): return bool(PLACEHOLDER_RE.search(txt or ""))

# ───────── Gmail send ───────────
async def gmail_send(aio,to,subj,body):
    gm=await aio.discover("gmail","v1")
    raw=base64.urlsafe_b64encode(f"To:{to}\r\nSubject:{subj}\r\n\r\n{body}".encode()).decode()
    await aio.as_user(gm.users.messages.send(userId="me",json={"raw":raw}))
    return "Email sent."

# ───────── executor ────────────
async def execute_plan(plan,user,client,contacts,max_retry=2):
    plan["send_email"]=_safe_task(plan.get("send_email"),
                                  {"run":False,"to":"","subject":"","body":""})

    retry=0
    while retry<=max_retry and (
        has_placeholder(plan["send_email"]["subject"]) or
        has_placeholder(plan["send_email"]["body"])
    ):
        retry+=1
        print(f"⚠️  Placeholder found, requesting rewrite (attempt {retry})")
        plan = plan_tasks("Rewrite the email filling all placeholders.",
                          build_user_context(ACTIVE),
                          build_contact_prompt(contacts))
        plan["send_email"]=_safe_task(plan.get("send_email"),
                                      {"run":False,"to":"","subject":"","body":""})

    if has_placeholder(plan["send_email"]["subject"]) or has_placeholder(plan["send_email"]["body"]):
        raise ValueError("Placeholders remain after retries; aborting send.")

    if plan["send_email"]["run"] and "@" not in plan["send_email"]["to"]:
        resolved = resolve_contact(plan["send_email"]["to"], contacts)
        if not resolved:
            resolved = input(f"📧 Address for '{plan['send_email']['to']}'? ").strip()
            contacts[plan["send_email"]["to"].lower()] = resolved
            CONTACT_CACHE.write_bytes(pickle.dumps(contacts))
        plan["send_email"]["to"] = resolved

    async with Aiogoogle(user_creds=user, client_creds=client) as aio:
        if plan["send_email"]["run"]:
            res = await gmail_send(
                aio,
                plan["send_email"]["to"],
                plan["send_email"]["subject"],
                plan["send_email"]["body"],
            )
            print("done", res)
            
    speak(plan.get("assistant_response", "All tasks completed."))