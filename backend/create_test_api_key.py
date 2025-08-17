import requests
import json

# 서버 URL
BASE_URL = "http://localhost:8001"

def create_and_test_api_key():
    """새로운 API 키 생성 및 테스트"""
    print("=== 새로운 API 키 생성 및 테스트 ===")
    
    # 1. 사용자 로그인 (JWT 토큰 획득)
    print("\n1. 사용자 로그인")
    login_data = {
        "user_id": "test_01",
        "password": "password"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"로그인 Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ 로그인 실패: {response.text}")
            return
        
        jwt_token = response.json()["access_token"]
        print(f"✅ JWT 토큰 획득: {jwt_token[:50]}...")
        
        # 2. API 키 생성
        print("\n2. API 키 생성")
        headers = {"Authorization": f"Bearer {jwt_token}"}
        import random
        token_id = f"debug_test_token_{random.randint(1000, 9999)}"
        
        response = requests.post(
            f"{BASE_URL}/tokens/{token_id}",
            headers=headers,
            params={"description": "디버깅용 테스트 토큰"}
        )
        
        print(f"API 키 생성 Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ API 키 생성 실패: {response.text}")
            return
        
        api_key = response.json()["token"]["api_key"]
        print(f"✅ API 키 생성 성공: {api_key}")
        
        # 3. API 키 검증 테스트
        print("\n3. API 키 검증 테스트")
        api_headers = {"Authorization": f"Bearer {api_key}"}
        
        response = requests.get(f"{BASE_URL}/tokens/verify", headers=api_headers)
        print(f"API 키 검증 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API 키 검증 성공")
            print(f"응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ API 키 검증 실패: {response.text}")
        
        # 4. 보호된 엔드포인트 테스트 (파일 없이)
        print("\n4. 보호된 엔드포인트 접근 테스트")
        
        response = requests.post(f"{BASE_URL}/transcribe/protected/", headers=api_headers)
        print(f"보호된 엔드포인트 Status Code: {response.status_code}")
        
        if response.status_code == 422:  # 파일이 없어서 발생하는 검증 오류는 정상
            print("✅ API 키 인증 성공 (파일 검증 오류는 정상)")
        elif response.status_code == 401:
            print(f"❌ API 키 인증 실패: {response.text}")
        else:
            print(f"응답: {response.text}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    create_and_test_api_key()