import requests
import json
from datetime import datetime

# 서버 URL
BASE_URL = "http://localhost:8000"

def test_token_api():
    """
    토큰 API 전체 테스트
1. JWT 토큰 기반 로그인
2. API 키 발행 ( POST /tokens/{token_id} )
3. API 키 검증 ( GET /tokens/verify )
4. 토큰 목록 조회 ( GET /tokens/ )
5. 토큰 사용 내역 조회 ( GET /tokens/history )

    """
    print("🧪 토큰 API 테스트 시작")
    print("=" * 50)
    
    # 1. 로그인하여 JWT 토큰 획득
    print("\n1️⃣ 로그인 테스트")
    login_data = {
        "email": "test_01@sample.com",
        "password": "test"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"로그인 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            login_result = response.json()
            access_token = login_result["access_token"]
            print(f"✅ 로그인 성공")
            print(f"JWT 토큰: {access_token}")
        else:
            print(f"❌ 로그인 실패: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ 로그인 오류: {e}")
        return
    
    # 인증 헤더 설정
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # 2. API 키 발행 테스트
    print("\n2️⃣ API 키 발행 테스트")
    token_id = f"test_token_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        response = requests.post(
            f"{BASE_URL}/tokens/{token_id}",
            params={"description": "테스트용 API 키"},
            headers=headers
        )
        print(f"API 키 발행 응답 상태: {response.status_code}")
        print(f"응답 내용: {response.text}")
        
        if response.status_code == 200:
            try:
                token_result = response.json()
                print(f"파싱된 응답: {token_result}")
                
                if "api_key" in token_result:
                    api_key = token_result["api_key"]
                    print(f"✅ API 키 발행 성공")
                    print(f"토큰 ID: {token_result.get('token_id', 'N/A')}")
                    print(f"API 키: {api_key[:20]}...")
                    print(f"설명: {token_result.get('description', 'N/A')}")
                else:
                    print(f"❌ 응답에 api_key가 없음: {token_result}")
                    return
            except json.JSONDecodeError as je:
                print(f"❌ JSON 파싱 오류: {je}")
                print(f"원본 응답: {response.text}")
                return
        else:
            print(f"❌ API 키 발행 실패: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ API 키 발행 오류: {e}")
        return
    
    # 3. API 키 검증 테스트
    print("\n3️⃣ API 키 검증 테스트")
    api_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/tokens/verify", headers=api_headers)
        print(f"API 키 검증 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            verify_result = response.json()
            print(f"✅ API 키 검증 성공")
            print(f"사용자 UUID: {verify_result['user_uuid']}")
        else:
            print(f"❌ API 키 검증 실패: {response.text}")
            
    except Exception as e:
        print(f"❌ API 키 검증 오류: {e}")
    
    # 4. 토큰 목록 조회 테스트
    print("\n4️⃣ 토큰 목록 조회 테스트")
    try:
        response = requests.get(f"{BASE_URL}/tokens/", headers=headers)
        print(f"토큰 목록 조회 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            tokens_result = response.json()
            print(f"✅ 토큰 목록 조회 성공")
            print(f"토큰 수: {tokens_result['total_count']}")
            for token in tokens_result['tokens']:
                print(f"  - {token['token_id']}: {token['token_name']} (활성: {token['is_active']})")
        else:
            print(f"❌ 토큰 목록 조회 실패: {response.text}")
            
    except Exception as e:
        print(f"❌ 토큰 목록 조회 오류: {e}")
    
    # 5. 토큰 사용 내역 조회 테스트
    print("\n5️⃣ 토큰 사용 내역 조회 테스트")
    try:
        response = requests.get(f"{BASE_URL}/tokens/history", headers=headers)
        print(f"토큰 사용 내역 조회 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            history_result = response.json()
            print(f"✅ 토큰 사용 내역 조회 성공")
            print(f"내역 수: {history_result['total_count']}")
            for history in history_result['history'][:3]:  # 최근 3개만 출력
                print(f"  - {history['action']}: {history['token_id']} ({history['timestamp']})")
        else:
            print(f"❌ 토큰 사용 내역 조회 실패: {response.text}")
            
    except Exception as e:
        print(f"❌ 토큰 사용 내역 조회 오류: {e}")
    
    print("\n" + "=" * 50)
    print("🧪 토큰 API 테스트 완료")

if __name__ == "__main__":
    test_token_api()