from database import get_db, APIToken, User
from sqlalchemy.orm import Session
import hashlib

def get_api_keys_info():
    """데이터베이스에서 API 키 정보 조회"""
    db = next(get_db())
    
    print("=== 활성 API 토큰 정보 ===")
    tokens = db.query(APIToken).filter(APIToken.is_active == True).all()
    
    for token in tokens:
        print(f"\nToken ID: {token.token_id}")
        print(f"User UUID: {token.user_uuid}")
        print(f"Token Name: {token.token_name}")
        print(f"Token Key Hash: {token.token_key}")
        print(f"Created At: {token.created_at}")
        print(f"Last Used At: {token.last_used_at}")
        
        # 사용자 정보도 조회
        user = db.query(User).filter(User.user_uuid == token.user_uuid).first()
        if user:
            print(f"User ID: {user.user_id}")
            print(f"User Email: {user.email}")
        else:
            print("❌ 연결된 사용자를 찾을 수 없음")
        
        print("-" * 50)
    
    db.close()

def test_hash_verification():
    """해시 검증 테스트"""
    print("\n=== 해시 검증 테스트 ===")
    
    # 예시 API 키로 해시 생성 테스트
    test_api_key = "test_api_key_example"
    api_key_hash = hashlib.sha256(test_api_key.encode()).hexdigest()
    
    print(f"테스트 API 키: {test_api_key}")
    print(f"생성된 해시: {api_key_hash}")
    
    # 데이터베이스의 해시와 비교
    db = next(get_db())
    tokens = db.query(APIToken).filter(APIToken.is_active == True).all()
    
    print("\n데이터베이스의 해시들:")
    for token in tokens:
        print(f"{token.token_id}: {token.token_key}")
    
    db.close()

if __name__ == "__main__":
    get_api_keys_info()
    test_hash_verification()