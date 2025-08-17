import os
import sys
from sqlalchemy.orm import Session
from database import get_db, User
from auth import hash_password

def update_existing_users_password():
    """기존 사용자들의 패스워드를 'password'로 설정"""
    db = next(get_db())
    
    try:
        # 모든 사용자 조회
        users = db.query(User).all()
        
        if not users:
            print("데이터베이스에 사용자가 없습니다.")
            return
        
        # 기본 패스워드 해시화
        default_password_hash = hash_password("password")
        
        updated_count = 0
        for user in users:
            # password_hash 필드가 없거나 None인 경우 업데이트
            if not hasattr(user, 'password_hash') or user.password_hash is None:
                user.password_hash = default_password_hash
                updated_count += 1
                print(f"사용자 {user.user_id}의 패스워드를 업데이트했습니다.")
        
        if updated_count > 0:
            db.commit()
            print(f"\n총 {updated_count}명의 사용자 패스워드를 업데이트했습니다.")
        else:
            print("업데이트할 사용자가 없습니다. 모든 사용자가 이미 패스워드를 가지고 있습니다.")
            
    except Exception as e:
        print(f"오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("기존 사용자들의 패스워드를 'password'로 설정합니다...")
    update_existing_users_password()
    print("완료!")