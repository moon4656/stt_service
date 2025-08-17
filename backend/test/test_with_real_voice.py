import requests
import time
import json
import random

def create_api_key():
    """
    새로운 API 키 생성
    """
    BASE_URL = "http://localhost:8001"
    
    # 1. 사용자 로그인 (JWT 토큰 획득)
    login_data = {
        "user_id": "test_01",
        "password": "password"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        raise Exception(f"로그인 실패: {response.text}")
    
    jwt_token = response.json()["access_token"]
    
    # 2. API 키 생성
    headers = {"Authorization": f"Bearer {jwt_token}"}
    token_id = f"test_token_{random.randint(1000, 9999)}"
    
    response = requests.post(
        f"{BASE_URL}/tokens/{token_id}",
        headers=headers,
        params={"description": "실제 음성 테스트용 토큰"}
    )
    
    if response.status_code != 200:
        raise Exception(f"API 키 생성 실패: {response.text}")
    
    return response.json()["token"]["api_key"]

def test_with_real_voice():
    """
    실제 음성 파일로 /transcribe/protected/ 엔드포인트 테스트
    """
    print("🔑 API 키 생성 중...")
    api_key = create_api_key()
    print(f"✅ API 키 생성 완료: {api_key[:20]}...")
    
    # 실제 음성 파일로 테스트
    audio_file = "english_voice_test.wav"
    
    print(f"📡 /transcribe/protected/ 엔드포인트 테스트 중... (파일: {audio_file})")
    
    with open(audio_file, "rb") as f:
        files = {"file": (audio_file, f, "audio/wav")}
        headers = {"Authorization": f"Bearer {api_key}"}
        data = {
            "service": "assemblyai",
            "fallback_enabled": "true",
            "summarize": "true"
        }
        
        import os
        file_size = os.path.getsize(audio_file)
        print(f"파일 크기: {file_size} bytes")
        
        response = requests.post(
            "http://localhost:8001/transcribe/protected/",
            files=files,
            headers=headers,
            data=data,
            timeout=60
        )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ 성공!")
        print(f"Request ID: {result.get('request_id')}")
        print(f"Status: {result.get('status')}")
        print(f"Service Used: {result.get('service_used')}")
        print(f"Transcription: {result.get('transcription')}")
        print(f"Summary: {result.get('summary')}")
        
        # 데이터베이스 레코드 확인
        if result.get('request_id'):
            time.sleep(1)  # 데이터베이스 저장 대기
            check_database_record(result.get('request_id'))
        
    else:
        print(f"❌ 실패: {response.status_code}")
        print(f"응답: {response.text}")

def check_database_record(request_id):
    """
    데이터베이스에서 해당 request_id의 레코드 확인
    """
    try:
        from database import get_db, TranscriptionResponse
        from sqlalchemy.orm import Session
        
        db = next(get_db())
        result = db.query(TranscriptionResponse).filter(
            TranscriptionResponse.request_id == request_id
        ).first()
        
        if result:
            print(f"\n✅ 데이터베이스 레코드 발견:")
            print(f"   - ID: {result.id}")
            print(f"   - Request ID: {result.request_id}")
            print(f"   - Transcribed Text: '{result.transcribed_text}' (길이: {len(result.transcribed_text) if result.transcribed_text else 0})")
            print(f"   - Summary Text: '{result.summary_text}' (길이: {len(result.summary_text) if result.summary_text else 0})")
            print(f"   - Service Provider: '{result.service_provider}'")
            print(f"   - Created At: {result.created_at}")
            
            # 수정 전후 비교
            if result.transcribed_text and result.transcribed_text.strip():
                print("\n🎉 transcribed_text가 올바르게 저장되었습니다!")
            else:
                print("\n⚠️ transcribed_text가 비어있습니다.")
                
            if result.service_provider and result.service_provider.strip():
                print("🎉 service_provider가 올바르게 저장되었습니다!")
            else:
                print("⚠️ service_provider가 비어있습니다.")
        else:
            print(f"❌ 데이터베이스에서 request_id '{request_id}' 레코드를 찾을 수 없습니다.")
            
    except Exception as e:
        print(f"❌ 데이터베이스 확인 중 오류: {e}")

if __name__ == "__main__":
    test_with_real_voice()