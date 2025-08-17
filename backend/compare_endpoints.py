import requests
import json
import time

def test_general_transcribe():
    """
    일반 /transcribe/ 엔드포인트를 테스트합니다.
    """
    print("\n=== 일반 /transcribe/ 엔드포인트 테스트 ===")
    
    # 테스트용 오디오 파일 생성 (가짜 데이터)
    test_audio_content = b"fake audio content for testing"
    
    files = {
        "file": ("test_audio.mp3", test_audio_content, "audio/mpeg")
    }
    
    try:
        response = requests.post(
            "http://localhost:8001/transcribe/",
            files=files,
            timeout=60
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            print("\n=== 일반 엔드포인트 응답 구조 ===")
            for key, value in response_data.items():
                print(f"{key}: {type(value).__name__} = {value}")
            return response_data
        else:
            print(f"❌ 일반 엔드포인트 테스트 실패: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 일반 엔드포인트 테스트 오류: {e}")
        return None

def test_protected_transcribe():
    """
    보호된 /transcribe/protected/ 엔드포인트를 테스트합니다.
    """
    print("\n=== 보호된 /transcribe/protected/ 엔드포인트 테스트 ===")
    
    # 먼저 API 키 생성
    login_data = {
        "user_id": "test_01",
        "password": "password"
    }
    
    # 로그인
    login_response = requests.post("http://localhost:8001/auth/login", json=login_data)
    if login_response.status_code != 200:
        print(f"❌ 로그인 실패: {login_response.status_code} - {login_response.text}")
        return None
    
    token = login_response.json()["access_token"]
    
    # API 키 생성
    headers = {"Authorization": f"Bearer {token}"}
    token_id = f"test_token_{int(time.time())}"
    api_key_response = requests.post(
        f"http://localhost:8001/tokens/{token_id}", 
        headers=headers, 
        params={"description": "Test API key"}
    )
    
    if api_key_response.status_code != 200:
        print(f"❌ API 키 생성 실패: {api_key_response.status_code} - {api_key_response.text}")
        return None
    
    api_key = api_key_response.json()["token"]["api_key"]
    print(f"생성된 API 키: {api_key}")
    
    # 테스트용 오디오 파일 생성 (가짜 데이터)
    test_audio_content = b"fake audio content for testing"
    
    files = {
        "file": ("test_audio.mp3", test_audio_content, "audio/mpeg")
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.post(
            "http://localhost:8001/transcribe/protected/",
            files=files,
            headers=headers,
            timeout=60
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            print("\n=== 보호된 엔드포인트 응답 구조 ===")
            for key, value in response_data.items():
                print(f"{key}: {type(value).__name__} = {value}")
            return response_data
        else:
            print(f"❌ 보호된 엔드포인트 테스트 실패: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 보호된 엔드포인트 테스트 오류: {e}")
        return None

def compare_responses(general_response, protected_response):
    """
    두 엔드포인트의 응답을 비교합니다.
    """
    print("\n" + "="*60)
    print("📊 두 엔드포인트 응답 비교 분석")
    print("="*60)
    
    if not general_response or not protected_response:
        print("❌ 비교할 응답 데이터가 없습니다.")
        return
    
    general_keys = set(general_response.keys())
    protected_keys = set(protected_response.keys())
    
    print("\n🔍 응답 키 비교:")
    print(f"일반 엔드포인트 키 개수: {len(general_keys)}")
    print(f"보호된 엔드포인트 키 개수: {len(protected_keys)}")
    
    # 공통 키
    common_keys = general_keys & protected_keys
    print(f"\n✅ 공통 키 ({len(common_keys)}개): {sorted(common_keys)}")
    
    # 일반 엔드포인트에만 있는 키
    general_only = general_keys - protected_keys
    if general_only:
        print(f"\n🔵 일반 엔드포인트에만 있는 키 ({len(general_only)}개): {sorted(general_only)}")
    
    # 보호된 엔드포인트에만 있는 키
    protected_only = protected_keys - general_keys
    if protected_only:
        print(f"\n🟢 보호된 엔드포인트에만 있는 키 ({len(protected_only)}개): {sorted(protected_only)}")
    
    # 공통 키의 값 비교
    print("\n📋 공통 키의 값 비교:")
    for key in sorted(common_keys):
        general_val = general_response[key]
        protected_val = protected_response[key]
        
        if general_val == protected_val:
            print(f"  ✅ {key}: 동일 ({general_val})")
        else:
            print(f"  ❌ {key}: 다름")
            print(f"    일반: {general_val} ({type(general_val).__name__})")
            print(f"    보호: {protected_val} ({type(protected_val).__name__})")
    
    # 고유 키의 값 출력
    if general_only:
        print("\n🔵 일반 엔드포인트 고유 키 값:")
        for key in sorted(general_only):
            print(f"  {key}: {general_response[key]} ({type(general_response[key]).__name__})")
    
    if protected_only:
        print("\n🟢 보호된 엔드포인트 고유 키 값:")
        for key in sorted(protected_only):
            print(f"  {key}: {protected_response[key]} ({type(protected_response[key]).__name__})")

if __name__ == "__main__":
    print("🔍 STT 엔드포인트 응답 구조 비교 테스트")
    print("="*70)
    
    # 두 엔드포인트 테스트
    general_response = test_general_transcribe()
    protected_response = test_protected_transcribe()
    
    # 응답 비교
    compare_responses(general_response, protected_response)
    
    print("\n📊 테스트 완료!")