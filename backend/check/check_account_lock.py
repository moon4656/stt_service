import requests
import json
import time
from datetime import datetime

# 서버 URL
BASE_URL = "http://localhost:8000"

def test_account_lock_functionality():
    """계정 잠금 기능 테스트"""
    print("\n=== 계정 잠금 기능 테스트 시작 ===")
    
    # 테스트용 사용자 (실제 존재하는 사용자 이메일로 변경)
    test_email = "test@example.com"  # 실제 사용자 이메일로 변경
    wrong_password = "wrong_password"
    
    print(f"테스트 대상: {test_email}")
    
    # 1단계: 5회 연속 로그인 실패 테스트
    print("\n--- 1단계: 5회 연속 로그인 실패 테스트 ---")
    
    for attempt in range(1, 6):
        login_data = {
            "email": test_email,
            "password": wrong_password
        }
        
        try:
            response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
            print(f"시도 {attempt}: Status {response.status_code}")
            
            if response.status_code == 401:
                error_data = response.json()
                print(f"  메시지: {error_data.get('detail', 'Unknown error')}")
            elif response.status_code == 423:
                error_data = response.json()
                print(f"  🔒 계정 잠금됨: {error_data.get('detail', 'Account locked')}")
                break
            
            time.sleep(1)  # 1초 대기
            
        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
    
    # 2단계: 계정 잠금 상태에서 로그인 시도
    print("\n--- 2단계: 계정 잠금 상태에서 로그인 시도 ---")
    
    # 올바른 비밀번호로도 로그인 시도
    correct_login_data = {
        "email": test_email,
        "password": "password"  # 실제 비밀번호로 변경
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=correct_login_data)
        print(f"올바른 비밀번호 시도: Status {response.status_code}")
        
        if response.status_code == 423:
            error_data = response.json()
            print(f"  🔒 예상대로 계정 잠금 유지: {error_data.get('detail')}")
        else:
            print(f"  ⚠️ 예상과 다른 결과: {response.text}")
            
    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
    
    print("\n--- 테스트 완료 ---")
    print("💡 30분 후 자동 해제 기능을 테스트하려면 시간을 기다리거나")
    print("   데이터베이스에서 직접 locked_at 시간을 수정하세요.")

def test_manual_unlock():
    """수동 계정 잠금 해제 테스트 (관리자 기능)"""
    print("\n=== 수동 계정 잠금 해제 테스트 ===")
    
    # 관리자 토큰이 필요한 경우
    # admin_token = "your_admin_token_here"
    # headers = {"Authorization": f"Bearer {admin_token}"}
    
    test_email = "test@example.com"  # 실제 사용자 이메일로 변경
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/unlock-account",
            params={"email": test_email}
            # headers=headers  # 관리자 권한이 필요한 경우
        )
        
        print(f"계정 잠금 해제 시도: Status {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ 성공: {result.get('message')}")
        else:
            print(f"  ❌ 실패: {response.text}")
            
    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")

if __name__ == "__main__":
    print("계정 잠금 기능 테스트")
    print("⚠️  주의: 실제 사용자 계정으로 테스트하기 전에 테스트용 계정을 사용하세요!")
    
    # 테스트 실행
    test_account_lock_functionality()
    
    # 수동 해제 테스트 (필요시)
    # test_manual_unlock()