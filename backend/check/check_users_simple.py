from database import get_db, User
from auth import verify_password

def check_users():
    """사용자 정보와 패스워드 확인"""
    db = next(get_db())
    
    try:
        users = db.query(User).all()
        print(f"총 {len(users)}명의 사용자:")
        print()
        
        for user in users:
            print(f"ID: {user.user_id}")
            print(f"이름: {user.name}")
            print(f"이메일: {user.email}")
            print(f"활성화: {user.is_active}")
            
            if user.password_hash:
                # 'password'로 검증
                is_valid = verify_password('password', user.password_hash)
                print(f"'password' 검증: {'✅ 성공' if is_valid else '❌ 실패'}")
                
                # 'password123'으로도 검증
                is_valid2 = verify_password('password123', user.password_hash)
                print(f"'password123' 검증: {'✅ 성공' if is_valid2 else '❌ 실패'}")
            else:
                print("패스워드 해시 없음")
            
            print("-" * 40)
            
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()