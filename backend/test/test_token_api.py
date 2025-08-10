import requests
import json

# API 베이스 URL
BASE_URL = "http://localhost:8000"

def test_token_apis():
    """토큰 관리 API 테스트"""
    
    print("=== 토큰 관리 API 테스트 시작 ===")
    
    # 1. 사용자 생성
    print("\n1. 사용자 생성 테스트")
    user_data = {
        "user_id": "test_user_001",
        "email": "test@example.com",
        "name": "테스트 사용자"
    }
    
    response = requests.post(f"{BASE_URL}/users/", json=user_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code != 200 and response.status_code != 400:
        print("사용자 생성 실패")
        return
    
    if response.status_code == 400:
        print("사용자가 이미 존재합니다. 기존 사용자로 진행합니다.")
    
    # 2. 로그인 (JWT 토큰 발급)
    print("\n2. 로그인 테스트 (JWT 토큰 발급)")
    login_data = {
        "user_id": "test_user_001"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code != 200:
        print("로그인 실패")
        return
    
    jwt_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {jwt_token}"}
    
    # 3. API 키 발행
    print("\n3. API 키 발행 테스트")
    token_id = "test_token_001"
    description = "테스트용 API 키"
    
    params = {"description": description}
    response = requests.post(f"{BASE_URL}/tokens/{token_id}", params=params, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code != 200:
        print("API 키 발행 실패")
        return
    
    api_key = response.json()["token"]["api_key"]
    api_key_hash = response.json()["token"]["api_key_hash"]
    api_headers = {"Authorization": f"Bearer {api_key}"}
    
    # 4. API 키 검증
    print("\n4. API 키 검증 테스트")
    response = requests.get(f"{BASE_URL}/tokens/verify", headers=api_headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # 5. 사용자 토큰 목록 조회
    print("\n5. 사용자 토큰 목록 조회 테스트")
    response = requests.get(f"{BASE_URL}/tokens/", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # 6. 토큰 사용 내역 조회
    print("\n6. 토큰 사용 내역 조회 테스트")
    response = requests.get(f"{BASE_URL}/tokens/history", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # 7. API 키로 보호된 transcribe 엔드포인트 테스트 (파일 없이)
    print("\n7. API 키로 보호된 transcribe 엔드포인트 접근 테스트")
    try:
        # 실제 파일 없이 엔드포인트 접근만 테스트
        response = requests.post(f"{BASE_URL}/transcribe/protected/", headers=api_headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 8. API 키 비활성화
    print("\n8. API 키 비활성화 테스트")
    revoke_data = {
        "api_key_hash": api_key_hash
    }
    
    response = requests.post(f"{BASE_URL}/tokens/revoke", json=revoke_data, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # 9. 비활성화된 API 키로 접근 시도
    print("\n9. 비활성화된 API 키로 접근 시도")
    response = requests.get(f"{BASE_URL}/tokens/verify", headers=api_headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    print("\n=== 토큰 관리 API 테스트 완료 ===")

if __name__ == "__main__":
    test_token_apis()