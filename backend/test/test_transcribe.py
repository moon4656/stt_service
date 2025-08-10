import requests
import os

# 테스트용 작은 오디오 파일 생성 (빈 파일)
test_file_path = "test_audio.mp3"
with open(test_file_path, "wb") as f:
    f.write(b"fake audio content for testing")

try:
    # /transcribe/ 엔드포인트 테스트
    with open(test_file_path, "rb") as f:
        files = {"file": ("test_audio.mp3", f, "audio/mp3")}
        response = requests.post("http://localhost:8000/transcribe/", files=files)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"Error: {e}")

finally:
    # 테스트 파일 삭제
    if os.path.exists(test_file_path):
        os.remove(test_file_path)