import os
import json
import base64
import io
import wave
import pyaudio
import numpy as np
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import google.generativeai as genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "gemini here"
os.environ['ELEVENLABS_API_KEY'] = 'ell here'

# Initialize ElevenLabs client
elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

class VoiceRecorder:
    def __init__(self, sample_rate=16000, chunk_size=1024, channels=1):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.audio_format = pyaudio.paInt16
        
    def record_until_silence(self, silence_threshold=50, silence_duration=2.0):
        """Record until silence is detected"""
        print("🎤 Listening... Speak now! (Will auto-stop after silence)")
        print("Press Ctrl+C to stop manually")
        
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        frames = []
        silent_chunks = 0
        silence_chunks_needed = int(self.sample_rate / self.chunk_size * silence_duration)
        
        try:
            while True:
                data = stream.read(self.chunk_size)
                frames.append(data)
                
                # Convert audio data to numpy array for proper volume calculation
                audio_array = np.frombuffer(data, dtype=np.int16)
                
                # Calculate RMS (Root Mean Square) for volume level
                rms = np.sqrt(np.mean(audio_array**2))
                
                # Print volume level for debugging (optional)
                print(f"Audio level: {rms:.0f}", end='\r')
                
                # Check for silence
                if rms < silence_threshold:
                    silent_chunks += 1
                else:
                    silent_chunks = 0
                
                # Stop if silence detected for specified duration
                if silent_chunks >= silence_chunks_needed:
                    print(f"\n✅ Recording complete (silence detected)")
                    break
                    
        except KeyboardInterrupt:
            print("\n⏹️ Recording stopped by user")
        
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        return frames
    
    def frames_to_wav_bytes(self, frames):
        """Convert recorded frames to WAV format bytes"""
        wav_buffer = io.BytesIO()
        
        # Create WAV file in memory
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(pyaudio.get_sample_size(self.audio_format))
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(b''.join(frames))
        
        wav_buffer.seek(0)
        return wav_buffer

def transcribe_audio(frames, recorder):
    """Transcribe audio using ElevenLabs"""
    try:
        print("🔄 Processing audio...")
        audio_data = recorder.frames_to_wav_bytes(frames)
        
        transcription = elevenlabs.speech_to_text.convert(
            file=audio_data,
            model_id="scribe_v1",
            tag_audio_events=True,
            language_code="eng",
            diarize=False
        )
        return transcription.text
    except Exception as e:
        print(f"❌ Error during transcription: {e}")
        return None

def get_voice_input(recorder):
    """Get voice input from user"""
    while True:
        print("\n" + "="*60)
        print("🎙️  VOICE INPUT MODE")
        print("="*60)
        print("Options:")
        print("1. 🎤 Speak your request")
        print("2. ⌨️  Type your request")
        print("3. 🚪 Exit")
        print("="*60)
        
        choice = input("Choose an option (1-3): ").strip()
        
        if choice == "1":
            frames = recorder.record_until_silence()
            if frames:
                text = transcribe_audio(frames, recorder)
                if text:
                    print(f"\n💬 You said: \"{text}\"")
                    confirm = input("Is this correct? (y/n): ").strip().lower()
                    if confirm in ['y', 'yes', '']:
                        return text
                    else:
                        print("Let's try again...")
                        continue
                else:
                    print("❌ Transcription failed. Please try again.")
                    continue
            else:
                print("❌ No audio recorded. Please try again.")
                continue
                
        elif choice == "2":
            text = input("Type your request: ").strip()
            if text:
                return text
            else:
                print("❌ Please enter a valid request.")
                continue
                
        elif choice == "3":
            return None
            
        else:
            print("❌ Invalid choice. Please try again.")
            continue

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
        print("✅ Email sent!")

    if plan_dict["review_recent_emails"]["run"]:
        hours = plan_dict["review_recent_emails"].get("time_window_hours", 24)
        summaries = summarize_recent_emails(creds, hours)
        print("\n📧 Summary of recent emails:")
        for subj in summaries:
            print("-", subj)

if __name__ == "__main__":
    # Check API keys
    if not os.getenv("ELEVENLABS_API_KEY"):
        print("❌ Error: ELEVENLABS_API_KEY not found in environment variables.")
        print("Please add your API key to your .env file:")
        print("ELEVENLABS_API_KEY=your_api_key_here")
        exit(1)
        
    if not GEMINI_API_KEY:
        print("❌ Warning: GEMINI_API_KEY not found. Some features may not work.")
    
    # Initialize voice recorder
    recorder = VoiceRecorder()
    
    # Authenticate Google services
    print("🔐 Authenticating Google services...")
    creds = authenticate_google()
    
    # Main loop
    while True:
        print("\n" + "🌟"*30)
        print("🤖 VOICE-ENABLED GOOGLE ASSISTANT")
        print("🌟"*30)
        
        # Get voice or text input
        query = get_voice_input(recorder)
        
        if query is None:
            print("👋 Goodbye!")
            break
            

        print(f"\n🎯 Processing request: \"{query}\"")
        
        try:
            # Generate task plan
            print("🧠 Analyzing request...")
            plan = get_task_plan(query)
            plan_dict = convert_composite(plan)
            
            # Show plan (optional)
            print("\n📋 Task Plan:")
            print(json.dumps(plan_dict, indent=2))
            
            # Execute plan
            print("\n⚡ Executing tasks...")
            execute_task_plan(plan_dict, creds)
            print("\n✅ All tasks completed!")
            
        except Exception as e:
            print(f"❌ Error processing request: {e}")
        
        # Ask if user wants to continue
        continue_choice = input("\n🔄 Would you like to make another request? (y/n): ").strip().lower()
        if continue_choice not in ['y', 'yes', '']:
            print("👋 Goodbye!")
            break