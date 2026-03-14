from elevenlabs.client import ElevenLabs
import os

client = ElevenLabs(api_key="sk_812942848bb63cc0d3d7370bd660a5ebd396be2d9e74a804")
response = client.voices.get_all()
for v in response.voices:
    print(v.voice_id, v.name)
