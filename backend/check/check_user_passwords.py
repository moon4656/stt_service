from database import get_db, User
from auth import verify_password

def check_user_passwords():
    """데이터베이스의 사용자 패스워드 확인"""
    db = next(get_db())
    
    try:
        users = db.query(User).all()
        print(f"총 {len(users)}명의 사용자 확인:")
        print()
        
        for user in users:
            print(f"사용자 ID: {user.user_id}")
            print(f"이름: {user.name}")
            print(f"이메일: {user.email}")
            print(f"패스워드 해시: {user.password_hash[:50] if user.password_hash else 'None'}...")
            
            # 'password'로 검증
            if user.password_hash:
                is_password_correct = verify_password('password', user.password_hash)
                print(f"'password' 검증: {'✅ 성공' if is_password_correct else '❌ 실패'}")
            else:
                print("패스워드 해시가 없습니다.")
            
            print("-" * 50)
            
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_user_passwords()