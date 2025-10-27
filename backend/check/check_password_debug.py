#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
패스워드 검증 디버그 스크립트
"""

import sys
import os

# core 디렉토리를 sys.path에 추가
core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core')
sys.path.insert(0, core_path)

import bcrypt
from sqlalchemy.orm import sessionmaker

# core 디렉토리에서 직접 import
os.chdir(core_path)
from database import User, engine

# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """패스워드 검증"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def main():
    print("🔍 패스워드 검증 디버그 테스트 시작")
    print("=" * 50)
    
    # 데이터베이스 연결
    db = SessionLocal()
    
    try:
        # test_lock_user 조회
        user = db.query(User).filter(User.user_id == "test_lock_user").first()
        
        if not user:
            print("❌ test_lock_user를 찾을 수 없습니다.")
            return
            
        print(f"=== 사용자 정보 ===")
        print(f"  사용자 ID: {user.user_id}")
        print(f"  이메일: {user.email}")
        print(f"  패스워드 해시: {user.password_hash[:50]}...")
        print(f"  실패 횟수: {user.failed_login_attempts}")
        print(f"  계정 잠금: {user.is_locked}")
        
        # 다양한 패스워드로 테스트
        test_passwords = [
            "correct_password",
            "testpassword123",
            "password123", 
            "test123",
            "123456",
            "testuser"
        ]
        
        print(f"\n=== 패스워드 검증 테스트 ===")
        for password in test_passwords:
            is_valid = verify_password(password, user.password_hash)
            print(f"  패스워드 '{password}': {'✅ 일치' if is_valid else '❌ 불일치'}")
            if is_valid:
                print(f"  🎉 올바른 패스워드를 찾았습니다: {password}")
                break
        
        # bcrypt로 직접 검증도 해보기
        print(f"\n=== bcrypt 직접 검증 ===")
        for password in test_passwords:
            try:
                is_valid = bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8'))
                print(f"  bcrypt 패스워드 '{password}': {'✅ 일치' if is_valid else '❌ 불일치'}")
                if is_valid:
                    print(f"  🎉 bcrypt로 올바른 패스워드를 찾았습니다: {password}")
                    break
            except Exception as e:
                print(f"  bcrypt 오류 '{password}': {e}")
                
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()