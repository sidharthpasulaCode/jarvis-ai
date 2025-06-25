# Jarvis 🎙️ — Voice-Driven Google Assistant  
*(Gemini 1.5 Pro + ElevenLabs TTS)*

Jarvis is a local Python agent that turns **natural-language voice or text prompts** into a structured JSON “task plan,” executes the plan against Google Workspace, then speaks a one-sentence confirmation back to you.

> **Example**  
> **You:** “Email Professor Garcia the final draft and book office hours next Tuesday.”  
> **Jarvis:** (*sends the mail, adds Calendar event*) “Email sent and meeting booked for Tuesday at 3 pm.”

---

## 1  Main Features

| Capability | Tech used |
|------------|-----------|
| **Voice input** | `pyaudio` capture → ElevenLabs Speech-to-Text `scribe_v1` |
| **Task planning** | Gemini 1.5-pro with **function-calling** → `task_schema.json` |
| **Google actions** | Async `aiogoogle` calls (Gmail, Docs, Sheets, Calendar) |
| **Contact resolver** | Scans mailbox once → fuzzy name ⇢ address mapping |
| **Placeholder guard** | Auto-rewrites any draft that still contains `[PUT YOUR NAME HERE]` |
| **Spoken confirmation** | Gemini fills `assistant_response` (≤ 20 words) → ElevenLabs TTS |
| **Modular code** | Clean package: `speech.py`, `contacts.py`, `planner.py`, `executor.py`, … |

---


## 2  Prerequisites

| What | Why |
|------|-----|
| **Python ≥ 3.10** | Modern typing / match statement |
| **Google Cloud credentials** (`credentials.json`) | Desktop-app OAuth client, enables Workspace APIs |
| **Generative AI API key** | Gemini 1.5-pro – add to `.env` |
| **ElevenLabs API key** | Speech-to-Text & Text-to-Speech |
| *(optional)* `VOICE_ID` | Choose any voice from your ElevenLabs studio |

Create **`.env`**:

```env
GEMINI_API_KEY=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=JBFqnCBsd6RMkjVDRZzb

set up credentials through creating your own google cloud project and defining its capabilities
a token will be generated afterward

run using the following command:
python -m agent.cli
