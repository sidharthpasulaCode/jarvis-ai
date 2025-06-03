import os
import json
import base64
import google.generativeai as genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# ========= API Setup =========
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyC9-sF7WTeeNgkaBJGqcrKrpu-NhUguwLU"

def authenticate_google():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

# ========= Gemini Setup =========
task_schema = {
    "type": "object",
    "properties": {
        "create_doc": {
            "type": "object",
            "properties": {
                "run": {"type": "boolean"},
                "doc_title": {"type": "string"},
                "doc_content": {"type": "string"}
            },
            "required": ["run", "doc_title", "doc_content"]
        },
        "review_doc": {
            "type": "object",
            "properties": {
                "run": {"type": "boolean"},
                "doc_name": {"type": "string"}
            },
            "required": ["run", "doc_name"]
        },
        "create_sheet": {
            "type": "object",
            "properties": {
                "run": {"type": "boolean"},
                "sheet_title": {"type": "string"},
                "sheet_data": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "string"}}
                }
            },
            "required": ["run", "sheet_title", "sheet_data"]
        },
        "review_sheet": {
            "type": "object",
            "properties": {
                "run": {"type": "boolean"},
                "sheet_name": {"type": "string"}
            },
            "required": ["run", "sheet_name"]
        },
        "calendar_update": {
            "type": "object",
            "properties": {
                "run": {"type": "boolean"},
                "events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string"},
                            "start": {"type": "string"},
                            "end": {"type": "string"}
                        },
                        "required": ["summary", "start", "end"]
                    }
                }
            },
            "required": ["run", "events"]
        },
        "youtube_info": {
            "type": "object",
            "properties": {
                "run": {"type": "boolean"},
                "query": {"type": "string"}
            },
            "required": ["run", "query"]
        },
        "review_recent_emails": {
            "type": "object",
            "properties": {
                "run": {"type": "boolean"},
                "time_window_hours": {"type": "integer"}
            },
            "required": ["run"]
        },
        "send_email": {
            "type": "object",
            "properties": {
                "run": {"type": "boolean"},
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["run", "to", "subject", "body"]
        }
    },
    "required": [
        "create_doc",
        "review_doc",
        "create_sheet",
        "review_sheet",
        "calendar_update",
        "youtube_info",
        "review_recent_emails",
        "send_email"
    ]
}


description = (
    "The user will provide natural language requests for a variety of tasks. "
    "Your job is to analyze the request and generate a structured JSON response specifying which tasks to perform. "
    "These tasks include creating or reviewing Google Docs, Sheets, Calendar events, YouTube information, and Gmail operations. "
    "When assigned a task like creating a Google Doc or Sheet, perform any necessary research or reasoning to complete the task thoughtfully. For example: "
    "If the user requests a summary, short essay, list, or explanation, this should result in a structured response under the 'create_doc' task. "
    "If the task involves organizing or structuring data, it likely falls under 'create_sheet'. "
    "Only set 'run': true for tasks that are clearly implied by the user's intent. "
    "Make smart, context-aware decisions to ensure your structured output meaningfully matches the user's request. "
    "Your ultimate goal is to ensure that the plan you produce enables successful completion of the task with no ambiguity."
    "DO NOT create blanks when sending emails and ensure that the reciever of the email has a full coherent email. This means no blanks like [put your name here] or [starting here]"
)

def get_task_plan(user_input):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        tools=[{
            "function_declarations": [{
                "name": "interpret_user_task",
                "description": description,
                "parameters": task_schema
            }]
        }]
    )

    response = model.generate_content(
    contents=[
        {
            "role": "user",
            "parts": [
                {
                    "function_call": {
                        "name": "interpret_user_task"
                    }
                }
            ]
        },
        {
            "role": "user",
            "parts": [
                {
                    "text": user_input
                }
            ]
        }
    ],
    tool_config={
        "function_calling_config": {
            "mode": "ANY"
        }
    }
)


    return (response.candidates[0].content.parts[0].function_call.args)

