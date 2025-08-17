import requests
import sys
sys.path.append('.')
from auth import users_db, get_user
from database import get_db, User

def debug_user_cache():
    """사용자 캐시 및 데이터베이스 상태 디버깅"""
    print("=== 사용자 캐시 및 데이터베이스 디버깅 ===")
    
    # 1. 메모리 캐시 확인
    print("\n1. 메모리 캐시 상태:")
    print(f"캐시된 사용자 수: {len(users_db)}")
    for user_id, user_info in users_db.items():
        print(f"  - {user_id}: {user_info.get('email', 'N/A')} (UUID: {user_info.get('user_uuid', 'N/A')})")
    
    # 2. 데이터베이스에서 직접 조회
    print("\n2. 데이터베이스 사용자 목록:")
    db = next(get_db())
    users = db.query(User).all()
    for user in users:
        print(f"  - ID: {user.user_id}, UUID: {user.user_uuid}, Email: {user.email}")
    
    # 3. get_user 함수 테스트
    print("\n3. get_user 함수 테스트:")
    test_user_id = "testuser"
    test_user_uuid = "5483d6b1-0eda-4069-98f3-8e3986584962"  # moontech 토큰의 user_uuid
    
    print(f"\nuser_id '{test_user_id}'로 검색:")
    result1 = get_user(test_user_id)
    print(f"결과: {result1}")
    
    print(f"\nuser_uuid '{test_user_uuid}'로 검색:")
    result2 = get_user(test_user_uuid)
    print(f"결과: {result2}")
    
    # 4. API 키 검증 테스트
    print("\n4. API 키 검증 직접 테스트:")
    from auth import TokenManager
    
    # 실제 API 키 가져오기
    from database import APIToken
    api_tokens = db.query(APIToken).filter(APIToken.is_active == True).limit(3).all()
    
    if api_tokens:
        print(f"\n활성 토큰 {len(api_tokens)}개 발견:")
        for token in api_tokens:
            print(f"  - {token.token_name} (User: {token.user_uuid})")
            print(f"    Token Hash: {token.token_key[:20]}...")
        
        # 첫 번째 토큰으로 테스트 (실제 해시값 사용)
        test_token = api_tokens[0]
        print(f"\n테스트용 토큰: {test_token.token_name}")
        print(f"저장된 해시: {test_token.token_key[:20]}...")
        
        # verify_api_key 함수 테스트 (db 세션 전달)
        try:
            # 실제 API 키는 해시되어 저장되므로, 원본 키를 알 수 없음
            # 대신 TokenManager.verify_api_key를 직접 테스트
            print("\n⚠️  실제 API 키는 해시되어 저장되므로 원본을 알 수 없습니다.")
            print("대신 데이터베이스에서 직접 토큰 정보를 확인합니다.")
            
            # 토큰 정보로 사용자 조회 테스트
            user_uuid = test_token.user_uuid
            print(f"\n토큰의 user_uuid: {user_uuid}")
            
            user_info = get_user(user_uuid, db)
            print(f"사용자 정보 조회 결과: {user_info}")
            
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
    else:
        print("활성 토큰이 없습니다.")

if __name__ == "__main__":
    debug_user_cache()