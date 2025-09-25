#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
테스트 사용자 이메일 업데이트 스크립트
"""

import sys
import os

# core 디렉토리를 sys.path에 추가
core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core')
sys.path.insert(0, core_path)

from sqlalchemy.orm import sessionmaker

# core 디렉토리에서 직접 import
os.chdir(core_path)
from database import User, engine

# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def main():
    print("📧 테스트 사용자 이메일 업데이트")
    print("=" * 50)
    
    # 데이터베이스 연결
    db = SessionLocal()
    
    try:
        # test_lock_user 조회
        user = db.query(User).filter(User.user_id == "test_lock_user").first()
        
        if not user:
            print("❌ test_lock_user를 찾을 수 없습니다.")
            return
            
        print(f"=== 현재 사용자 정보 ===")
        print(f"  사용자 ID: {user.user_id}")
        print(f"  현재 이메일: {user.email}")
        print(f"  사용자명: {user.name}")
        
        # 이메일 업데이트
        old_email = user.email
        new_email = "stttest01@g.com"
        
        user.email = new_email
        db.commit()
        
        print(f"\n=== 이메일 업데이트 완료 ===")
        print(f"  이전 이메일: {old_email}")
        print(f"  새 이메일: {new_email}")
        print(f"  ✅ 이메일이 성공적으로 업데이트되었습니다.")
        
        # 업데이트 확인
        updated_user = db.query(User).filter(User.user_id == "test_lock_user").first()
        print(f"\n=== 업데이트 확인 ===")
        print(f"  확인된 이메일: {updated_user.email}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()