import pickle, asyncio, datetime as dt, email.utils, re
from aiogoogle import Aiogoogle
from .auth import to_user, load_client_creds
from .config import CONTACT_CACHE
from typing import Dict, Optional

_norm = re.compile(r"[^\w]").sub

async def _scan_mailbox(creds, days: int, msgs: int) -> dict[str, str]:
    """
    Scan the caller’s Gmail and build a {name → e-mail} dictionary.

    Parameters
    ----------
    creds : google.oauth2.credentials.Credentials
        OAuth credentials returned by get_google_creds().
    days  : int
        Look at messages newer than today-minus-days.
    msgs  : int
        Maximum number of messages to retrieve (API quota guard).

    Returns
    -------
    dict[str, str]
        Keys are lower-cased display names (falling back to the part
        before the ‘@’), values are full e-mail addresses.
    """
    name2mail: dict[str, str] = {}

    async with Aiogoogle(
        user_creds=to_user(creds),
        client_creds=load_client_creds()
    ) as aio:
        gmail = await aio.discover("gmail", "v1")

        after_unix = int(
            (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).timestamp()
        )

        lst = await aio.as_user(
            gmail.users.messages.list(
                userId="me",
                q=f"after:{after_unix}",
                maxResults=msgs,
            )
        )
        ids = [m["id"] for m in lst.get("messages", [])]

        for mid in ids:
            msg = await aio.as_user(
                gmail.users.messages.get(
                    userId="me",
                    id=mid,
                    format="metadata",
                    metadataHeaders=["From", "To", "Cc"],
                )
            )

            for h in msg["payload"]["headers"]:
                if h["name"] in ("From", "To", "Cc"):
                    for disp, addr in email.utils.getaddresses([h["value"]]):
                        key = (disp or addr.split("@")[0]).strip().lower()
                        if key and key not in name2mail:
                            name2mail[key] = addr 

    return name2mail

def fetch_contacts(creds, days=365, msgs=1500)->Dict[str,str]:
    if CONTACT_CACHE.exists():
        return pickle.loads(CONTACT_CACHE.read_bytes())
    async def _scan():
        async with Aiogoogle(user_creds=to_user(creds),
                             client_creds=load_client_creds()) as aio:
            gmail = await aio.discover("gmail","v1")
            after=int((dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=days)).timestamp())
            lst = await aio.as_user(gmail.users.messages.list(userId="me",
                        q=f"after:{after}", maxResults=msgs))
            ids=[m["id"] for m in lst.get("messages",[])]
            book={}
            for mid in ids:
                msg=await aio.as_user(gmail.users.messages.get(userId="me",id=mid,
                        format="metadata",metadataHeaders=["From","To","Cc"]))
                for h in msg["payload"]["headers"]:
                    if h["name"] in ("From","To","Cc"):
                        for disp,addr in email.utils.getaddresses([h["value"]]):
                            k=(disp or addr.split("@")[0]).strip().lower()
                            if k and k not in book: book[k]=addr
            return book
    print("🔎 Scanning mailbox for contacts… (Ctrl-C to skip)")
    try:
        contacts = asyncio.run(_scan())
        CONTACT_CACHE.write_bytes(pickle.dumps(contacts))
        print(f"✅ Stored {len(contacts)} contacts.")
        return contacts
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("⏹️ Scan skipped."); return {}

def resolve_contact(name:str, book:Dict[str,str])->Optional[str]:
    k=name.lower().strip()
    if k in book: return book[k]
    for key,addr in book.items():
        if key.startswith(k): return addr
    k2=_norm("",k)
    for key,addr in book.items():
        if _norm("",key)==k2: return addr
    for key,addr in book.items():
        if k in key: return addr
    return None
