import requests
import json
import time
from database import engine
from sqlalchemy import text

# 요약 기능을 포함한 테스트 요청
url = "http://localhost:8001/transcribe/"
params = {
    "service": "assemblyai",
    "fallback": "true",
    "summarization": "true"  # 요약 기능 활성화
}

# 더미 파일로 테스트
files = {'file': ('test_duration.wav', b'dummy audio data for duration test', 'audio/wav')}

print("audio_duration_minutes 및 tokens_used 계산 테스트 시작...")
print("요약 기능을 포함한 요청을 전송합니다.")

try:
    start_time = time.time()
    response = requests.post(url, params=params, files=files, timeout=60)
    request_time = time.time() - start_time
    
    print(f"응답 상태: {response.status_code}")
    print(f"요청 소요 시간: {request_time:.2f}초")
    
    if response.status_code == 200:
        response_data = response.json()
        print(f"응답 내용 (일부): {str(response_data)[:300]}...")
    else:
        print(f"응답 내용: {response.text[:200]}...")
        
except Exception as e:
    print(f"요청 오류: {e}")

# 잠시 대기 후 데이터베이스에서 최신 레코드 확인
time.sleep(3)

print("\n=== 최신 레코드의 duration 관련 필드 확인 ===")
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT id, audio_duration_minutes, tokens_used, duration, service_provider, created_at
        FROM transcription_responses 
        ORDER BY id DESC 
        LIMIT 1
    '''))
    
    for row in result:
        print(f"ID: {row[0]}")
        print(f"audio_duration_minutes: {row[1]}")
        print(f"tokens_used: {row[2]}")
        print(f"duration (초): {row[3]}")
        print(f"service_provider: {row[4]}")
        print(f"created_at: {row[5]}")
        
        # 계산 검증
        if row[1] is not None and row[2] is not None:
            print(f"\n✅ 계산 결과:")
            print(f"   - audio_duration_minutes: {row[1]:.2f}분")
            print(f"   - tokens_used: {row[2]:.2f}점 (1분당 1점 기준)")
            print(f"   - 계산 일치 여부: {'✅' if abs(row[1] - row[2]) < 0.01 else '❌'}")
        else:
            print("❌ duration 관련 필드가 NULL입니다.")

print("\n=== 테스트 완료 ===")