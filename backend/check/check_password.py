import bcrypt
from database import get_db, User

def check_password():
    db = next(get_db())
    user = db.query(User).filter(User.user_id == 'test_01').first()
    
    if not user:
        print("사용자를 찾을 수 없습니다.")
        return
    
    print(f"사용자 ID: {user.user_id}")
    print(f"저장된 해시: {user.password_hash}")
    
    # 여러 패스워드 시도
    test_passwords = ['test123', 'password', 'test_password', '123456', 'admin']
    
    for pwd in test_passwords:
        try:
            is_valid = bcrypt.checkpw(pwd.encode('utf-8'), user.password_hash.encode('utf-8'))
            print(f"패스워드 '{pwd}': {'✅ 맞음' if is_valid else '❌ 틀림'}")
            if is_valid:
                return pwd
        except Exception as e:
            print(f"패스워드 '{pwd}' 검증 중 오류: {e}")
    
    return None

if __name__ == "__main__":
    correct_password = check_password()
    if correct_password:
        print(f"\n올바른 패스워드: {correct_password}")
    else:
        print("\n올바른 패스워드를 찾을 수 없습니다.")