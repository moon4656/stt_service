import sys
import os
# core 디렉토리를 먼저 추가
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))
# 상위 디렉토리(backend)를 sys.path에 추가하여 core 모듈에 접근
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
from datetime import datetime
from database import get_db, User
from auth import create_user, hash_password

BASE_URL = "http://localhost:8000"

def check_database_users():
    """데이터베이스에 있는 사용자 확인"""
    print("=== 데이터베이스 사용자 확인 ===")
    db = next(get_db())
    
    try:
        users = db.query(User).all()
        print(f"총 {len(users)}명의 사용자가 있습니다.")
        
        for user in users:
            print(f"\n사용자 ID: {user.user_id}")
            print(f"이메일: {user.email}")
            print(f"이름: {user.name}")
            print(f"활성화: {user.is_active}")
            print(f"로그인 실패 횟수: {user.failed_login_attempts}")
            print(f"계정 잠금: {user.is_locked}")
            print(f"잠금 시간: {user.locked_at}")
            print(f"마지막 실패 로그인: {user.last_failed_login}")
            print("-" * 50)
            
        return users
    except Exception as e:
        print(f"오류 발생: {e}")
        return []
    finally:
        db.close()

def create_test_user():
    """테스트용 사용자 생성"""
    print("\n=== 테스트 사용자 생성 ===")
    db = next(get_db())
    
    try:
        # 기존 테스트 사용자 삭제
        existing_user = db.query(User).filter(User.user_id == "test_lock_user").first()
        if existing_user:
            db.delete(existing_user)
            db.commit()
            print("기존 테스트 사용자 삭제됨")
        
        # 새 테스트 사용자 생성
        test_user = User(
            user_id="test_lock_user",
            email="test_lock@example.com",
            name="테스트 잠금 사용자",
            user_type="A01",
            password_hash=hash_password("correct_password"),
            is_active=True,
            failed_login_attempts=0,
            is_locked=False,
            locked_at=None,
            last_failed_login=None
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print(f"테스트 사용자 생성 완료: {test_user.user_id}")
        return test_user
        
    except Exception as e:
        print(f"테스트 사용자 생성 오류: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def test_login_failures():
    """로그인 실패 테스트"""
    print("\n=== 로그인 실패 테스트 시작 ===")
    
    # 잘못된 패스워드로 5번 로그인 시도
    for i in range(1, 6):
        print(f"\n--- {i}번째 로그인 실패 시도 ---")
        
        login_data = {
            "email": "test_lock@example.com",
            "password": "wrong_password"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/auth/login", json=login_data, timeout=10)
            print(f"응답 상태 코드: {response.status_code}")
            print(f"응답 내용: {response.text}")
            
            # 데이터베이스에서 사용자 상태 확인
            check_user_status_after_attempt()
            
        except requests.exceptions.RequestException as e:
            print(f"요청 오류: {e}")
            print("서버가 실행 중인지 확인해주세요.")
            break

def check_user_status_after_attempt():
    """로그인 시도 후 사용자 상태 확인"""
    db = next(get_db())
    
    try:
        user = db.query(User).filter(User.user_id == "test_lock_user").first()
        if user:
            print(f"  현재 실패 횟수: {user.failed_login_attempts}")
            print(f"  계정 잠금 상태: {user.is_locked}")
            print(f"  잠금 시간: {user.locked_at}")
            print(f"  마지막 실패 시간: {user.last_failed_login}")
        else:
            print("  사용자를 찾을 수 없습니다.")
    except Exception as e:
        print(f"  상태 확인 오류: {e}")
    finally:
        db.close()

def test_successful_login_after_lock():
    """계정 잠금 후 올바른 패스워드로 로그인 시도"""
    print("\n=== 계정 잠금 후 올바른 패스워드 로그인 테스트 ===")
    
    login_data = {
        "email": "test_lock@example.com",
        "password": "correct_password"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data, timeout=10)
        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        
        if response.status_code == 423:
            print("✅ 계정 잠금이 정상적으로 작동하고 있습니다.")
        elif response.status_code == 200:
            print("⚠️ 계정이 잠기지 않았거나 이미 해제되었습니다.")
        else:
            print(f"⚠️ 예상하지 못한 응답: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"요청 오류: {e}")

def main():
    """메인 테스트 함수"""
    print("🔒 계정 잠금 기능 디버그 테스트 시작")
    print(f"서버 URL: {BASE_URL}")
    print(f"테스트 시간: {datetime.now()}")
    
    # 1. 현재 데이터베이스 사용자 확인
    users = check_database_users()
    
    # 2. 테스트 사용자 생성
    test_user = create_test_user()
    if not test_user:
        print("❌ 테스트 사용자 생성 실패. 테스트를 중단합니다.")
        return
    
    # 3. 로그인 실패 테스트
    test_login_failures()
    
    # 4. 계정 잠금 후 올바른 패스워드 테스트
    test_successful_login_after_lock()
    
    # 5. 최종 사용자 상태 확인
    print("\n=== 최종 사용자 상태 ===")
    check_user_status_after_attempt()
    
    print("\n🔒 계정 잠금 기능 디버그 테스트 완료")

if __name__ == "__main__":
    main()