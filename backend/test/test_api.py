import requests

# API 테스트
url = "http://localhost:8000/transcribe/"
file_path = "meeting_audios/meeting_20250809_110851_full.mp3"

try:
    with open(file_path, 'rb') as f:
        files = {'file': (file_path, f, 'audio/mpeg')}
        response = requests.post(url, files=files)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"Error: {e}")