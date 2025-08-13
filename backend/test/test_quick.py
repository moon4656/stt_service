import requests
import io
import wave
import struct

def create_dummy_wav():
    """Create a minimal dummy WAV file in memory"""
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(44100)  # 44.1kHz
        # Write 1 second of silence (44100 frames)
        silence = struct.pack('<h', 0) * 44100
        wav_file.writeframes(silence)
    buffer.seek(0)
    return buffer.getvalue()

def test_transcribe():
    url = "http://localhost:8001/transcribe/"
    
    # Create dummy audio file
    audio_data = create_dummy_wav()
    
    files = {
        'file': ('test_audio.wav', audio_data, 'audio/wav')
    }
    
    print(f"Sending request with very short timeout...")
    print(f"File size: {len(audio_data)} bytes")
    
    try:
        # Very short timeout to force failure quickly
        response = requests.post(url, files=files, timeout=1)
        print(f"✅ Success: {response.status_code}")
        print(f"Response: {response.json()}")
    except requests.exceptions.Timeout:
        print("⏰ Request timed out (expected)")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_transcribe()