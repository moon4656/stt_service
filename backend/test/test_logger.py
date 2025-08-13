import requests
import time

# 간단한 더미 오디오 파일 생성 (WAV 헤더)
def create_dummy_wav():
    # 최소한의 WAV 파일 헤더 (44바이트)
    wav_header = b'RIFF'
    wav_header += (36).to_bytes(4, 'little')  # 파일 크기 - 8
    wav_header += b'WAVE'
    wav_header += b'fmt '
    wav_header += (16).to_bytes(4, 'little')  # fmt 청크 크기
    wav_header += (1).to_bytes(2, 'little')   # 오디오 포맷 (PCM)
    wav_header += (1).to_bytes(2, 'little')   # 채널 수
    wav_header += (44100).to_bytes(4, 'little')  # 샘플 레이트
    wav_header += (88200).to_bytes(4, 'little')  # 바이트 레이트
    wav_header += (2).to_bytes(2, 'little')   # 블록 정렬
    wav_header += (16).to_bytes(2, 'little')  # 비트 깊이
    wav_header += b'data'
    wav_header += (0).to_bytes(4, 'little')   # 데이터 크기
    return wav_header

def test_transcribe():
    url = "http://localhost:8001/transcribe/"
    
    # 더미 WAV 파일 생성
    dummy_audio = create_dummy_wav()
    
    try:
        files = {'file': ('test_audio.wav', dummy_audio, 'audio/wav')}
        data = {
            'service': 'assemblyai',
            'fallback': 'false'
        }
        
        print("Sending request to AssemblyAI service (no fallback)...")
        print(f"File size: {len(dummy_audio)} bytes")
        response = requests.post(url, files=files, data=data, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_transcribe()