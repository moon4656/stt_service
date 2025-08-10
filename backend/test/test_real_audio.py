import requests
import os

def test_transcribe_with_real_audio():
    url = "http://localhost:8001/transcribe/"
    
    # 실제 오디오 파일 사용
    audio_file_path = "test_audio.mp3"
    
    if not os.path.exists(audio_file_path):
        print(f"❌ Audio file not found: {audio_file_path}")
        return
    
    try:
        with open(audio_file_path, 'rb') as audio_file:
            files = {
                'file': ('test_audio.mp3', audio_file, 'audio/mp3')
            }
            
            print("Sending request to /transcribe/ endpoint with real audio file...")
            print(f"File: {audio_file_path}")
            
            # 타임아웃을 60초로 설정
            response = requests.post(url, files=files, timeout=60)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("✅ Request successful")
                # JSON 응답 파싱
                try:
                    result = response.json()
                    print(f"RID: {result.get('rid')}")
                    print(f"Status: {result.get('status')}")
                    print(f"Progress: {result.get('progress')}")
                    if 'sttResults' in result:
                        print(f"Transcription: {result['sttResults']}")
                except Exception as e:
                    print(f"Failed to parse JSON: {e}")
            else:
                print(f"❌ Request failed with status {response.status_code}")
                
    except requests.exceptions.Timeout:
        print("⏰ Request timed out after 60 seconds")
        print("This might indicate the transcription is taking longer than expected")
    except Exception as e:
        print(f"❌ Error occurred: {e}")

if __name__ == "__main__":
    test_transcribe_with_real_audio()