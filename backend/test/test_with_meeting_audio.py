import requests
import time

def test_transcribe_with_meeting_audio():
    url = "http://localhost:8001/transcribe/"
    
    # 실제 존재하는 파일 경로로 변경 필요
    audio_file_path = "../meeting_audios/meeting_20250809_110851_full.mp3"
    
    # 파일 존재 여부 먼저 확인
    import os
    if not os.path.exists(audio_file_path):
        print(f"⚠️ 테스트 파일이 존재하지 않습니다: {audio_file_path}")
        print("테스트를 건너뜁니다.")
        return None
    
    try:
        with open(audio_file_path, "rb") as audio_file:
            files = {"file": ("meeting_audio.mp3", audio_file, "audio/mpeg")}
            
            print(f"Sending transcription request with real meeting audio...")
            response = requests.post(url, files=files, timeout=10)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Request ID: {result.get('id')}")
                print(f"Status: {result.get('status')}")
                return result.get('id')
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return None
                
    except requests.exceptions.Timeout:
        print("Request timed out after 10 seconds (expected for async processing)")
        return None
    except FileNotFoundError:
        print(f"Audio file not found: {audio_file_path}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    test_transcribe_with_meeting_audio()