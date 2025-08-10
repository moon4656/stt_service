import requests
import os
from io import BytesIO

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

def test_transcribe_endpoint():
    url = "http://localhost:8001/transcribe/"
    
    # 더미 WAV 파일 생성
    dummy_audio = create_dummy_wav()
    
    # 파일 업로드
    files = {
        'file': ('test_audio.wav', dummy_audio, 'audio/wav')
    }
    
    try:
        print("Sending request to /transcribe/ endpoint...")
        print(f"File size: {len(dummy_audio)} bytes")
        
        # 타임아웃을 30초로 늘려서 실제 응답을 받아보기
        response = requests.post(url, files=files, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Request successful")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out (expected for Daglo API call)")
        print("This is normal - the request should have been logged to database")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_transcribe_endpoint()