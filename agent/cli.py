import asyncio, json
from .speech import VoiceRecorder, transcribe
from .planner import plan_tasks, build_contact_prompt
from .users import ACTIVE, build_user_context
from .contacts import fetch_contacts
from .auth import get_google_creds, to_user, load_client_creds
from .executor import execute_plan
from .config import GEMINI_API_KEY

def main():
    if not GEMINI_API_KEY:
        raise SystemExit("Add GEMINI_API_KEY to .env")

    creds = get_google_creds()
    user_creds  = to_user(creds)
    client_creds = load_client_creds()
    contacts = fetch_contacts(creds)

    recorder = VoiceRecorder()

    while True:
        mode = input("\n(1) Speak (2) Type (3) Quit: ").strip()
        if mode == "3":
            break
        query = (
            transcribe(recorder.record_until_silence())
            if mode == "1"
            else input("Type request: ").strip()
        )
        if not query:
            continue

        print("Planning …")
        plan = plan_tasks(
            query,
            build_user_context(ACTIVE),
            build_contact_prompt(contacts),
        )
        print(json.dumps(plan, indent=2, ensure_ascii=False))

        print("⚡ Executing …")
        asyncio.run(execute_plan(plan, user_creds, client_creds, contacts))

if __name__ == "__main__":
    main()