def convert_composite(obj):
    if isinstance(obj, dict):
        return {k: convert_composite(v) for k, v in obj.items()}
    elif hasattr(obj, "items"):  # MapComposite
        return {k: convert_composite(v) for k, v in obj.items()}
    elif isinstance(obj, list) or hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
        return [convert_composite(v) for v in obj]
    else:
        return obj


def send_email(creds, to, subject, body):
    service = build("gmail", "v1", credentials=creds)
    message = {
        "raw": base64.urlsafe_b64encode(
            f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}".encode("utf-8")
        ).decode("utf-8")
    }
    service.users().messages().send(userId="me", body=message).execute()

def summarize_recent_emails(creds, hours=24):
    service = build("gmail", "v1", credentials=creds)
    now = datetime.utcnow()
    after = int((now - timedelta(hours=hours)).timestamp())
    query = f"after:{after}"
    results = service.users().messages().list(userId="me", q=query).execute()
    messages = results.get("messages", [])
    summaries = []
    for msg in messages[:10]:
        msg_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
        headers = msg_data.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(No Subject)")
        summaries.append(subject)
    return summaries

def execute_task_plan(plan_dict, creds):
    docs_service = build("docs", "v1", credentials=creds)
    sheets_service = build("sheets", "v4", credentials=creds)
    calendar_service = build("calendar", "v3", credentials=creds)
    youtube_service = build("youtube", "v3", credentials=creds)

    if plan_dict["create_doc"]["run"]:
        doc_title = plan_dict["create_doc"]["doc_title"]
        doc_content = plan_dict["create_doc"]["doc_content"]
        doc = docs_service.documents().create(body={"title": doc_title}).execute()
        doc_id = doc["documentId"]
        requests = [{"insertText": {"location": {"index": 1}, "text": doc_content}}]
        docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
        print(f"✅ Created Google Doc: {doc_title}")

    if plan_dict["create_sheet"]["run"]:
        sheet_title = plan_dict["create_sheet"]["sheet_title"]
        sheet_data = plan_dict["create_sheet"]["sheet_data"]
        spreadsheet = sheets_service.spreadsheets().create(body={
            "properties": {"title": sheet_title}
        }).execute()
        sheet_id = spreadsheet["spreadsheetId"]
        sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range="Sheet1!A1",
            valueInputOption="RAW",
            body={"values": sheet_data}
        ).execute()
        print(f"✅ Created Google Sheet: {sheet_title}")

    if plan_dict["calendar_update"]["run"]:
        for event in plan_dict["calendar_update"]["events"]:
            calendar_service.events().insert(
                calendarId="primary",
                body={
                    "summary": event["summary"],
                    "start": {"dateTime": event["start"], "timeZone": "America/New_York"},
                    "end": {"dateTime": event["end"], "timeZone": "America/New_York"}
                }
            ).execute()
        print("✅ Calendar events added.")

    if plan_dict["youtube_info"]["run"]:
        query = plan_dict["youtube_info"]["query"]
        results = youtube_service.search().list(
            q=query, part="snippet", type="video", maxResults=3
        ).execute()
        print("📺 YouTube Search Results:")
        for item in results.get("items", []):
            title = item["snippet"]["title"]
            video_id = item["id"]["videoId"]
            print(f" - {title}\n   https://youtube.com/watch?v={video_id}")
    
    if plan_dict["send_email"]["run"]:
        send_email(creds, plan_dict["send_email"]["to"], plan_dict["send_email"]["subject"], plan_dict["send_email"]["body"])
        print("Email sent!")

    if plan_dict["review_recent_emails"]["run"]:
        hours = plan_dict["review_recent_emails"].get("time_window_hours", 24)
        summaries = summarize_recent_emails(creds, hours)
        print("\n🧾 Summary of recent emails:")
        for subj in summaries:
            print("-", subj)        
    


if __name__ == "__main__":
    creds = authenticate_google()
    query = input("What would you like me to do?\n> ")
    plan = get_task_plan(query)
    plan_dict = convert_composite(plan)
    print(json.dumps(plan_dict, indent=2))
    execute_task_plan(plan_dict, creds)
    print("done")
