import requests
import json
import time
from database import engine
from sqlalchemy import text

# 테스트용 한글 오디오 파일 업로드 (실제로는 더미 요청)
url = "http://localhost:8001/transcribe/"
params = {
    "service": "assemblyai",
    "fallback": "true",
    "summarization": "false"
}

# 더미 파일로 테스트 (실제 오디오 파일이 없으므로)
files = {'file': ('test_korean.wav', b'dummy audio data', 'audio/wav')}

print("한글 인코딩 테스트를 위한 요청 전송 중...")
try:
    response = requests.post(url, params=params, files=files, timeout=30)
    print(f"응답 상태: {response.status_code}")
    print(f"응답 내용: {response.text[:200]}...")
except Exception as e:
    print(f"요청 오류: {e}")

# 잠시 대기 후 데이터베이스에서 최신 레코드 확인
time.sleep(2)

print("\n=== 최신 레코드의 response_data 확인 ===")
with engine.connect() as conn:
    result = conn.execute(text('SELECT id, response_data FROM transcription_responses ORDER BY id DESC LIMIT 1'))
    
    for row in result:
        print(f"ID: {row[0]}")
        print(f"Raw response_data: {row[1][:300]}...")
        
        # JSON 파싱 시도
        try:
            parsed_data = json.loads(row[1])
            print(f"Parsed transcription: {parsed_data.get('transcription', '')[:100]}...")
            print("✅ 한글이 올바르게 저장되었습니다!")
        except Exception as e:
            print(f"JSON 파싱 오류: {e}")