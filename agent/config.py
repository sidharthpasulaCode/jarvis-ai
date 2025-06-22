import os, re
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
ELEVEN_KEY      = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
ROOT            = Path(__file__).resolve().parent
GOOGLE_CLIENT   = ROOT / "credentials.json"
TOKEN_CACHE     = ROOT / "token.json"
CONTACT_CACHE   = ROOT / "contacts.pkl"
USERS_FILE      = ROOT / "users.json"

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

PLACEHOLDER_RE = re.compile(
    r"\[\s*(?:put\s+your\s+name\s+here|place\s*holder|.+?\.\.\.)\s*\]",
    re.IGNORECASE,
)
