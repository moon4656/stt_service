#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
계정 잠금 해제 기능 디버그 테스트 스크립트

이 스크립트는 계정 잠금 해제 기능을 테스트합니다:
1. 잠긴 계정의 locked_at 시간을 30분 전으로 수정
2. 올바른 패스워드로 로그인 시도
3. 계정이 자동으로 해제되는지 확인
"""

import sys
import os

# 상위 디렉토리(backend)를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from database import get_db, User
from auth import authenticate_user
import requests
from datetime import datetime, timedelta

def test_account_unlock():
    """계정 잠금 해제 테스트"""
    print("🔓 계정 잠금 해제 기능 디버그 테스트 시작")
    print("=" * 50)
    
    # 데이터베이스 연결
    db = next(get_db())
    
    try:
        # 테스트 사용자 조회
        user = db.query(User).filter(User.user_id == "test_lock_user").first()
        
        if not user:
            print("❌ 테스트 사용자를 찾을 수 없습니다.")
            return
        
        print("=== 현재 계정 상태 ===")
        print(f"  현재 실패 횟수: {user.failed_login_attempts}")
        print(f"  계정 잠금 상태: {user.is_locked}")
        print(f"  잠금 시간: {user.locked_at}")
        print(f"  마지막 실패 시간: {user.last_failed_login}")
        
        if not user.is_locked:
            print("❌ 계정이 잠겨있지 않습니다. 먼저 계정을 잠그세요.")
            return
        
        # 잠금 시간을 30분 전으로 수정 (자동 해제 조건 만족)
        old_locked_at = user.locked_at
        user.locked_at = datetime.now() - timedelta(minutes=31)  # 31분 전으로 설정
        db.commit()
        
        print("\n=== 잠금 시간 수정 ===")
        print(f"  기존 잠금 시간: {old_locked_at}")
        print(f"  수정된 잠금 시간: {user.locked_at}")
        print("  (31분 전으로 설정하여 자동 해제 조건 만족)")
        
        # 올바른 패스워드로 로그인 테스트
        print("\n=== 올바른 패스워드로 로그인 테스트 ===")
        
        login_data = {
            "email": "test_lock@example.com",
            "password": "testpassword123"
        }
        
        try:
            response = requests.post(
                "http://localhost:8000/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"응답 상태 코드: {response.status_code}")
            print(f"응답 내용: {response.text}")
            
            if response.status_code == 200:
                print("✅ 로그인 성공! 계정 잠금이 자동으로 해제되었습니다.")
            elif response.status_code == 423:
                print("❌ 계정이 여전히 잠겨있습니다. 자동 해제가 작동하지 않았습니다.")
            else:
                print(f"❌ 예상치 못한 응답: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 요청 오류: {e}")
        
        # 최종 사용자 상태 확인
        print("\n=== 최종 사용자 상태 ===")
        db.refresh(user)
        print(f"  현재 실패 횟수: {user.failed_login_attempts}")
        print(f"  계정 잠금 상태: {user.is_locked}")
        print(f"  잠금 시간: {user.locked_at}")
        print(f"  마지막 실패 시간: {user.last_failed_login}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    print("\n🔓 계정 잠금 해제 기능 디버그 테스트 완료")

if __name__ == "__main__":
    test_account_unlock()