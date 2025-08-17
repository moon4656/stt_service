#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db, User
from auth import create_user
import uuid

def test_existing_users_uuid():
    """기존 사용자들의 UUID 확인"""
    print("=== 기존 사용자들의 UUID 확인 ===")
    db = next(get_db())
    
    users = db.query(User).all()
    for user in users:
        print(f"사용자 ID: {user.user_id}, UUID: {user.user_uuid}, 이름: {user.name}")
    
    print(f"\n총 {len(users)}명의 사용자가 있습니다.")
    db.close()

def test_new_user_creation():
    """새 사용자 생성 시 UUID 자동 생성 테스트"""
    print("\n=== 새 사용자 생성 테스트 ===")
    
    # 테스트용 사용자 ID 생성
    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    test_email = f"{test_user_id}@test.com"
    
    try:
        # 새 사용자 생성
        user_info = create_user(
            user_id=test_user_id,
            email=test_email,
            name="테스트 사용자",
            user_type="개인",
            password="test123",
            phone_number="010-1234-5678"
        )
        
        print(f"새 사용자 생성 성공!")
        print(f"사용자 ID: {test_user_id}")
        
        # 데이터베이스에서 실제 UUID 확인
        db = next(get_db())
        created_user = db.query(User).filter(User.user_id == test_user_id).first()
        if created_user:
            print(f"생성된 UUID: {created_user.user_uuid}")
            print(f"UUID 길이: {len(created_user.user_uuid)}")
            
            # UUID 형식 검증
            try:
                uuid.UUID(created_user.user_uuid)
                print("✅ UUID 형식이 올바릅니다.")
            except ValueError:
                print("❌ UUID 형식이 올바르지 않습니다.")
        else:
            print("❌ 생성된 사용자를 찾을 수 없습니다.")
        
        db.close()
        
    except Exception as e:
        print(f"❌ 사용자 생성 실패: {e}")

if __name__ == "__main__":
    test_existing_users_uuid()
    test_new_user_creation()