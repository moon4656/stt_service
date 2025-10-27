import requests
import json
import os
from datetime import datetime

# 테스트 설정
BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword123"

def test_tokens_history_api():
    """
    /tokens/history API 엔드포인트를 테스트합니다.
    """
    print("🧪 /tokens/history API 테스트 시작")
    print("=" * 50)
    
    # 1. 로그인하여 JWT 토큰 획득
    print("\n1️⃣ 사용자 로그인 중...")
    login_data = {
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    }
    
    try:
        login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"로그인 응답 상태: {login_response.status_code}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            access_token = login_result.get("access_token")
            print(f"✅ 로그인 성공 - 토큰 획득")
            print(f"토큰 타입: {login_result.get('token_type')}")
        else:
            print(f"❌ 로그인 실패: {login_response.text}")
            return
            
    except Exception as e:
        print(f"❌ 로그인 요청 중 오류: {e}")
        return
    
    # 2. JWT 토큰으로 /tokens/history API 호출
    print("\n2️⃣ 토큰 사용 내역 조회 중...")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # 기본 조회 (limit=50)
    try:
        history_response = requests.get(f"{BASE_URL}/tokens/history", headers=headers)
        print(f"API 응답 상태: {history_response.status_code}")
        
        if history_response.status_code == 200:
            history_result = history_response.json()
            print(f"✅ 토큰 사용 내역 조회 성공")
            print(f"응답 상태: {history_result.get('status')}")
            
            history_data = history_result.get('history', [])
            print(f"📊 조회된 내역 수: {len(history_data)}건")
            
            # 내역이 있는 경우 첫 번째 항목 출력
            if history_data:
                print("\n📋 첫 번째 사용 내역:")
                first_item = history_data[0]
                for key, value in first_item.items():
                    print(f"  - {key}: {value}")
            else:
                print("📝 사용 내역이 없습니다.")
                
        else:
            print(f"❌ API 호출 실패: {history_response.text}")
            
    except Exception as e:
        print(f"❌ API 호출 중 오류: {e}")
    
    # 3. limit 파라미터를 사용한 조회 테스트
    print("\n3️⃣ limit 파라미터 테스트 (limit=10)...")
    try:
        limited_response = requests.get(f"{BASE_URL}/tokens/history?limit=10", headers=headers)
        print(f"API 응답 상태: {limited_response.status_code}")
        
        if limited_response.status_code == 200:
            limited_result = limited_response.json()
            limited_history = limited_result.get('history', [])
            print(f"✅ 제한된 조회 성공 - 조회된 내역 수: {len(limited_history)}건")
        else:
            print(f"❌ 제한된 조회 실패: {limited_response.text}")
            
    except Exception as e:
        print(f"❌ 제한된 조회 중 오류: {e}")
    
    # 4. 잘못된 토큰으로 테스트 (인증 실패 테스트)
    print("\n4️⃣ 잘못된 토큰으로 인증 실패 테스트...")
    invalid_headers = {
        "Authorization": "Bearer invalid_token_here",
        "Content-Type": "application/json"
    }
    
    try:
        invalid_response = requests.get(f"{BASE_URL}/tokens/history", headers=invalid_headers)
        print(f"API 응답 상태: {invalid_response.status_code}")
        
        if invalid_response.status_code == 401:
            print(f"✅ 예상된 인증 실패 - 상태 코드: {invalid_response.status_code}")
        else:
            print(f"⚠️ 예상과 다른 응답: {invalid_response.text}")
            
    except Exception as e:
        print(f"❌ 인증 실패 테스트 중 오류: {e}")
    
    # 5. 토큰 없이 호출 테스트
    print("\n5️⃣ 토큰 없이 호출 테스트...")
    try:
        no_token_response = requests.get(f"{BASE_URL}/tokens/history")
        print(f"API 응답 상태: {no_token_response.status_code}")
        
        if no_token_response.status_code == 401:
            print(f"✅ 예상된 인증 실패 - 상태 코드: {no_token_response.status_code}")
        else:
            print(f"⚠️ 예상과 다른 응답: {no_token_response.text}")
            
    except Exception as e:
        print(f"❌ 토큰 없는 호출 테스트 중 오류: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 /tokens/history API 테스트 완료")

def test_tokens_history_with_existing_user():
    """
    기존 사용자 계정으로 토큰 히스토리 테스트
    """
    print("\n🔍 기존 사용자로 토큰 히스토리 상세 테스트")
    print("=" * 50)
    
    # 실제 존재하는 사용자 정보로 테스트
    # 환경에 맞게 수정 필요
    existing_user_email = "user@example.com"  # 실제 존재하는 이메일로 변경
    existing_user_password = "password123"    # 실제 비밀번호로 변경
    
    login_data = {
        "email": existing_user_email,
        "password": existing_user_password
    }
    
    try:
        # 로그인
        login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if login_response.status_code != 200:
            print(f"❌ 기존 사용자 로그인 실패: {login_response.text}")
            return
            
        access_token = login_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 다양한 limit 값으로 테스트
        for limit in [5, 20, 100]:
            print(f"\n📊 limit={limit}으로 조회 중...")
            response = requests.get(f"{BASE_URL}/tokens/history?limit={limit}", headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                history_count = len(result.get('history', []))
                print(f"✅ 조회 성공 - {history_count}건 조회됨")
            else:
                print(f"❌ 조회 실패: {response.text}")
                
    except Exception as e:
        print(f"❌ 기존 사용자 테스트 중 오류: {e}")

if __name__ == "__main__":
    print("🚀 토큰 히스토리 API 테스트 시작")
    print(f"📡 테스트 대상 서버: {BASE_URL}")
    print(f"⏰ 테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 기본 테스트 실행
    test_tokens_history_api()
    
    # 기존 사용자 테스트 (선택적)
    # test_tokens_history_with_existing_user()
    
    print(f"\n⏰ 테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")