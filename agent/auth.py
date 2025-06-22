import json, datetime as dt
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from aiogoogle.auth.creds import UserCreds, ClientCreds
from .config import SCOPES, TOKEN_CACHE, GOOGLE_CLIENT

# ───────── Google auth ─────────
def get_google_creds() -> Credentials:
    if TOKEN_CACHE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_CACHE, SCOPES)
    else:
        creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_CLIENT, SCOPES).run_local_server(port=0)
        TOKEN_CACHE.write_text(creds.to_json())
    return creds

def to_user(creds)->UserCreds:
    exp = creds.expiry
    if exp.tzinfo is None: exp = exp.replace(tzinfo=dt.timezone.utc)
    seconds = max(int((exp - dt.datetime.now(dt.timezone.utc)).total_seconds()),0)
    return UserCreds(access_token=creds.token, refresh_token=creds.refresh_token,
                     expires_in=seconds, token_type="Bearer",
                     scopes =" ".join(creds.scopes))

def load_client_creds()->ClientCreds:
    c = json.load(open(GOOGLE_CLIENT))
    src = c.get("installed") or c.get("web")
    return ClientCreds(client_id=src["client_id"], client_secret=src["client_secret"],
                       scopes=SCOPES, redirect_uri=src["redirect_uris"][0])
