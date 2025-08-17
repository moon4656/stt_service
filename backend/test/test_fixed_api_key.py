import requests
import sys
sys.path.append('.')
from database import get_db, APIToken

def test_api_key_verification():
    """수정된 API 키 검증 테스트"""
    print("=== 수정된 API 키 검증 테스트 ===")
    
    # 1. 새로운 API 키 생성 및 테스트
    print("\n1. 새로운 API 키 생성 및 테스트...")
    
    # 로그인해서 JWT 토큰 획득
    print("로그인 시도...")
    login_response = requests.post(
        "http://localhost:8001/auth/login",
        json={"user_id": "test_01", "password": "password"}
    )
    
    print(f"로그인 응답 코드: {login_response.status_code}")
    if login_response.status_code != 200:
        print(f"로그인 응답: {login_response.text}")
        # 다른 사용자로 시도
        print("\n다른 사용자로 로그인 시도...")
        login_response = requests.post(
            "http://localhost:8001/auth/login",
            json={"user_id": "test_personal_kr", "password": "password"}
        )
        print(f"두 번째 로그인 응답 코드: {login_response.status_code}")
        if login_response.status_code != 200:
            print(f"두 번째 로그인 응답: {login_response.text}")
    
    if login_response.status_code != 200:
        print(f"❌ 로그인 실패: {login_response.status_code}")
        return
    
    jwt_token = login_response.json()["access_token"]
    print(f"✅ JWT 토큰 획득: {jwt_token[:20]}...")
    
    # 새 API 키 생성
    import time
    unique_token_id = f"test_token_{int(time.time())}"
    print(f"API 키 생성 중... (토큰 ID: {unique_token_id})")
    
    create_response = requests.post(
        f"http://localhost:8001/tokens/{unique_token_id}",
        headers={"Authorization": f"Bearer {jwt_token}"},
        params={"description": "Fixed API key test"}
    )
    
    if create_response.status_code != 200:
        print(f"❌ API 키 생성 실패: {create_response.status_code}")
        print(f"응답: {create_response.text}")
        return
    
    print("✅ API 키 생성 성공")
    response_data = create_response.json()
    print(f"응답 데이터: {response_data}")
    
    # 응답에서 API 키 추출 (정확한 구조: {"status": "success", "token": {"api_key": "...", ...}})
    if response_data.get("status") == "success" and "token" in response_data:
        api_key = response_data["token"].get("api_key")
    else:
        api_key = None
    
    if not api_key:
        print(f"❌ API 키를 찾을 수 없음. 응답: {response_data}")
        return
    
    print(f"생성된 API 키: {api_key[:20]}...")
    
    # 3. API 키 검증 테스트
    print("\n3. API 키 검증 테스트")
    print(f"사용할 API 키: {api_key}")
    verify_response = requests.get(
        "http://localhost:8001/tokens/verify",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    
    print(f"검증 Status Code: {verify_response.status_code}")
    if verify_response.status_code == 200:
        print(f"✅ API 키 검증 성공: {verify_response.json()}")
    else:
        print(f"❌ API 키 검증 실패: {verify_response.text}")
        
        # API 키가 유효하지 않은 경우 추가 디버깅
        print("\n=== 디버깅: 데이터베이스에서 API 키 확인 ===")
        from auth import TokenManager
        
        db = next(get_db())
        # 데이터베이스에서 API 키 확인
        tokens = db.query(APIToken).filter(APIToken.is_active == True).all()
        print(f"활성 토큰 수: {len(tokens)}")
        for token in tokens:
            print(f"토큰 ID: {token.token_id}, user_uuid: {token.user_uuid}")
        
        # API 키 해시 확인
        import hashlib
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        matching_token = db.query(APIToken).filter(APIToken.token_key == api_key_hash).first()
        if matching_token:
            print(f"매칭되는 토큰 발견: {matching_token.token_id}, user_uuid: {matching_token.user_uuid}")
        else:
            print("매칭되는 토큰을 찾을 수 없습니다.")
        
        db.close()
    
    # 4. 보호된 엔드포인트 테스트
    print("\n4. 보호된 엔드포인트 테스트")
    protected_response = requests.post(
        "http://localhost:8001/transcribe/protected/",
        headers={"Authorization": f"Bearer {api_key}"},
        files={"file": ("test.txt", "test content", "text/plain")}
    )
    
    print(f"보호된 엔드포인트 Status Code: {protected_response.status_code}")
    if protected_response.status_code == 422:
        print("✅ API 키 인증 성공 (파일 형식 오류는 정상)")
    elif protected_response.status_code == 401:
        print(f"❌ API 키 인증 실패: {protected_response.text}")
    else:
        print(f"응답: {protected_response.text}")

if __name__ == "__main__":
    test_api_key_verification()