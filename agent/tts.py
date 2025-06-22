import pyaudio 
from elevenlabs.client import ElevenLabs
from elevenlabs import play
from .config import ELEVEN_KEY, ELEVEN_VOICE_ID 

_elabs = ElevenLabs(api_key=ELEVEN_KEY)

def speak(
    text: str,
    voice_id: str = ELEVEN_VOICE_ID,
    model_id: str = "eleven_multilingual_v2",
    fmt: str = "mp3_44100_128",         
) -> None:
    if not text.strip():
        return
    audio_gen = _elabs.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format=fmt,
    )

    play(audio_gen)

