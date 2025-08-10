from sqlalchemy.orm import Session
from database import get_db, User
from auth import verify_password

def check_passwords_in_database():
    """데이터베이스의 패스워드 해시 확인"""
    db = next(get_db())
    
    try:
        # 모든 사용자 조회
        users = db.query(User).all()
        
        print(f"총 {len(users)}명의 사용자가 있습니다.\n")
        
        for user in users:
            print(f"사용자 ID: {user.user_id}")
            print(f"이름: {user.name}")
            print(f"패스워드 해시: {user.password_hash[:50]}..." if user.password_hash else "패스워드 해시 없음")
            
            # 기존 사용자들의 기본 패스워드 'password' 검증
            if user.user_id != 'test_password_user' and user.password_hash:
                is_valid = verify_password('password', user.password_hash)
                print(f"기본 패스워드 'password' 검증: {'✅ 성공' if is_valid else '❌ 실패'}")
            
            # 새로 생성된 사용자의 패스워드 검증
            elif user.user_id == 'test_password_user' and user.password_hash:
                is_valid = verify_password('mySecretPassword123', user.password_hash)
                print(f"설정된 패스워드 'mySecretPassword123' 검증: {'✅ 성공' if is_valid else '❌ 실패'}")
            
            print("-" * 50)
            
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("=== 데이터베이스 패스워드 해시 확인 ===")
    check_passwords_in_database()