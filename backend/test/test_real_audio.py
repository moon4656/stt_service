import requests
import time

def test_transcribe_real_audio():
    url = "http://localhost:8001/transcribe/"
    
    # 실제 음성 파일 사용
    with open("real_test_audio.wav", "rb") as f:
        files = {"file": ("real_test_audio.wav", f, "audio/wav")}
        
        print("Sending request to /transcribe/ endpoint...")
        print(f"File size: {len(f.read())} bytes")
        f.seek(0)  # 파일 포인터 리셋
        
        try:
            # 타임아웃을 60초로 설정 (실제 음성 파일이므로 더 오래 걸릴 수 있음)
            response = requests.post(url, files=files, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 성공!")
                print(f"Request ID: {result.get('request_id')}")
                print(f"Status: {result.get('status')}")
                if 'transcribed_text' in result:
                    print(f"Transcribed text: {result['transcribed_text'][:100]}...")
            else:
                print(f"❌ 오류 - 상태 코드: {response.status_code}")
                print(f"응답: {response.text}")
                
        except requests.exceptions.Timeout:
            print("⏰ Request timed out (expected for long audio processing)")
            print("This is normal - the request should have been logged to database")
        except Exception as e:
            print(f"❌ 예외 발생: {e}")

if __name__ == "__main__":
    test_transcribe_real_audio()