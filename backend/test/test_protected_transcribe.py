import requests
import json

def test_protected_transcribe():
    """
    API 키로 보호된 transcribe 엔드포인트를 테스트합니다.
    """
    # 먼저 API 키 생성
    login_data = {
        "user_id": "test_01",
        "password": "password"
    }
    
    # 로그인
    login_response = requests.post("http://localhost:8001/auth/login", json=login_data)
    if login_response.status_code != 200:
        print(f"❌ 로그인 실패: {login_response.status_code} - {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    
    # API 키 생성
    headers = {"Authorization": f"Bearer {token}"}
    import time
    token_id = f"test_token_{int(time.time())}"
    api_key_response = requests.post(f"http://localhost:8001/tokens/{token_id}", headers=headers, params={"description": "Test API key"})
    
    if api_key_response.status_code != 200:
        print(f"❌ API 키 생성 실패: {api_key_response.status_code} - {api_key_response.text}")
        return
    
    api_key = api_key_response.json()["token"]["api_key"]
    print(f"생성된 API 키: {api_key}")
    
    # 테스트용 오디오 파일 생성 (가짜 데이터)
    test_audio_content = b"fake audio content for testing"
    
    # 보호된 transcribe 엔드포인트 테스트
    files = {
        "file": ("test_audio.mp3", test_audio_content, "audio/mpeg")
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    print("\n=== 보호된 transcribe 엔드포인트 테스트 ===")
    response = requests.post(
        "http://localhost:8001/transcribe/protected/",
        files=files,
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ 보호된 transcribe 엔드포인트 테스트 성공!")
    else:
        print(f"❌ 보호된 transcribe 엔드포인트 테스트 실패: {response.status_code}")

if __name__ == "__main__":
    test_protected_transcribe()