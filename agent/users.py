import json
from .config import USERS_FILE

def load_users():
    try:
        return json.load(open(USERS_FILE))
    except FileNotFoundError:
        raise SystemExit("❌ users.json missing")

USERS  = load_users()
ACTIVE = USERS["users"][USERS["default_user"]]

def build_user_context(u):
    return (
        "Sender profile:\n"
        f"first_name = {u['first_name']}\n"
        f"last_name  = {u['last_name']}\n"
        f"email      = {u['email']}\n"
        f"signature  = '''{u.get('signature','')}'''\n"
        "--- End profile ---\n"
    )
