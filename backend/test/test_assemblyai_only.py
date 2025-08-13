import requests
import time

def test_assemblyai_only():
    print("Testing AssemblyAI service only (no fallback)...")
    
    # 매우 작은 더미 오디오 파일 생성
    audio_data = b'\x00' * 100  # 100 bytes의 더미 데이터
    
    print(f"File size: {len(audio_data)} bytes")
    
    try:
        # AssemblyAI 서비스만 사용하도록 설정
        response = requests.post(
            'http://localhost:8001/transcribe/',
            files={'file': ('test.wav', audio_data, 'audio/wav')},
            data={
                'service': 'assemblyai',  # AssemblyAI만 사용
                'fallback': 'false'  # 폴백 비활성화
            },
            timeout=10  # 10초 타임아웃
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"Response: {result}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_assemblyai_only()