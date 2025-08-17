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
        params={"description": "테스트용 토큰"}
    )
    
    if response.status_code != 200:
        raise Exception(f"API 키 생성 실패: {response.text}")
    
    return response.json()["token"]["api_key"]

def test_fixed_protected_transcribe():
    """
    수정된 /transcribe/protected/ 엔드포인트 테스트
    """
    print("🔑 API 키 생성 중...")
    api_key = create_api_key()
    print(f"✅ API 키 생성 완료: {api_key[:20]}...")
    
    url = "http://localhost:8001/transcribe/protected/"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    # 실제 음성 파일 사용
    with open("real_test_audio.wav", "rb") as f:
        files = {"file": ("real_test_audio.wav", f, "audio/wav")}
        data = {
            "service": "assemblyai",
            "fallback": "true",
            "summarization": "true"
        }
        
        print("📡 /transcribe/protected/ 엔드포인트 테스트 중...")
        print(f"파일 크기: {len(f.read())} bytes")
        f.seek(0)  # 파일 포인터 리셋
        
        try:
            response = requests.post(url, files=files, data=data, headers=headers, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 성공!")
                print(f"Request ID: {result.get('request_id')}")
                print(f"Status: {result.get('status')}")
                print(f"Service Used: {result.get('service_used')}")
                print(f"Transcription: {result.get('transcription', '')[:100]}...")
                print(f"Summary: {result.get('summary', '')[:100]}...")
                
                # 데이터베이스에서 확인
                print("\n📊 데이터베이스 확인 중...")
                check_database_record(result.get('request_id'))
                
            else:
                print(f"❌ 오류 - 상태 코드: {response.status_code}")
                print(f"응답: {response.text}")
                
        except requests.exceptions.Timeout:
            print("⏰ Request timed out")
        except Exception as e:
            print(f"❌ 예외 발생: {e}")

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
            print(f"✅ 데이터베이스 레코드 발견:")
            print(f"   - ID: {result.id}")
            print(f"   - Request ID: {result.request_id}")
            print(f"   - Transcribed Text: '{result.transcribed_text}'")
            print(f"   - Summary Text: '{result.summary_text}'")
            print(f"   - Service Provider: '{result.service_provider}'")
            print(f"   - Created At: {result.created_at}")
            
            # 수정 전후 비교
            if result.transcribed_text and result.transcribed_text.strip():
                print("🎉 transcribed_text가 올바르게 저장되었습니다!")
            else:
                print("⚠️ transcribed_text가 비어있습니다.")
                
            if result.service_provider and result.service_provider.strip():
                print("🎉 service_provider가 올바르게 저장되었습니다!")
            else:
                print("⚠️ service_provider가 비어있습니다.")
        else:
            print(f"❌ 데이터베이스에서 request_id '{request_id}' 레코드를 찾을 수 없습니다.")
            
    except Exception as e:
        print(f"❌ 데이터베이스 확인 중 오류: {e}")

if __name__ == "__main__":
    test_fixed_protected_transcribe()