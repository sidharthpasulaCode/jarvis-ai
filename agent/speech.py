import io, wave, numpy as np, pyaudio
from elevenlabs.client import ElevenLabs
from .config import ELEVEN_KEY

eleven = ElevenLabs(api_key=ELEVEN_KEY)

class VoiceRecorder:
    def __init__(self, rate=16_000, chunk=1024, ch=1, thresh=50, silence=2.0):
        self.rate, self.chunk, self.ch, self.t = rate, chunk, ch, thresh
        self.silence_chunks = int(rate / chunk * silence)
        self.format = pyaudio.paInt16
    def record_until_silence(self) -> io.BytesIO:
        pa = pyaudio.PyAudio()
        st = pa.open(format=self.format, channels=self.ch, rate=self.rate,
                     input=True, frames_per_buffer=self.chunk)
        frames, silent = [], 0
        try:
            while True:
                data = st.read(self.chunk)
                frames.append(data)
                rms = np.sqrt(np.mean(np.frombuffer(data, np.int16) ** 2))
                silent = silent + 1 if rms < self.t else 0
                if silent >= self.silence_chunks: break
        finally:
            st.stop_stream(); st.close(); pa.terminate()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(self.ch)
            w.setsampwidth(pyaudio.get_sample_size(self.format))
            w.setframerate(self.rate)
            w.writeframes(b"".join(frames))
        buf.seek(0); return buf

def transcribe(buf: io.BytesIO) -> str:
    return eleven.speech_to_text.convert(
        file=buf, model_id="scribe_v1", language_code="eng"
    ).text
