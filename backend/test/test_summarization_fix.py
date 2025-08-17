import requests
import json
import os

def create_api_key():
    """
    테스트용 API 키를 생성합니다.
    """
    import random
    BASE_URL = "http://localhost:8001"
    
    # 사용자 로그인
    login_data = {
        "user_id": "test_01",
        "password": "password"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code != 200:
            print(f"❌ 로그인 실패: {response.text}")
            return None
        
        jwt_token = response.json()["access_token"]
        
        # API 키 생성
        headers = {"Authorization": f"Bearer {jwt_token}"}
        token_id = f"test_summarization_{random.randint(1000, 9999)}"
        
        response = requests.post(
            f"{BASE_URL}/tokens/{token_id}",
            headers=headers,
            params={"description": "요약 기능 테스트용 토큰"}
        )
        
        if response.status_code != 200:
            print(f"❌ API 키 생성 실패: {response.text}")
            return None
        
        return response.json()["token"]["api_key"]
        
    except Exception as e:
        print(f"❌ API 키 생성 중 오류: {e}")
        return None

def test_summarization_feature():
    """
    요약 기능이 수정된 후 정상 작동하는지 테스트합니다.
    """
    print("🧪 요약 기능 테스트 시작...")
    
    # API 키 생성
    print("🔑 API 키 생성 중...")
    api_key = create_api_key()
    if not api_key:
        print("❌ API 키 생성 실패")
        return False
    print(f"✅ API 키 생성 성공: {api_key[:20]}...")
    
    # 테스트할 음성 파일 경로
    audio_file_path = "english_voice_test.wav"
    
    if not os.path.exists(audio_file_path):
        print(f"❌ 테스트 음성 파일이 없습니다: {audio_file_path}")
        return False
    
    # API 요청 준비
    url = "http://localhost:8001/transcribe/protected/"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    # 요약 기능을 활성화하여 요청
    params = {
        "service": "assemblyai",
        "fallback": "true",
        "summarization": "true",  # 요약 기능 활성화
        "summary_model": "informative",
        "summary_type": "bullets"
    }
    
    try:
        with open(audio_file_path, "rb") as audio_file:
            files = {"file": (audio_file_path, audio_file, "audio/wav")}
            
            print("📡 요약 기능이 포함된 STT 요청 전송 중...")
            response = requests.post(url, headers=headers, params=params, files=files)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 요청 성공!")
                print("\n=== 전체 응답 내용 ===")
                for key, value in result.items():
                    print(f"{key}: {value}")
                print("========================\n")
                
                print(f"📝 Request ID: {result.get('request_id', 'N/A')}")
                print(f"🎯 Service Used: {result.get('service_used', 'N/A')}")
                print(f"📄 Transcription: {result.get('transcription', 'N/A')}")
                print(f"📋 Summary: {result.get('summary', 'N/A')}")
                print(f"👤 User UUID: {result.get('user_uuid', 'N/A')}")
                
                # user_uuid가 비어있는지 확인
                if not result.get('user_uuid'):
                    print("⚠️ user_uuid가 비어있습니다!")
                    return False
                
                # 요약이 제대로 생성되었는지 확인
                summary = result.get('summary', '')
                if summary and summary != "요약 생성 중 오류가 발생했습니다.":
                    print("✅ 요약 기능이 정상적으로 작동합니다!")
                    return True
                elif summary == "요약 생성 중 오류가 발생했습니다.":
                    print("❌ 요약 생성 중 오류가 여전히 발생합니다.")
                    return False
                else:
                    print("⚠️ 요약이 생성되지 않았습니다. (요약 기능이 비활성화되었을 수 있음)")
                    return False
            else:
                print(f"❌ 요청 실패: {response.status_code}")
                print(f"오류 내용: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    success = test_summarization_feature()
    if success:
        print("\n🎉 요약 기능 테스트 성공!")
    else:
        print("\n💥 요약 기능 테스트 실패!")