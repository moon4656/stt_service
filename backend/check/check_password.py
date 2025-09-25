import sys
sys.path.append('.')
from database import User, get_db
from auth import verify_password

db = next(get_db())
user = db.query(User).filter(User.email == 'test_01@sample.com').first()

if user:
    print(f'사용자: {user.email}')
    print(f'패스워드 해시: {user.password_hash[:50]}...')
    
    passwords = ['test', 'password', 'test123', 'password123']
    for pwd in passwords:
        is_valid = verify_password(pwd, user.password_hash)
        print(f"패스워드 '{pwd}': {'✅ 성공' if is_valid else '❌ 실패'}")
else:
    print('사용자를 찾을 수 없습니다.')

db.close()