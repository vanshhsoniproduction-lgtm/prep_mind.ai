from elevenlabs.client import ElevenLabs
from django.conf import settings
import uuid
import os
import time
import tempfile

from PrepMind_AI.settings import BASE_DIR

# Initialize ElevenLabs
client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)

def generate_audio(text, user_id):
    """Convert text to speech using ElevenLabs and return the audio file URL."""
    print(f"\n{'='*60}")
    print(f"[ELEVENLABS-TTS] 🔊 generate_audio()")
    print(f"[ELEVENLABS-TTS] 📝 Text: {text[:200]}")
    
    start_time = time.time()
    
    audio_stream = client.text_to_speech.convert(
        voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel
        output_format="mp3_44100_128",
        text=text,
        model_id="eleven_multilingual_v2",
        voice_settings={
            "stability": 0.5,
            "similarity_boost": 0.75,
        }
    )
    
    filename = f"audio_{user_id}_{uuid.uuid4().hex[:8]}.mp3"
    audio_dir = os.path.join(BASE_DIR, 'static', 'audio')
    os.makedirs(audio_dir, exist_ok=True)
    filepath = os.path.join(audio_dir, filename)
    
    with open(filepath, "wb") as f:
        for chunk in audio_stream:
            if chunk:
                f.write(chunk)
    
    elapsed = round(time.time() - start_time, 2)
    file_size = os.path.getsize(filepath)
    
    print(f"[ELEVENLABS-TTS] ✅ Audio saved: {filename} ({file_size} bytes) in {elapsed}s")
    print(f"{'='*60}\n")
                
    return f"/static/audio/{filename}"


def transcribe_audio(audio_file_path):
    """Convert speech audio file to text using ElevenLabs STT."""
    print(f"\n{'='*60}")
    print(f"[ELEVENLABS-STT] 🎤 transcribe_audio()")
    print(f"[ELEVENLABS-STT] 📂 File: {audio_file_path}")
    
    start_time = time.time()
    
    with open(audio_file_path, "rb") as audio_file:
        result = client.speech_to_text.convert(
            file=audio_file,
            model_id="scribe_v1",
            language_code="en",
        )
    
    transcript = result.text.strip() if result and result.text else ""
    elapsed = round(time.time() - start_time, 2)
    
    print(f"[ELEVENLABS-STT] ✅ Transcribed in {elapsed}s")
    print(f"[ELEVENLABS-STT] 📝 Result: \"{transcript[:200]}\"")
    print(f"{'='*60}\n")
    
    return transcript
