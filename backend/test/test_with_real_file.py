import requests
import os

def test_with_real_audio():
    url = "http://localhost:8001/transcribe/"
    
    # 실제 오디오 파일 사용
    audio_file_path = "test_audio.mp3"
    
    if not os.path.exists(audio_file_path):
        print(f"❌ Audio file not found: {audio_file_path}")
        return
    
    file_size = os.path.getsize(audio_file_path)
    print(f"File size: {file_size} bytes")
    
    try:
        with open(audio_file_path, 'rb') as audio_file:
            files = {
                'file': ('test_audio.mp3', audio_file, 'audio/mp3')
            }
            
            print("Sending request to /transcribe/ endpoint with real audio file...")
            print(f"File: {audio_file_path}")
            
            # 타임아웃을 10초로 설정 (업로드만 확인)
            response = requests.post(url, files=files, timeout=10)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("✅ Request successful")
            else:
                print(f"❌ Request failed with status {response.status_code}")
                
    except requests.exceptions.Timeout:
        print("⏰ Request timed out (expected - transcription takes time)")
        print("Check server logs and database for the request record")
    except Exception as e:
        print(f"❌ Error occurred: {e}")

if __name__ == "__main__":
    test_with_real_audio()