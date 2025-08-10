from sqlalchemy.orm import Session
from database import User, get_db

def check_users_in_db():
    """데이터베이스에 저장된 사용자들을 확인합니다."""
    db = next(get_db())
    
    try:
        # 모든 사용자 조회
        users = db.query(User).all()
        
        print(f"📊 users 테이블: {len(users)}개 레코드")
        
        if users:
            print("\n사용자 목록:")
            for i, user in enumerate(users, 1):
                print(f"{i}. ID: {user.id}")
                print(f"   사용자 ID: {user.user_id}")
                print(f"   이메일: {user.email}")
                print(f"   이름: {user.name}")
                print(f"   사용구분: {user.user_type}")
                print(f"   전화번호: {user.phone_number}")
                print(f"   활성상태: {user.is_active}")
                print(f"   생성일시: {user.created_at}")
                print(f"   수정일시: {user.updated_at}")
                print()
        else:
            print("저장된 사용자가 없습니다.")
            
    except Exception as e:
        print(f"❌ 데이터베이스 조회 오류: {e}")
    finally:
        db.close()
        print("✅ 데이터베이스 조회 완료")

if __name__ == "__main__":
    check_users_in_db()